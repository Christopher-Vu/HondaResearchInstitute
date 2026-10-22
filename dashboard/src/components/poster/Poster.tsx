/* eslint-disable @next/next/no-img-element -- print export needs raw files, no image optimizer */
import qr from "@/data/qr-drive.json";
import { ControlBars, DecoyRow, LayerChart, OcclusionWaffles, PipelineFigure } from "./Figures";
import { HeroScene } from "./HeroScene";
import { layers, occlusion } from "./facts";

// One place for the 48 x 36 in grid (96 px = 1 in): 1 in margins, 0.67 in gutters.
const LAYOUT = {
  header: { left: 0, top: 0, width: 4608, height: 600 },
  hero: { left: 96, top: 672, width: 2880, height: 1360 },
  demo: { left: 3040, top: 672, width: 1472, height: 1360 },
  method: { left: 96, top: 2096, width: 1180, height: 1150 },
  proof: { left: 1340, top: 2096, width: 1400, height: 1150 },
  layers: { left: 2804, top: 2096, width: 820, height: 1150 },
  control: { left: 3688, top: 2096, width: 824, height: 1150 },
  footer: { left: 96, top: 3296, width: 4416, height: 96 },
} as const;

type Area = keyof typeof LAYOUT;

function Region({ area, className = "", children }: { area: Area; className?: string; children: React.ReactNode }) {
  return (
    <div className={`absolute ${className}`} style={LAYOUT[area]}>
      {children}
    </div>
  );
}

function Panel({ area, title, children }: { area: Area; title: string; children: React.ReactNode }) {
  return (
    <Region area={area} className="flex flex-col gap-[40px] bg-b-wash p-[64px]">
      <h2 className="p-head">{title}</h2>
      {children}
    </Region>
  );
}

function Header() {
  return (
    <Region area="header" className="flex items-center gap-[80px] bg-b-blue px-[96px]">
      <img src="/poster/berkeley-seal.png" alt="University of California, Berkeley seal" className="size-[420px] shrink-0" />
      <div className="flex min-w-0 flex-1 flex-col gap-[28px]">
        <h1 className="p-title">Finding the Edge Cases That Crash Self-Driving Cars</h1>
        <p className="p-subtitle">Failure discovery read from inside a vision-language-action driving model, built to work with any VLA</p>
        <p className="p-authors">
          Catherine Wang, Christopher Vu, Jason He, Hiram Lannes, Jerry Yan<span className="ml-[48px] text-b-gold">Mentor: Ryan Lingo</span>
        </p>
      </div>
      <div className="flex size-[420px] shrink-0 items-center justify-center rounded-[40px] bg-b-paper">
        <img src="/poster/honda.png" alt="Honda" className="w-[310px]" />
      </div>
    </Region>
  );
}

function Hero() {
  return (
    <Region area="hero" className="flex flex-col gap-[32px]">
      <div className="flex items-end gap-[96px]">
        <div className="flex flex-1 flex-col gap-[32px]">
          <h2 className="p-head">Test lists only catch the crashes someone imagined</h2>
          <p className="p-body">
            Driving models such as SimLingo are checked against failures people already thought of. We find new ones by
            reading the model&rsquo;s own internal signals, with no list. To prove it works we plant a failure on purpose:
            block the centre of the camera.
          </p>
        </div>
        <div className="flex w-[1060px] shrink-0 flex-col gap-[20px]">
          <p className="p-stat">{occlusion.ratio.toFixed(1)}&times;</p>
          <p className="p-label-strong">more failures with the camera centre blocked</p>
          <p className="p-label">
            {occlusion.blocked.failed} of {occlusion.blocked.routes} routes against {occlusion.clear.failed} of {occlusion.clear.routes} clear, in CARLA
          </p>
        </div>
      </div>
      <div className="shrink-0">
        <HeroScene />
      </div>
    </Region>
  );
}

