import type { Metadata } from "next";
import { DriveGame } from "@/components/drive/DriveGame";

export const metadata: Metadata = {
  title: "Can you stop in time?",
  description: "Brake when a pedestrian steps out, then compare your reaction with a driving model.",
};

export default function DrivePage() {
  return <DriveGame />;
}
