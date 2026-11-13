/* eslint-disable @next/next/no-img-element -- print export needs raw files, no image optimizer */
import qr from "@/data/qr-drive.json";
import { ControlBars, GapGallery, LayerChart, OcclusionWaffles, PipelineFigure } from "./Figures";
import { HeroScene } from "./HeroScene";
import { layers, occlusion, reproduction } from "./facts";

// One place for the 48 x 36 in grid (96 px = 1 in): 1 in margins, 0.67 in gutters.
const LAYOUT = {
  header: { left: 0, top: 0, width: 4608, height: 600 },
  hero: { left: 96, top: 672, width: 2560, height: 1360 },
  results: { left: 2720, top: 672, width: 1792, height: 1360 },
  demo: { left: 96, top: 2096, width: 1040, height: 1104 },
  method: { left: 1200, top: 2096, width: 1680, height: 1104 },
  gaps: { left: 2944, top: 2096, width: 1568, height: 1104 },
  footer: { left: 96, top: 3248, width: 4416, height: 144 },
} as const;

type Area = keyof typeof LAYOUT;

function Region({ area, className = "", children }: { area: Area; className?: string; children: React.ReactNode }) {
  return (
    <div className={`absolute ${className}`} style={LAYOUT[area]}>
      {children}
    </div>
  );
}

function Panel({ area, title, claim, children }: { area: Area; title: string; claim?: string; children: React.ReactNode }) {
  return (
    <Region area={area} className="flex flex-col gap-[36px] bg-b-wash p-[64px]">
      <div className="flex flex-col gap-[16px]">
        <h2 className="p-head">{title}</h2>
        {claim && <p className="p-claim">{claim}</p>}
      </div>
      {children}
    </Region>
  );
}

function Bullets({ items, className = "" }: { items: React.ReactNode[]; className?: string }) {
  return (
    <ul className={`p-bullets ${className}`}>
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
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
    <Region area="hero" className="flex flex-col gap-[40px]">
      <div className="flex items-start gap-[80px]">
        <div className="flex flex-1 flex-col gap-[28px]">
          <div className="flex flex-col gap-[16px]">
            <h2 className="p-head">Problem</h2>
            <p className="p-claim">Test lists only catch the crashes someone imagined</p>
          </div>
          <Bullets
            items={[
              "Driving models are tested on failures people already thought of.",
              "We find new ones from the model\u2019s own internal signals, with no list.",
              "To check this works, we plant a failure: we block the centre of the camera.",
            ]}
          />
        </div>
        <figure className="flex w-[820px] shrink-0 flex-col gap-[14px]">
          <img
            src="/poster/p4-blocked-city.jpg"
            alt="A SimLingo camera frame from a city route with the middle third of the image blacked out"
            className="aspect-[2/1] w-full object-cover"
          />
          <figcaption className="p-label">What the model sees with the planted patch</figcaption>
        </figure>
      </div>
      <div className="mt-auto shrink-0">
        <HeroScene />
      </div>
    </Region>
  );
}

function ResultBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-[20px]">
      <h3 className="p-label-strong">{title}</h3>
      {children}
    </div>
  );
}

