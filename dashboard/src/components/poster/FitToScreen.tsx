"use client";

import { useSyncExternalStore } from "react";

const POSTER = { width: 4608, height: 3456 };

function subscribe(onChange: () => void) {
  window.addEventListener("resize", onChange);
  return () => window.removeEventListener("resize", onChange);
}

function screenScale() {
  return Math.min(window.innerWidth / POSTER.width, window.innerHeight / POSTER.height, 1);
}

// On screen the 48 x 36 in page shrinks to fit the window; print and the PDF export ignore the scale.
export function FitToScreen({ children }: { children: React.ReactNode }) {
  const scale = useSyncExternalStore(subscribe, screenScale, () => 1);
  return (
    <div className="grid min-h-dvh place-items-center bg-b-rule print:bg-transparent">
      <div className="poster-fit shadow-xl print:shadow-none" style={{ "--poster-scale": scale } as React.CSSProperties}>
        {children}
      </div>
    </div>
  );
}
