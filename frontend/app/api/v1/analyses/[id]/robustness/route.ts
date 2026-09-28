import { NextRequest, NextResponse } from "next/server";
import { getAnalysisResults } from "@/lib/data";

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const results = getAnalysisResults(id);
  if (!results || !results.robustness) {
    return NextResponse.json({ detail: "Robustness results not available" }, { status: 409 });
  }
  return NextResponse.json(results.robustness);
}
