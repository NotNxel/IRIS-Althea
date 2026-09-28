import path from "path";
import fs from "fs";

export function getDataDir(): string {
  const candidates = [
    path.join(process.cwd(), "data"),
    path.join(process.cwd(), "frontend", "data"),
    path.resolve(process.cwd(), "..", "data"),
  ];
  for (const c of candidates) {
    if (fs.existsSync(path.join(c, "analyses"))) {
      return c;
    }
  }
  return path.join(process.cwd(), "data");
}

export function getProjects(): any[] {
  const file = path.join(getDataDir(), "projects.json");
  if (fs.existsSync(file)) {
    return JSON.parse(fs.readFileSync(file, "utf-8"));
  }
  return [];
}

export function listAnalyses(): any[] {
  const analysesDir = path.join(getDataDir(), "analyses");
  if (!fs.existsSync(analysesDir)) return [];
  const entries = fs.readdirSync(analysesDir, { withFileTypes: true });
  const results: any[] = [];
  for (const entry of entries) {
    if (entry.isDirectory()) {
      const stateFile = path.join(analysesDir, entry.name, "state.json");
      if (fs.existsSync(stateFile)) {
        try {
          const state = JSON.parse(fs.readFileSync(stateFile, "utf-8"));
          results.push(state);
        } catch {
          // ignore corrupted files
        }
      }
    }
  }
  return results.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
}

export function getAnalysisFolder(id: string): string | null {
  const sanitized = id.replace(/[^a-zA-Z0-9-]/g, "");
  const folder = path.join(getDataDir(), "analyses", sanitized);
  if (fs.existsSync(folder) && fs.existsSync(path.join(folder, "state.json"))) {
    return folder;
  }
  return null;
}

export function getAnalysisState(id: string): any | null {
  const folder = getAnalysisFolder(id);
  if (!folder) return null;
  return JSON.parse(fs.readFileSync(path.join(folder, "state.json"), "utf-8"));
}

export function getAnalysisResults(id: string): any | null {
  const folder = getAnalysisFolder(id);
  if (!folder) return null;
  const resultsFile = path.join(folder, "results.json");
  if (!fs.existsSync(resultsFile)) return null;
  return JSON.parse(fs.readFileSync(resultsFile, "utf-8"));
}

export function getCandidate(id: string, compound: string): any | null {
  const results = getAnalysisResults(id);
  if (!results || !results.candidates) return null;
  
  const decodedCompound = decodeURIComponent(compound).trim().toLowerCase();
  const candidate = results.candidates.find(
    (c: any) => c.compound.toLowerCase() === decodedCompound
  );
  if (!candidate) return null;

  const folder = getAnalysisFolder(id)!;
  const evidenceFile = path.join(folder, "gene_level_scores.csv");
  let geneEvidence: any[] = [];

  if (fs.existsSync(evidenceFile)) {
    const content = fs.readFileSync(evidenceFile, "utf-8");
    const lines = content.split("\n");
    const header = lines[0].split(",").map(h => h.trim());
    const compoundIdx = header.indexOf("compound");
    const geneIdx = header.indexOf("gene");
    const cancerLog2fcIdx = header.indexOf("cancer_log2fc");
    const cancerDirIdx = header.indexOf("cancer_direction");
    const drugDirIdx = header.indexOf("drug_direction");
    const contributionIdx = header.indexOf("contribution");
    const opposingIdx = header.indexOf("opposing");
    const termIdx = header.indexOf("term");

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      const parts = line.split(",");
      if (parts[compoundIdx]?.trim().toLowerCase() === candidate.compound.toLowerCase()) {
        geneEvidence.push({
          gene: parts[geneIdx]?.trim(),
          cancer_log2fc: parseFloat(parts[cancerLog2fcIdx] || "0"),
          cancer_direction: parts[cancerDirIdx]?.trim(),
          drug_direction: parts[drugDirIdx]?.trim(),
          contribution: parseFloat(parts[contributionIdx] || "0"),
          opposing: parts[opposingIdx]?.trim().toLowerCase() === "true",
          term: parts[termIdx]?.trim(),
          compound: candidate.compound,
        });
      }
    }
  }

  return {
    ...candidate,
    gene_evidence: geneEvidence,
    signature: results.signature,
  };
}

export function getArtifact(id: string, name: string): { path: string; buffer: Buffer } | null {
  const allowed = new Set([
    "signature.csv", "differential_expression.csv", "candidate_rankings.csv", "robustness.csv",
    "cross_cancer.csv", "analysis_metadata.json", "gene_level_scores.csv", "results.json",
    "raw_counts.csv.gz", "normalized_cpm.csv.gz", "signature_baseline.csv", "signature_relaxed.csv",
    "signature_stringent.csv", "signature_multi-context.csv"
  ]);
  if (!allowed.has(name)) return null;

  const folder = getAnalysisFolder(id);
  if (!folder) return null;
  const filePath = path.join(folder, name);
  if (!fs.existsSync(filePath)) return null;

  return { path: filePath, buffer: fs.readFileSync(filePath) };
}

