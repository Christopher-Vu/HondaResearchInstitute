import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "neutral";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-b-blue text-b-paper hover:bg-b-blue-deep",
  neutral: "bg-b-wash text-b-ink hover:bg-b-rule",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  return (
    <button
      type="button"
      className={`min-h-14 w-full rounded-lg px-6 text-lg font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-b-blue ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    />
  );
}
