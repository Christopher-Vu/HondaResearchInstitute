"use client";

import { ArrowSquareOut, CaretDoubleRight, DownloadSimple } from "@phosphor-icons/react";
import { useEffect, useState, useSyncExternalStore } from "react";
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
      setStatus(`The Canva import did not start (${error}). Try Canva again.`);
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

// Whether the bar is expanded, remembered per viewer; falls back to memory when storage is blocked.
const OPEN_KEY = "poster-export-open";
const openListeners = new Set<() => void>();
let openInMemory: boolean | null = null;

function readOpen() {
  if (openInMemory !== null) return openInMemory;
  try {
    return window.localStorage.getItem(OPEN_KEY) !== "0";
  } catch {
    return true;
  }
}

function writeOpen(open: boolean) {
  openInMemory = open;
  try {
    window.localStorage.setItem(OPEN_KEY, open ? "1" : "0");
  } catch {
    // Storage blocked: the in-memory value still applies for this visit.
  }
  openListeners.forEach((listener) => listener());
}

function subscribeOpen(listener: () => void) {
  openListeners.add(listener);
  return () => openListeners.delete(listener);
}

export function ExportBar({ canvaOneClick }: { canvaOneClick: boolean }) {
  const [status, setStatus] = useState("");
  const open = useSyncExternalStore(subscribeOpen, readOpen, () => true);
  useCanvaReturn(setStatus);

  function pdfForCanva() {
    downloadFile(PDF);
    window.open(CANVA_HOME, "_blank", "noopener");
    setStatus("PDF downloaded. In Canva, choose Create a design, then Import file.");
  }

  const canvaClass = buttonClass("neutral", "compact");
  return (
    <div data-screen-only className="fixed top-4 right-4 z-10 flex max-w-xs flex-col items-end gap-2 print:hidden">
      {open ? (
        <div className="flex items-center gap-2 rounded-xl bg-b-paper p-2 shadow-[0_8px_24px_rgb(0_0_0/0.18)]">
          <a href={PPTX} download aria-label="Download PowerPoint" className={buttonClass("primary", "compact")}>
            <DownloadSimple weight="bold" aria-hidden="true" />
            PowerPoint
          </a>
          {canvaOneClick ? (
            <a href="/api/canva/start" aria-label="Import into Canva" className={canvaClass}>
              <ArrowSquareOut weight="bold" aria-hidden="true" />
              Canva
            </a>
          ) : (
            <button type="button" onClick={pdfForCanva} aria-label="Download PDF for Canva" className={canvaClass}>
              <DownloadSimple weight="bold" aria-hidden="true" />
              Canva
            </button>
          )}
          <button
            type="button"
            onClick={() => writeOpen(false)}
            aria-label="Hide export buttons"
            aria-expanded="true"
            title="Hide"
            className="grid size-11 place-items-center rounded-lg text-b-ink-2 hover:bg-b-wash focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-b-blue"
          >
            <CaretDoubleRight weight="bold" aria-hidden="true" />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => writeOpen(true)}
          aria-expanded="false"
          className={buttonClass("floating", "compact")}
        >
          <DownloadSimple weight="bold" aria-hidden="true" />
          Export
        </button>
      )}
      <p role="status" className="rounded-lg bg-b-paper px-3 text-right text-sm text-b-ink-2 empty:hidden">
        {status}
      </p>
    </div>
  );
}
