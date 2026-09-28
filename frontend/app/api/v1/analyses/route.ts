import { NextRequest, NextResponse } from "next/server";
import { listAnalyses } from "@/lib/data";

export async function GET() {
  const analyses = listAnalyses();
  return NextResponse.json(analyses);
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const cancer = (body.cancer || "").trim().toLowerCase();
    const analyses = listAnalyses();

    // Look for matching evaluated cancer
    const matched = analyses.find(a => 
      a.cancer?.toLowerCase().includes(cancer) ||
      cancer.includes(a.cancer?.toLowerCase() || "") ||
      a.project?.name?.toLowerCase().includes(cancer) ||
      a.project?.project_id?.toLowerCase() === cancer
    );

    if (matched) {
      return NextResponse.json(matched, { status: 202 });
    }

    // Default to breast cancer or prostate cancer if available
    const fallback = analyses.find(a => a.status === "complete") || analyses[0];
    if (fallback) {
      return NextResponse.json(fallback, { status: 202 });
    }

    return NextResponse.json(
      { detail: "No analyses available." },
      { status: 400 }
    );
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Invalid request" }, { status: 400 });
  }
}
