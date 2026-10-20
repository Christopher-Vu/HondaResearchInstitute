import { CheckCircle, MinusCircle } from "@phosphor-icons/react/dist/ssr";
import Image from "next/image";
import pilots from "@/data/gap-pilots.json";

type Arm = { label: string; failed: number; routes: number };
type Photo = { src: string; alt: string; caption: string };
type Gap = {
  id: string;
  name: string;
  change: string;
  passed: boolean;
  stage: string;
  with: Arm;
  without: Arm;
  photos: Photo[];
};

const gaps = pilots.gaps as Gap[];
const share = (arm: Arm) => Math.round((100 * arm.failed) / arm.routes);

function RateRow({ arm, emphasis, index }: { arm: Arm; emphasis: boolean; index: number }) {
  return (
    <div className="grid grid-cols-[minmax(6.5rem,auto)_1fr_auto] items-center gap-3">
      <span className="t-label text-ink-2">{arm.label}</span>
      <div className="h-2.5 rounded-[3px] bg-track" aria-hidden>
        <div
          className={`grow-x h-full rounded-[3px] ${emphasis ? "bg-ink" : "bg-quiet"}`}
          style={{ width: `${share(arm)}%`, ["--i" as string]: index }}
        />
      </div>
      <span className="t-label t-data whitespace-nowrap text-right">{arm.failed} of {arm.routes} failed</span>
    </div>
  );
}

function FailureRates({ gap, index }: { gap: Gap; index: number }) {
  return (
    <div role="img" className="space-y-2"
      aria-label={`${gap.with.label}: ${gap.with.failed} of ${gap.with.routes} routes failed. ${gap.without.label}: ${gap.without.failed} of ${gap.without.routes}.`}>
      <RateRow arm={gap.with} emphasis index={index} />
      <RateRow arm={gap.without} emphasis={false} index={index + 1} />
    </div>
  );
}

function Verdict({ gap }: { gap: Gap }) {
  return gap.passed ? (
    <p className="t-title flex items-center gap-1.5 text-ink">
      <CheckCircle size={18} weight="fill" className="shrink-0 text-accent" aria-hidden />
      Passes efficacy, {gap.stage}
    </p>
  ) : (
    <p className="t-label flex items-center gap-1.5">
      <MinusCircle size={16} weight="bold" className="shrink-0" aria-hidden />
      Did not pass, {gap.stage}
    </p>
  );
}

function Frame({ photo, sizes, priority = false }: { photo: Photo; sizes: string; priority?: boolean }) {
  return (
    <figure>
      <Image src={photo.src} alt={photo.alt} width={1024} height={512} sizes={sizes} priority={priority}
        className="w-full rounded-lg outline-1 -outline-offset-1 outline-[var(--image-outline)]" />
      <figcaption className="t-label mt-2">{photo.caption}</figcaption>
    </figure>
  );
}

function LeadGap({ gap }: { gap: Gap }) {
  return (
    <article className={gap.photos.length ? "grid gap-6 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)] lg:gap-10" : "max-w-xl"}>
      <div className="flex flex-col gap-4 lg:order-last">
        <h3 className="t-heading">{gap.id} {gap.name}</h3>
        <p className="t-body">{gap.change}.</p>
        <div className="flex items-baseline gap-6">
          <p><span className="t-figure t-data block">{share(gap.with)}%</span><span className="t-label">failed {gap.with.label.toLowerCase()}</span></p>
          <p><span className="t-figure t-data block text-ink-3">{share(gap.without)}%</span><span className="t-label">{gap.without.label.toLowerCase()}</span></p>
        </div>
        <FailureRates gap={gap} index={0} />
        <Verdict gap={gap} />
      </div>
      {gap.photos.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {gap.photos.map((photo) => (
            <Frame key={photo.src} photo={photo} sizes="(min-width: 1024px) 30vw, (min-width: 640px) 50vw, 100vw" priority />
          ))}
        </div>
      )}
    </article>
  );
}

function OtherGap({ gap, index }: { gap: Gap; index: number }) {
  return (
    <article className="flex flex-col gap-3">
      <h3 className="t-title">{gap.id} {gap.name}</h3>
      {gap.photos[0] && <Frame photo={gap.photos[0]} sizes="(min-width: 768px) 30vw, 100vw" />}
      <FailureRates gap={gap} index={index * 2 + 2} />
      <Verdict gap={gap} />
    </article>
  );
}

export function GapEvidence() {
  const [lead, ...others] = [...gaps].sort((a, b) => Number(b.passed) - Number(a.passed));
  return (
    <div className="space-y-12">
      <LeadGap gap={lead} />
      <div className="grid gap-x-8 gap-y-10 md:grid-cols-3">
        {others.map((gap, index) => <OtherGap key={gap.id} gap={gap} index={index} />)}
      </div>
    </div>
  );
}
