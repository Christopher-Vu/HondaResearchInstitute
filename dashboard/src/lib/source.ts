import { cacheLife } from "next/cache";
import { parse } from "yaml";
import type { Progress, Step1Measure, Step2Measure, Update } from "./types";

export const REPO = "Christopher-Vu/HondaResearchInstitute";
export const REPO_URL = `https://github.com/${REPO}`;
// The branch the progress file and step configs are read from. Set DATA_REF to main once
// codex/carla-bringup has merged.
export const DATA_REF = process.env.DATA_REF ?? "codex/carla-bringup";

const UPDATE_WORD_LIMIT = 20;

// Plain github.com endpoints (git refs and Atom feeds) carry no API rate limit, so a public
// repo needs no token.
async function getText(url: string): Promise<string> {
  const response = await fetch(url, { headers: { "User-Agent": "failure-axis-status" } });
  if (!response.ok) throw new Error(`${url} answered ${response.status}`);
  return response.text();
}

// Branch heads from git's own ref listing: branch name to commit id.
async function branchHeads(): Promise<Map<string, string>> {
  const refs = await getText(`${REPO_URL}.git/info/refs?service=git-upload-pack`);
  return new Map([...refs.matchAll(/([0-9a-f]{40}) refs\/heads\/([^\s\0]+)/g)].map((match) => [match[2], match[1]]));
}

// Read at the branch's current commit, not the branch name: raw.githubusercontent.com caches
// branch URLs for up to 5 minutes, but a commit URL never changes.
async function readRepoYaml<T>(path: string): Promise<T> {
  "use cache";
  cacheLife("repo");
  const commit = (await branchHeads()).get(DATA_REF) ?? DATA_REF;
  return parse(await getText(`https://raw.githubusercontent.com/${REPO}/${commit}/${path}`)) as T;
}

export async function getProgress(): Promise<Progress> {
  return readRepoYaml<Progress>("docs/steps/progress.yaml");
}

export async function getStep1(): Promise<Step1Measure> {
  return (await readRepoYaml<{ measure: Step1Measure }>("configs/rollout/step1-single-route.yaml")).measure;
}

export async function getStep2(): Promise<Step2Measure> {
  return (await readRepoYaml<{ measure: Step2Measure }>("configs/rollout/step2-bench2drive220.yaml")).measure;
}


const ENTITIES: Record<string, string> = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'" };

function decode(text: string): string {
  return text.replace(/&(amp|lt|gt|quot|#39);/g, (entity) => ENTITIES[entity]);
}

function field(entry: string, pattern: RegExp): string {
  return decode(entry.match(pattern)?.[1]?.trim() ?? "");
}

export function limitWords(text: string, limit = UPDATE_WORD_LIMIT): string {
  const words = text.split(/\s+/).filter(Boolean);
  return words.length <= limit ? words.join(" ") : `${words.slice(0, limit).join(" ")}…`;
}

function parseFeed(xml: string, branch: string): Update[] {
  return [...xml.matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map(([, entry]) => ({
    sha: field(entry, /Grit::Commit\/(\w+)/),
    url: field(entry, /<link[^>]*href="([^"]+)"/),
    message: limitWords(field(entry, /<title>([\s\S]*?)<\/title>/)),
    author: field(entry, /<name>([\s\S]*?)<\/name>/),
    authorUrl: field(entry, /<uri>([\s\S]*?)<\/uri>/),
    avatar: field(entry, /<media:thumbnail[^>]*url="([^"]+)"/).replace(/s=\d+/, "s=96"),
    branch,
    time: field(entry, /<updated>([\s\S]*?)<\/updated>/),
  }));
}

function isMerge(update: Update): boolean {
  return /^Merge (pull request|branch|remote-tracking)/.test(update.message);
}

// A commit reachable from several branches is shown once, under the branch listed first:
// the default branch, then the others in ref order.
export async function getUpdates(): Promise<{ updates: Update[]; fetchedAt: string }> {
  "use cache";
  cacheLife("repo");
  const branches = [...(await branchHeads()).keys()];
  const feeds = await Promise.all(
    branches.map(async (branch) => parseFeed(await getText(`${REPO_URL}/commits/${branch}.atom`), branch)),
  );
  const ordered = [...feeds].sort((a, b) => Number(b[0]?.branch === "main") - Number(a[0]?.branch === "main"));
  const seen = new Map<string, Update>();
  for (const update of ordered.flat()) {
    if (!seen.has(update.sha) && !isMerge(update)) seen.set(update.sha, update);
  }
  const updates = [...seen.values()].sort((a, b) => b.time.localeCompare(a.time));
  return { updates, fetchedAt: new Date().toISOString() };
}
