import { NextRequest, NextResponse } from "next/server";
import { getCandidate } from "@/lib/data";

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string; compound: string }> }) {
  const { id, compound } = await params;
  const candidate = getCandidate(id, compound);
  if (!candidate) {
    return NextResponse.json({ detail: "Compound not found" }, { status: 404 });
  }
  return NextResponse.json(candidate);
}
