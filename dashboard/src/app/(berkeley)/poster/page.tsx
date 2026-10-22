import type { Metadata } from "next";
import { ExportBar } from "@/components/poster/ExportBar";
import { FitToScreen } from "@/components/poster/FitToScreen";
import { Poster } from "@/components/poster/Poster";
import { canvaConfigured } from "@/lib/canva";

export const metadata: Metadata = {
  title: "Research poster",
  description: "48 x 36 in print poster for the failure-axis discovery project.",
};

export default function PosterPage() {
  return (
    <>
      <ExportBar canvaOneClick={canvaConfigured()} />
      <FitToScreen>
        <Poster />
      </FitToScreen>
    </>
  );
}
