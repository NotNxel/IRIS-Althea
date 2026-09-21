'use client';
import {useEffect,useState,useRef} from 'react';
import Link from 'next/link';
import {api,decimal} from '@/components/api';
import {Footer} from '@/components/shell';
export default function Research(){
 const[runs,setRuns]=useState<any[]>([]);
 const[selected,setSelected]=useState<string[]>([]);
 const[result,setResult]=useState<any>(null);
 const[error,setError]=useState('');
 const[loadError,setLoadError]=useState('');
 const[loading,setLoading]=useState(true);
 const[refreshKey,setRefreshKey]=useState(0);
 const[busy,setBusy]=useState(false);
 const compareController=useRef<AbortController|null>(null);
 useEffect(()=>{
  const controller=new AbortController();
  let timer:ReturnType<typeof setTimeout>;
  async function refresh(){
   try{
    const records=await api<any[]>('/analyses',{signal:controller.signal});
    if(!controller.signal.aborted){setRuns(records);setLoadError('')}
   }catch(e){if(!controller.signal.aborted)setLoadError((e as Error).message)}
   finally{if(!controller.signal.aborted){setLoading(false);timer=setTimeout(refresh,15000)}}
  }
  refresh();
  return()=>{controller.abort();clearTimeout(timer)};
 },[refreshKey]);
 useEffect(()=>()=>compareController.current?.abort(),[]);
 const completedProjects=selected.flatMap(id=>{
  const run=runs.find(r=>r.id===id);
  return run?.status==='complete'&&run.project?.project_id?[run.project.project_id]:[];
 });
 const duplicateProjects=new Set(completedProjects).size!==completedProjects.length;
 function select(id:string,checked:boolean){
  setSelected(current=>checked?[...current,id]:current.filter(value=>value!==id));
  setResult(null);setError('');
 }
 async function compare(){
  if(compareController.current||selected.length<2||selected.length>10||duplicateProjects)return;
  const controller=new AbortController();compareController.current=controller;
  setBusy(true);setError('');setResult(null);
  try{
   const comparison=await api('/comparisons',{method:'POST',body:JSON.stringify({analysis_ids:selected,top_k:20}),signal:controller.signal});
   if(!controller.signal.aborted)setResult(comparison);
  }catch(e){if(!controller.signal.aborted)setError((e as Error).message)}
  finally{compareController.current=null;if(!controller.signal.aborted)setBusy(false)}
 }
 const name=(id:string)=>{const run=runs.find(r=>r.id===id);return `${run?.project?.project_id||run?.cancer||id.slice(0,8)} · ${id.slice(0,6)}`};return <main><div className="page-head"><span className="eyebrow">THE RESEARCH NOTEBOOK</span><h1>Independent runs. Comparable evidence.</h1><p>Inspect saved analyses and compare cancer signatures and compound rankings. Failed or insufficient-data runs remain visible in the comparison record.</p></div>{error&&<div className="notice error" role="alert">{error}</div>}{loadError&&<div className="notice error" role="alert">Could not refresh saved analyses: {loadError}. <button className="secondary" onClick={()=>setRefreshKey(value=>value+1)}>Try again</button></div>}<div className="section-heading"><h2>Saved analyses</h2><button className="primary" onClick={compare} disabled={selected.length<2||selected.length>10||duplicateProjects||busy||loading}>{busy?'Comparing…':`Compare selected (${selected.length}) →`}</button></div>{duplicateProjects&&<div className="notice" role="status">Select one completed run per cancer to compare distinct TCGA projects.</div>}<p className="small">Choose 2–10 analyses. Include one completed run per cancer; unfinished runs remain visible in the comparison record.</p>{loading?<div className="empty" role="status">Loading saved analyses…</div>:!runs.length&&!loadError?<div className="empty">No saved analyses yet. <Link href="/" style={{color:'var(--accent)'}}>Start from the workspace →</Link></div>:runs.map(r=><div className="history-row" key={r.id}><label className="check-label"><input aria-label={'Select '+r.cancer+' '+r.id.slice(0,6)} type="checkbox" checked={selected.includes(r.id)} disabled={busy||(!selected.includes(r.id)&&selected.length>=10)} onChange={e=>select(r.id,e.target.checked)}/><div><h3><Link href={'/analysis/'+r.id}>{r.project?.name||r.cancer} ↗</Link></h3><p>{r.project?.project_id||'Project unresolved'} · {r.id.slice(0,8)} · {new Date(r.created_at).toLocaleString()}</p></div></label><span className="pill">{r.status.replace('_',' ')}</span></div>)}{result&&<><div className="section-heading"><h2>Cross-cancer comparison</h2><a className="secondary" href={result.csv_url}>Download cross_cancer.csv ↓</a></div><div className="table-wrap"><table><thead><tr><th>Analysis pair</th><th>Top-20 overlap</th><th>Jaccard</th><th>Spearman ρ</th><th>Common candidates</th></tr></thead><tbody>{result.comparisons.map((c:any)=><tr key={c.a+c.b}><td>{name(c.a)} ↔ {name(c.b)}</td><td>{c.overlap}</td><td>{decimal(c.jaccard)}</td><td>{decimal(c.rank_correlation)}</td><td>{c.common_candidates}</td></tr>)}</tbody></table></div>{result.comparisons.length===0&&<div className="notice">Insufficient data: at least two completed analyses are needed to calculate overlap.</div>}<div className="section-heading"><h2>Directional cancer-signature overlap</h2></div><div className="table-wrap"><table><thead><tr><th>Analysis pair</th><th>UP Jaccard</th><th>DOWN Jaccard</th></tr></thead><tbody>{result.signature_comparisons.map((c:any)=><tr key={c.a+c.b}><td>{name(c.a)} ↔ {name(c.b)}</td><td>{decimal(c.up_jaccard)}</td><td>{decimal(c.down_jaccard)}</td></tr>)}</tbody></table></div><div className="section-heading"><h2>Top-candidate overlap matrix</h2></div><div className="table-wrap"><table><thead><tr><th>Compound</th>{result.analyses.map((r:any)=><th key={r.id}>{name(r.id)}</th>)}<th>Observed pattern</th></tr></thead><tbody>{result.compounds.map((c:any)=><tr key={c.compound}><td>{c.compound}</td>{result.analyses.map((r:any)=><td key={r.id} style={{background:c.analyses.includes(r.id)?'#254231':undefined}}>{r.status!=='complete'?'Not available':c.analyses.includes(r.id)?'● Top 20':'—'}</td>)}<td>{c.cancer_specific?'Exclusive in selected lists':`Shared by ${c.cancer_count} lists`}</td></tr>)}</tbody></table></div><div className="notice">{result.caveat}</div>{result.analyses.filter((r:any)=>r.status!=='complete').map((r:any)=><div className="notice error" key={r.id}>{name(r.id)}: {r.status} — {r.reason||'No completed results available'}</div>)}</>}<div className="notice">Central research question: Can transcriptomic reversal be used to prioritize compounds whose gene-expression effects oppose a cancer-specific molecular signature?</div><Footer/></main>}
