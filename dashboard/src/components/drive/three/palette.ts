import { useEffect, useState, type RefObject } from "react";

// three.js needs concrete colours, so the scene reads the .theme-berkeley tokens once instead of restating them.
const TOKENS = ["blue", "blue-deep", "blue-mid", "gold", "gold-deep", "ink", "ink-3", "rule", "wash", "paper", "asphalt", "crash"] as const;

export type Token = (typeof TOKENS)[number];
export type Palette = Record<Token, string>;

function readPalette(element: Element): Palette {
  const style = getComputedStyle(element);
  return Object.fromEntries(TOKENS.map((token) => [token, style.getPropertyValue(`--b-${token}`).trim()])) as Palette;
}

export function usePalette(ref: RefObject<HTMLElement | null>) {
  const [palette, setPalette] = useState<Palette | null>(null);
  useEffect(() => {
    if (ref.current) setPalette(readPalette(ref.current));
  }, [ref]);
  return palette;
}