function spearman(x: number[], y: number[]): number | null {
  const n = x.length;
  if (n < 2) return null;
  const meanX = x.reduce((a, b) => a + b, 0) / n;
  const meanY = y.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let denX = 0;
  let denY = 0;
  for (let i = 0; i < n; i++) {
    const dx = x[i] - meanX;
    const dy = y[i] - meanY;
    num += dx * dy;
    denX += dx * dx;
    denY += dy * dy;
  }
  const den = Math.sqrt(denX * denY);
  if (den === 0) return 0;
  return num / den;
}

export function compareAnalyses(ids: string[], topK: number = 20) {
  const records: Record<string, any> = {};
  for (const id of ids) {
    const state = getAnalysisState(id);
    if (!state) continue;
    if (state.status === "complete") {
      records[id] = getAnalysisResults(id) || state;
    } else {
      records[id] = state;
    }
  }

  const available: Record<string, any> = {};
  for (const [k, v] of Object.entries(records)) {
    if (v.status === "complete") {
      available[k] = v;
    }
  }

  const rankings: Record<string, any[]> = {};
  for (const [k, v] of Object.entries(available)) {
    rankings[k] = v.candidates || [];
  }

  const comparisons: any[] = [];
  const keys = Object.keys(rankings);
  for (let i = 0; i < keys.length; i++) {
    for (let j = i + 1; j < keys.length; j++) {
      const a = keys[i];
      const b = keys[j];
      const aa: Record<string, number> = {};
      rankings[a].forEach(r => { aa[r.compound] = r.rank; });
      const bb: Record<string, number> = {};
      rankings[b].forEach(r => { bb[r.compound] = r.rank; });

      const topA = new Set(rankings[a].slice(0, topK).map(r => r.compound));
      const topB = new Set(rankings[b].slice(0, topK).map(r => r.compound));
      const overlapCount = [...topA].filter(c => topB.has(c)).length;
      const unionCount = new Set([...topA, ...topB]).size;
      const jaccard = unionCount > 0 ? overlapCount / unionCount : null;

      const commonCompounds = Object.keys(aa).filter(c => c in bb);
      commonCompounds.sort();
      const rankA = commonCompounds.map(c => aa[c]);
      const rankB = commonCompounds.map(c => bb[c]);
      const rho = spearman(rankA, rankB);

      comparisons.push({
        a,
        b,
        top_k: topK,
        overlap: overlapCount,
        jaccard,
        rank_correlation: rho,
        common_candidates: commonCompounds.length,
      });
    }
  }

  const collected: Record<string, Record<string, number>> = {};
  for (const [config, cands] of Object.entries(rankings)) {
    for (const row of cands) {
      if (!collected[row.compound]) collected[row.compound] = {};
      collected[row.compound][config] = row.rank;
    }
  }

  const stability: any[] = [];
  for (const [compound, ranks] of Object.entries(collected)) {
    const vals = Object.values(ranks);
    const mean = vals.reduce((sum, v) => sum + v, 0) / vals.length;
    const variance = vals.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / vals.length;
    stability.push({
      compound,
      ranks,
      configurations_present: vals.length,
      top_k_frequency: vals.filter(v => v <= topK).length,
      evaluated_configurations: keys.length,
      mean_rank: mean,
      rank_sd: Math.sqrt(variance),
    });
  }
  stability.sort((a, b) => {
    if (b.top_k_frequency !== a.top_k_frequency) return b.top_k_frequency - a.top_k_frequency;
    if (a.mean_rank !== b.mean_rank) return a.mean_rank - b.mean_rank;
    return a.compound.localeCompare(b.compound);
  });

  const signaturePairs: any[] = [];
  for (let i = 0; i < keys.length; i++) {
    for (let j = i + 1; j < keys.length; j++) {
      const a = keys[i];
      const b = keys[j];
      const row: any = { a, b };
      for (const arm of ["up", "down"]) {
        const ga = new Set((available[a].signature || []).filter((g: any) => g.direction === arm).map((g: any) => g.gene));
        const gb = new Set((available[b].signature || []).filter((g: any) => g.direction === arm).map((g: any) => g.gene));
        const inter = [...ga].filter(g => gb.has(g)).length;
        const union = new Set([...ga, ...gb]).size;
        row[arm + "_jaccard"] = union > 0 ? inter / union : null;
      }
      signaturePairs.push(row);
    }
  }

  const appearances: Record<string, string[]> = {};
  for (const [key, ranking] of Object.entries(rankings)) {
    const top = new Set(ranking.slice(0, topK).map(r => r.compound));
    for (const c of top) {
      if (!appearances[c]) appearances[c] = [];
      appearances[c].push(key);
    }
  }

  const compoundList = Object.keys(appearances).sort().map(c => ({
    compound: c,
    analyses: appearances[c],
    cancer_count: appearances[c].length,
    cancer_specific: appearances[c].length === 1,
  }));

  const analysisSummaries = Object.entries(records).map(([key, value]) => ({
    id: key,
    project: value.project,
    status: value.status,
    reason: value.error,
  }));

  const comparisonId = "comp-" + Date.now();

  return {
    id: comparisonId,
    comparisons,
    stability,
    top_k: topK,
    signature_comparisons: signaturePairs,
    compounds: compoundList,
    analyses: analysisSummaries,
    caveat: "Specificity means exclusive to the selected top-k lists, not biological specificity.",
    csv_url: `/api/v1/comparisons/${comparisonId}/cross_cancer.csv`,
  };
}
