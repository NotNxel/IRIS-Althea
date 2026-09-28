import { NextRequest, NextResponse } from "next/server";
import { getAnalysisResults, getAnalysisState } from "@/lib/data";

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const state = getAnalysisState(id);
  if (!state) {
    return NextResponse.json({ detail: "Analysis not found" }, { status: 404 });
  }
  if (state.status !== "complete") {
    return NextResponse.json({ detail: "Results not available; inspect analysis status" }, { status: 409 });
  }
  const results = getAnalysisResults(id);
  if (!results) {
    return NextResponse.json({ detail: "Results not available; inspect analysis status" }, { status: 409 });
  }
  return NextResponse.json(results);
}
