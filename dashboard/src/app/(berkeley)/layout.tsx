import localFont from "next/font/local";

// Static TTFs (Alegreya release, OFL) rather than a variable font: Chromium embeds static
// TrueType as real text in the print PDF, which Canva can import as editable type.
const alegreya = localFont({
  variable: "--font-alegreya",
  src: [
    { path: "../../fonts/Alegreya-Regular.ttf", weight: "400" },
    { path: "../../fonts/Alegreya-Medium.ttf", weight: "500" },
    { path: "../../fonts/Alegreya-SemiBold.ttf", weight: "600" },
    { path: "../../fonts/Alegreya-Bold.ttf", weight: "700" },
  ],
});

export default function BerkeleyLayout({ children }: { children: React.ReactNode }) {
  return <div className={`${alegreya.variable} theme-berkeley min-h-dvh`}>{children}</div>;
}
