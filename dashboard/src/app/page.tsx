import { GithubLogo } from "@phosphor-icons/react/dist/ssr";
import Image from "next/image";
import { Suspense } from "react";
import { LayerSweep, ModelDiagram, ReplayStrip, type ReplayFrame } from "@/components/Activations";
import { AbilityChart, BulletRow } from "@/components/Benchmark";
import { ComputeSummary } from "@/components/Compute";
import { RouteWaffle } from "@/components/RouteWaffle";
import { Failure, Section } from "@/components/Section";
import { CheckList, doneCount, StepLadder } from "@/components/StepLadder";
import { TimeAgo } from "@/components/TimeAgo";
import { UpdatesFeed } from "@/components/UpdatesFeed";
import { WeekSummary } from "@/components/WeekSummary";
import replayBf16 from "@/data/replay-bf16.json";
import step2Routes from "@/data/step2-routes.json";
import { DATA_REF, getProgress, getStep1, getStep2, getUpdates, REPO, REPO_URL } from "@/lib/source";
import type { Route } from "@/lib/types";

type Settled<T> = { ok: true; value: T } | { ok: false };

async function settle<T>(promise: Promise<T>): Promise<Settled<T>> {
  try {
    return { ok: true, value: await promise };
  } catch {
    return { ok: false };
  }
}

const routes = step2Routes.routes as Route[];
const replayFrames = replayBf16.frames as ReplayFrame[];
const whole = new Intl.NumberFormat("en-US");

function Placeholder({ height }: { height: string }) {
  return <div className={`${height} animate-pulse rounded-xl bg-track motion-reduce:animate-none`} />;
}

async function ThisWeek() {
  const [progress, feed] = await Promise.all([settle(getProgress()), settle(getUpdates())]);
  if (!progress.ok || !progress.value.week) return null;
  const avatars = new Map(
    (feed.ok ? feed.value.updates : []).map((update) => [update.authorUrl.split("/").pop() ?? "", update.avatar]),
  );
  return <WeekSummary week={progress.value.week} avatars={avatars} />;
}

async function Plan() {
  const [progress, step1] = await Promise.all([settle(getProgress()), settle(getStep1())]);
  if (!progress.ok) return <Failure what="the plan" />;
  const { steps, current } = progress.value;
  const step = steps.find((candidate) => candidate.id === current) ?? steps[0];
  return (
    <section aria-labelledby="plan" className="grid gap-10 py-10 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)] lg:gap-14 lg:py-14">
      <div className="flex flex-col">
        <h2 id="plan" className="sr-only">Plan progress</h2>
        <p className="t-display rise-in">Step {step.id}</p>
        <p className="t-heading rise-in mt-3" style={{ ["--i" as string]: 1 }}>{step.title}</p>
        <p className="t-label t-data mt-1">{doneCount(step)} of {step.checks.length} done-conditions met</p>
        <div className="mt-6"><CheckList checks={step.checks} /></div>
        <div className="mt-auto pt-10">
          <p className="t-title mb-3">All {steps.length} steps</p>
          <StepLadder steps={steps} current={current} />
        </div>
      </div>
      <figure className="self-start">
        <Image
          src="/savio-route-26956.png" alt="SimLingo's front camera on a Town05 road with two cars ahead" width={1024} height={512} priority
          className="w-full rounded-xl outline-1 -outline-offset-1 outline-[var(--image-outline)]"
        />
        {step1.ok && (
          <figcaption className="t-label mt-3">
            What SimLingo saw on a Savio A40 during route 26956, which it finished with a score of 100 at {step1.value.real_time_factor.toFixed(3)}× real time.
          </figcaption>
        )}
      </figure>
    </section>
  );
}

async function Benchmark() {
  const [progress, step2] = await Promise.all([settle(getProgress()), settle(getStep2())]);
  if (!progress.ok || !step2.ok) return <Failure what="the benchmark" />;
  const { paper, bar_driving_score } = progress.value.benchmark;
  const measure = step2.value;
  return (
    <div className="grid gap-10 md:grid-cols-2 md:gap-12">
      <div className="space-y-8">
        <BulletRow name="Driving score" ours={measure.official_driving_score} paper={paper.driving_score} bar={bar_driving_score} index={0} />
        <BulletRow
          name="Success rate" unit="%" index={1}
          ours={measure.official_success_rate * 100}
          paper={{ mean: paper.success_rate.mean * 100, sd: paper.success_rate.sd * 100 }}
        />
      </div>
      <AbilityChart ours={measure.ability_success_rate} paper={paper.ability_success_rate} />
    </div>
  );
}

