import type { Metadata } from "next";
import { FitToScreen } from "@/components/poster/FitToScreen";
import { Poster } from "@/components/poster/Poster";

export const metadata: Metadata = {
  title: "Research poster",
  description: "48 x 36 in print poster for the failure-axis discovery project.",
};

export default function PosterPage() {
  return (
    <FitToScreen>
      <Poster />
    </FitToScreen>
  );
}
