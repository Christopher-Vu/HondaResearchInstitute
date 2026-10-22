import localFont from "next/font/local";

// Static TTFs (IBM's release, OFL) rather than Google's variable font: Chromium embeds static
// TrueType as real text in the print PDF, which Canva can import as editable type.
const plex = localFont({
  variable: "--font-plex",
  src: [
    { path: "../../fonts/IBMPlexSans-Regular.ttf", weight: "400" },
    { path: "../../fonts/IBMPlexSans-Medium.ttf", weight: "500" },
    { path: "../../fonts/IBMPlexSans-SemiBold.ttf", weight: "600" },
    { path: "../../fonts/IBMPlexSans-Bold.ttf", weight: "700" },
  ],
});

export default function BerkeleyLayout({ children }: { children: React.ReactNode }) {
  return <div className={`${plex.variable} theme-berkeley min-h-dvh`}>{children}</div>;
}