async function RecordedCounts() {
  const step2 = await settle(getStep2());
  if (!step2.ok) return null;
  return (
    <div className="flex flex-wrap gap-x-10 gap-y-4">
      <p><span className="t-figure block">{routes.length}</span><span className="t-label">Savio routes recorded</span></p>
      <p><span className="t-figure block">{whole.format(Math.round(step2.value.simulated_seconds / 0.05))}</span><span className="t-label">steps recorded, 24 layers each</span></p>
    </div>
  );
}

async function Compute() {
  const [progress, step1, step2] = await Promise.all([settle(getProgress()), settle(getStep1()), settle(getStep2())]);
  if (!progress.ok || !step1.ok || !step2.ok) return <Failure what="compute" />;
  const spent = [
    { item: "Step 2, all 220 routes", su: step2.value.service_units },
    { item: "Per-ability scoring", su: step2.value.ability_job_service_units },
    { item: "Step 1, one route", su: step1.value.service_units },
  ];
  return <ComputeSummary compute={progress.value.compute} spent={spent} perRoute={step2.value.service_units / routes.length} />;
}

async function Team() {
  const feed = await settle(getUpdates());
  if (!feed.ok) return <Failure what="team updates" />;
  return <UpdatesFeed updates={feed.value.updates} />;
}

async function CheckedAt() {
  const feed = await settle(getUpdates());
  return feed.ok ? <span className="t-label">Checked <TimeAgo iso={feed.value.fetchedAt} /></span> : null;
}

export default function Page() {
  return (
    <div className="mx-auto max-w-[1320px] px-4 pb-16 sm:px-8">
      <header className="flex h-16 items-center justify-between gap-4 border-b border-hairline">
        <h1 className="t-title">
          Failure-axis discovery <span className="hidden font-normal text-ink-3 sm:inline">SimLingo on Bench2Drive</span>
        </h1>
        <a href={REPO_URL} aria-label="Open the repository on GitHub" className="-m-2 rounded-full p-2 text-ink-2 transition-colors duration-150 hover:text-ink">
          <GithubLogo size={22} />
        </a>
      </header>

      <Suspense fallback={<div className="py-8"><Placeholder height="h-40" /></div>}>
        <ThisWeek />
      </Suspense>

      <Suspense fallback={<div className="py-14"><Placeholder height="h-80" /></div>}>
        <Plan />
      </Suspense>

      <div className="grid gap-14 lg:grid-cols-[minmax(0,1fr)_21rem] xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="space-y-14">
          <Section id="benchmark" title="Bench2Drive-220 on Savio" aside={<span className="t-label">One seed, chain-of-thought off</span>}>
            <Suspense fallback={<Placeholder height="h-56" />}><Benchmark /></Suspense>
          </Section>
          <Section id="routes" title="Every route">
            <RouteWaffle routes={routes} />
          </Section>
          <Section id="activations" title="Activations">
            <div className="space-y-10">
              <Suspense fallback={<Placeholder height="h-14" />}><RecordedCounts /></Suspense>
              <ModelDiagram />
              <LayerSweep draftUrl={`${REPO_URL}/blob/${DATA_REF}/docs/steps/b7-gap-signal.md`} />
              <ReplayStrip frames={replayFrames} />
            </div>
          </Section>
          <Section id="compute" title="Compute">
            <Suspense fallback={<Placeholder height="h-56" />}><Compute /></Suspense>
          </Section>
        </div>
        <Section id="team" title="Team" aside={<Suspense><CheckedAt /></Suspense>}>
          <Suspense fallback={<Placeholder height="h-96" />}><Team /></Suspense>
        </Section>
      </div>

      <footer className="t-label mt-16 border-t border-hairline pt-5">
        Read from {REPO} on the {DATA_REF} branch every 10 minutes. Route outcomes come from Savio jobs 39732614 to 39734524.
      </footer>
    </div>
  );
}
