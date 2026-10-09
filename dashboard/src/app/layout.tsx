import type { Metadata } from "next";
import { JetBrains_Mono, Mona_Sans } from "next/font/google";
import "./globals.css";

const mona = Mona_Sans({ variable: "--font-mona", subsets: ["latin"], axes: ["wdth"] });
const jetbrains = JetBrains_Mono({ variable: "--font-jetbrains", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Failure-axis discovery status",
  description: "Plan progress, Bench2Drive results, compute and team updates for the SimLingo failure-axis project.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${mona.variable} ${jetbrains.variable} h-full`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
