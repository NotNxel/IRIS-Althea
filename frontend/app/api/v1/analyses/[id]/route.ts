import { NextRequest, NextResponse } from "next/server";
import { getAnalysisState } from "@/lib/data";

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const state = getAnalysisState(id);
  if (!state) {
    return NextResponse.json({ detail: "Analysis not found" }, { status: 404 });
  }
  return NextResponse.json(state);
}
