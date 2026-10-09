"use client";

import { useSyncExternalStore } from "react";

const units: [Intl.RelativeTimeFormatUnit, number][] = [
  ["day", 86_400_000],
  ["hour", 3_600_000],
  ["minute", 60_000],
];
const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto", style: "short" });
// Pinned to the team's time zone so the server (UTC on Vercel) and the browser render the same text.
const absolute = new Intl.DateTimeFormat("en-US", {
  month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/Los_Angeles", timeZoneName: "short",
});

function describe(iso: string, now: number): string {
  const elapsed = new Date(iso).getTime() - now;
  for (const [unit, size] of units) {
    if (Math.abs(elapsed) >= size) return relative.format(Math.round(elapsed / size), unit);
  }
  return "just now";
}

function subscribe(onChange: () => void) {
  const timer = setInterval(onChange, 60_000);
  return () => clearInterval(timer);
}

// The server renders the absolute time; the browser swaps in "3 hr. ago" against its own clock.
export function TimeAgo({ iso, className = "" }: { iso: string; className?: string }) {
  const now = useSyncExternalStore(subscribe, () => Math.floor(Date.now() / 60_000) * 60_000, () => 0);
  return (
    <time dateTime={iso} title={absolute.format(new Date(iso))} className={className}>
      {now === 0 ? absolute.format(new Date(iso)) : describe(iso, now)}
    </time>
  );
}
