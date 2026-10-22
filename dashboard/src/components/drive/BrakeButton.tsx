import { HandPalm } from "@phosphor-icons/react";
import type { PointerEvent } from "react";

interface BrakeButtonProps {
  held: boolean;
  onPress: () => void;
  onRelease: () => void;
}

export function BrakeButton({ held, onPress, onRelease }: BrakeButtonProps) {
  function handlePointerDown(event: PointerEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    onPress();
  }

  return (
    <button
      type="button"
      aria-label="Brake. Press and hold, or hold the space bar."
      onPointerDown={handlePointerDown}
      onPointerUp={onRelease}
      onPointerCancel={onRelease}
      onContextMenu={(event) => event.preventDefault()}
      className={`flex min-h-20 w-full touch-none select-none items-center justify-center gap-3 rounded-lg text-3xl font-semibold text-b-paper [-webkit-tap-highlight-color:transparent] [-webkit-touch-callout:none] motion-safe:transition-colors ${
        held ? "bg-b-blue-deep ring-4 ring-b-gold" : "bg-b-blue"
      }`}
    >
      <HandPalm size={36} weight="fill" aria-hidden="true" />
      Brake
    </button>
  );
}
