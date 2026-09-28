import { NextRequest, NextResponse } from "next/server";
import { getArtifact } from "@/lib/data";

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string; name: string }> }) {
  const { id, name } = await params;
  const artifact = getArtifact(id, name);
  if (!artifact) {
    return NextResponse.json({ detail: "Artifact not found" }, { status: 404 });
  }

  const contentType = name.endsWith(".json")
    ? "application/json"
    : name.endsWith(".csv")
    ? "text/csv"
    : "application/octet-stream";

  return new Response(artifact.buffer, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Content-Disposition": `attachment; filename="${name}"`,
    },
  });
}
