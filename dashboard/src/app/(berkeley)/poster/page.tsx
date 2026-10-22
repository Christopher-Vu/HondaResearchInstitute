import type { Metadata } from "next";
import { Poster } from "@/components/poster/Poster";

export const metadata: Metadata = {
  title: "Research poster",
  description: "48 x 36 in print poster for the failure-axis discovery project.",
};

export default function PosterPage() {
  return <Poster />;
}
