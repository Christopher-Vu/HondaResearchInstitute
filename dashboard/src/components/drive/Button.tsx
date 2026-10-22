import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "neutral" | "floating";
type Size = "regular" | "compact";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-b-blue text-b-paper hover:bg-b-blue-deep",
  neutral: "bg-b-wash text-b-ink hover:bg-b-rule",
  // Sits over other content, so it carries its own surface and lift.
  floating: "bg-b-paper text-b-ink shadow-[0_8px_24px_rgb(0_0_0/0.18)] hover:bg-b-wash",
};

const SIZE_CLASSES: Record<Size, string> = {
  regular: "min-h-14 px-6 text-lg",
  compact: "min-h-11 px-4 text-base",
};

// Shared by <button>s and by links styled as buttons, such as the poster's downloads.
export function buttonClass(variant: Variant = "primary", size: Size = "regular") {
  return `inline-flex items-center justify-center gap-2 rounded-lg font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-b-blue ${SIZE_CLASSES[size]} ${VARIANT_CLASSES[variant]}`;
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  return <button type="button" className={`w-full ${buttonClass(variant)} ${className}`} {...props} />;
}
