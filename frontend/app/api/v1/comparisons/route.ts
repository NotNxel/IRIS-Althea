import { NextRequest, NextResponse } from "next/server";
import { compareAnalyses } from "@/lib/data";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const ids: string[] = body.analysis_ids || [];
    const topK: number = body.top_k || 20;

    if (ids.length < 2) {
      return NextResponse.json({ detail: "Select at least two analyses" }, { status: 422 });
    }
    if (new Set(ids).size !== ids.length) {
      return NextResponse.json({ detail: "Select distinct analyses" }, { status: 422 });
    }

    const comparison = compareAnalyses(ids, topK);
    return NextResponse.json(comparison);
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Comparison failed" }, { status: 400 });
  }
}
