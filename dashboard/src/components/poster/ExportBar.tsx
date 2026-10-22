"use client";

import { ArrowSquareOut, DownloadSimple } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { buttonClass } from "@/components/drive/Button";
import type { ImportJob } from "@/lib/canva";

const PPTX = "/poster/exports/poster.pptx";
const PDF = "/poster/exports/poster.pdf";
const CANVA_HOME = "https://www.canva.com/";
const POLL_MS = 2000;

function downloadFile(href: string) {
  const link = document.createElement("a");
  link.href = href;
  link.download = "";
  link.click();
}

// After the Canva sign-in, /api/canva/callback sends the user back with ?canva_job=<id> or ?canva_error=<code>.
function useCanvaReturn(setStatus: (message: string) => void) {
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const error = query.get("canva_error");
    if (error) {
      setStatus(`The Canva import did not start (${error}). Download the PDF for Canva instead.`);
      return;
    }
    const job = query.get("canva_job");
    if (!job) return;
    setStatus("Importing the poster into Canva…");
    const timer = window.setInterval(async () => {
      const result = (await (await fetch(`/api/canva/import/${encodeURIComponent(job)}`)).json()) as ImportJob;
      if (result.status === "in_progress") return;
      window.clearInterval(timer);
      if (result.status === "success" && result.editUrl) window.location.assign(result.editUrl);
      else setStatus(`Canva could not import the poster: ${result.error ?? "unknown error"}.`);
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [setStatus]);
}

export function ExportBar({ canvaOneClick }: { canvaOneClick: boolean }) {
  const [status, setStatus] = useState("");
  useCanvaReturn(setStatus);

  function pdfForCanva() {
    downloadFile(PDF);
    window.open(CANVA_HOME, "_blank", "noopener");
    setStatus("PDF downloaded. In Canva, choose Create a design, then Import file.");
  }

  return (
    <div data-screen-only className="fixed top-4 right-4 z-10 flex max-w-sm flex-col items-end gap-2 print:hidden">
      <div className="flex flex-wrap justify-end gap-2 rounded-xl bg-b-paper p-2 shadow-[0_8px_24px_rgb(0_0_0/0.18)]">
        <a href={PPTX} download className={buttonClass("primary", "compact")}>
          <DownloadSimple weight="bold" aria-hidden="true" />
          Download PowerPoint
        </a>
        {canvaOneClick && (
          <a href="/api/canva/start" className={buttonClass("neutral", "compact")}>
            <ArrowSquareOut weight="bold" aria-hidden="true" />
            Import into Canva
          </a>
        )}
        <button type="button" onClick={pdfForCanva} className={buttonClass("neutral", "compact")}>
          <DownloadSimple weight="bold" aria-hidden="true" />
          Download PDF for Canva
        </button>
      </div>
      <p role="status" className="rounded-lg bg-b-paper px-3 text-right text-sm text-b-ink-2 empty:hidden">
        {status}
      </p>
    </div>
  );
}