function Results() {
  return (
    <Panel area="results" title="Results">
      <ResultBlock title="Blocking the camera centre is a real failure">
        <div className="flex items-start gap-[64px]">
          <div className="w-[800px] shrink-0">
            <OcclusionWaffles />
          </div>
          <div className="flex flex-col gap-[16px]">
            <p className="p-stat">
              {occlusion.blockedOnly}:{occlusion.clearOnly}
            </p>
            <p className="p-label">
              paired routes that failed only blocked, against only clear (p&nbsp;=&nbsp;{occlusion.pairedP}
              <sup>{occlusion.pairedExponent}</sup>)
            </p>
          </div>
        </div>
      </ResultBlock>
      <div className="grid grid-cols-2 gap-[64px]">
        <ResultBlock title={`Layer ${layers.chosen} flags failures best`}>
          <LayerChart />
        </ResultBlock>
        <ResultBlock title="Every method finds the easy control">
          <ControlBars />
        </ResultBlock>
      </div>
      <p className="p-note mt-auto">
        Measured in CARLA simulation on Bench2Drive routes. Repair by targeted training is next and not measured yet.
      </p>
    </Panel>
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
    <Region area="demo" className="flex flex-col gap-[36px] bg-b-blue p-[64px]">
      <div className="flex flex-col gap-[16px]">
        <h2 className="p-head text-b-gold">Demo</h2>
        <p className="p-claim text-b-paper">Can you stop in time?</p>
      </div>
      <Bullets
        className="text-b-paper"
        items={["Scan the code.", "Hold Brake when someone steps out.", "Compare yourself with the model and our SDK."]}
      />
      <div className="mt-auto flex items-end justify-between gap-[36px]">
        <div className="flex flex-col gap-[20px]">
          <div className="rounded-[32px] bg-b-paper p-[36px]">
            <QrCode size={380} />
          </div>
          <p className="p-note text-b-paper">failure-axis-status.vercel.app/drive</p>
        </div>
        <img
          src="/poster/drive-phone.png"
          alt="The demo on a phone: a 3D street with three lanes, you, the model alone, and the model with our SDK, after a pedestrian steps out"
          className="h-[520px] w-auto rounded-[40px] shadow-[0_24px_60px_rgb(0_0_0/0.35)]"
        />
      </div>
    </Region>
  );
}

function Method() {
  return (
    <Panel area="method" title="Methodology" claim="How we find failure axes">
      <PipelineFigure />
      <Bullets
        className="mt-auto"
        items={[
          "Run SimLingo on Bench2Drive routes and record layer 10 on every drive.",
          "A plane that separates failing drives from clean ones is a failure axis.",
          "Each axis names scenarios to train on next.",
        ]}
      />
      <p className="p-note">
        Our two reproductions scored {reproduction.scores[0]} and {reproduction.scores[1]} of 100 over{" "}
        {reproduction.routes} routes.
      </p>
    </Panel>
  );
}

function Gaps() {
  return (
    <Panel area="gaps" title="Validation" claim="Planted failures must really fail">
      <Bullets
        items={[
          "Each planted failure is sealed in an answer key.",
          "We keep only those that raise failures.",
          "Fog and animals did not fail, so they are decoys.",
        ]}
      />
      <div className="mt-auto">
        <GapGallery />
      </div>
    </Panel>
  );
}

const WORDMARKS = ["SimLingo", "Bench2Drive"];

function BuiltWith() {
  return (
    <div className="flex items-center gap-[56px]">
      <p className="p-label">Built with</p>
      {WORDMARKS.map((name) => (
        <p key={name} className="p-wordmark">
          {name}
        </p>
      ))}
      <img src="/poster/logos/carla.png" alt="CARLA simulator" className="h-[120px] w-auto" />
      <img src="/poster/logos/pytorch.svg" alt="PyTorch" className="h-[72px] w-auto" />
      <div className="flex items-center gap-[16px]">
        <img src="/poster/logos/hf.svg" alt="" className="h-[88px] w-auto" />
        <p className="p-wordmark">Hugging Face</p>
      </div>
      <div className="flex items-center gap-[16px]">
        <img src="/poster/logos/brc.png" alt="Berkeley Research Computing" className="size-[120px]" />
        <p className="p-wordmark">Savio</p>
      </div>
    </div>
  );
}

function Footer() {
  return (
    <Region area="footer" className="flex items-center justify-between gap-[64px]">
      <BuiltWith />
      <p className="p-note max-w-[1300px] text-right">
        <strong>References.</strong> SimLingo: Renz et al., CVPR 2025. Bench2Drive: Jia et al., NeurIPS 2024. CARLA: Dosovitskiy et al., CoRL 2017.
        Overlap is Jaccard similarity: shared failures over combined failures.
      </p>
    </Region>
  );
}

export function Poster() {
  return (
    <main className="relative h-[3456px] w-[4608px] overflow-hidden bg-b-paper" aria-label="Research poster">
      <Header />
      <Hero />
      <Results />
      <Demo />
      <Method />
      <Gaps />
      <Footer />
    </main>
  );
}
