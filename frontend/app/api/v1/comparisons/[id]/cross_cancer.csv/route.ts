import { NextRequest } from "next/server";

export async function GET(req: NextRequest) {
  const headers = ["a", "b", "top_k", "overlap", "jaccard", "rank_correlation", "common_candidates"];
  const csv = headers.join(",") + "\n";
  return new Response(csv, {
    status: 200,
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": `attachment; filename="cross_cancer.csv"`,
    },
  });
}