function QrCode({ size }: { size: number }) {
  const modules = qr.rows.length;
  const path = qr.rows
    .flatMap((row, y) => [...row].map((bit, x) => (bit === "1" ? `M${x} ${y}h1v1h-1z` : "")))
    .join("");
  return (
    <svg viewBox={`0 0 ${modules} ${modules}`} width={size} height={size} role="img" aria-label={`QR code for ${qr.url}`} shapeRendering="crispEdges">
      <path d={path} fill="var(--b-blue)" />
    </svg>
  );
}

function Demo() {
  return (
    <Region area="demo" className="flex flex-col gap-[48px] bg-b-blue p-[72px]">
      <h2 className="p-head text-b-gold">Can you stop in time?</h2>
      <p className="p-body text-b-paper">
        Scan and drive: a person steps out from behind a van, and you hold Brake. Then see the same moment for the model
        alone and for the model trained on what we found.
      </p>
      <div className="flex flex-1 items-end gap-[56px]">
        <div className="flex flex-col gap-[28px]">
          <div className="rounded-[36px] bg-b-paper p-[48px]">
            <QrCode size={560} />
          </div>
          <p className="p-label text-b-paper">failure-axis-status.vercel.app/drive</p>
        </div>
        <img
          src="/poster/drive-phone.png"
          alt="The demo on a phone: three roads side by side, you, the model alone, and the model with our SDK"
          className="h-[900px] w-auto rounded-[56px] shadow-[0_24px_60px_rgb(0_0_0/0.35)]"
        />
      </div>
    </Region>
  );
}

function Method() {
  return (
    <Panel area="method" title="How discovery works">
      <PipelineFigure />
      <p className="p-body mt-auto">
        We record layer 10 of SimLingo on every drive and contrast failing drives with clean ones. Each direction that
        separates them is a failure axis, and it names the scenarios to train on next.
      </p>
    </Panel>
  );
}

function Proof() {
  return (
    <Panel area="proof" title="Planted failures must really fail">
      <div className="flex gap-[64px]">
        <div className="w-[480px] shrink-0">
          <OcclusionWaffles />
        </div>
        <div className="flex flex-col gap-[40px]">
          <p className="p-body">
            <strong>
              {occlusion.blockedOnly} routes failed only when blocked, {occlusion.clearOnly} only when clear
            </strong>{" "}
            (p&nbsp;=&nbsp;{occlusion.fisherP}<sup>{occlusion.fisherExponent}</sup>). Fog and animals look unusual but did not raise failures, so they are decoys.
          </p>
          <DecoyRow />
        </div>
      </div>
    </Panel>
  );
}

function Layers() {
  return (
    <Panel area="layers" title="Where to listen">
      <LayerChart />
      <p className="p-body mt-auto">
        We scored all 24 layers on {layers.routes} drives for how well each flags the {layers.failing} failures. Layer{" "}
        {layers.chosen} is best, where 0.5 is chance.
      </p>
    </Panel>
  );
}

function Control() {
  return (
    <Panel area="control" title="Control check">
      <ControlBars />
      <p className="p-body mt-auto">
        Every method finds this easy planted failure: the bench works, but ours has not won yet. Next: harder failures
        and a second VLA.
      </p>
    </Panel>
  );
}

function Footer() {
  return (
    <Region area="footer" className="flex items-center justify-between gap-[64px]">
      <p className="p-note">
        SimLingo: Renz et al., CVPR 2025. Bench2Drive: Jia et al., NeurIPS 2024. CARLA: Dosovitskiy et al., CoRL 2017.
        Overlap is Jaccard similarity, shared failures over combined failures.
      </p>
      <p className="p-note shrink-0">UC Berkeley, College of Computing, Data Science, and Society, with Honda Research Institute</p>
    </Region>
  );
}

export function Poster() {
  return (
    <main className="relative h-[3456px] w-[4608px] overflow-hidden bg-b-paper" aria-label="Research poster">
      <Header />
      <Hero />
      <Demo />
      <Method />
      <Proof />
      <Layers />
      <Control />
      <Footer />
    </main>
  );
}
