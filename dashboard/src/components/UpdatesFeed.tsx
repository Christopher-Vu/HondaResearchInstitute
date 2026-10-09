import Image from "next/image";
import type { Update } from "@/lib/types";
import { TimeAgo } from "./TimeAgo";

const PER_PERSON = 3;

// One block per teammate, most recently active first, so a busy branch cannot bury the others.
function byAuthor(updates: Update[]): Update[][] {
  const people = new Map<string, Update[]>();
  for (const update of updates) people.set(update.author, [...(people.get(update.author) ?? []), update]);
  return [...people.values()].sort((a, b) => b[0].time.localeCompare(a[0].time));
}

function Person({ updates }: { updates: Update[] }) {
  const [latest] = updates;
  return (
    <li className="py-4">
      <div className="mb-2.5 flex items-center gap-3">
        <span className="block size-9 shrink-0 overflow-hidden rounded-full shadow-[0_0_0_1px_var(--image-outline)]">
          <Image src={latest.avatar} alt="" width={36} height={36} />
        </span>
        <div className="min-w-0">
          <a href={latest.authorUrl} className="t-title block hover:underline">{latest.author}</a>
          <span className="t-label">Active <TimeAgo iso={latest.time} /></span>
        </div>
      </div>
      <ul className="space-y-2.5 pl-12">
        {updates.slice(0, PER_PERSON).map((update) => (
          <li key={update.sha}>
            <a href={update.url} className="t-body block text-ink hover:underline">{update.message}</a>
            <span className="mt-0.5 flex items-baseline justify-between gap-3">
              <span className="t-code break-all">{update.branch}</span>
              <TimeAgo iso={update.time} className="t-label t-data shrink-0" />
            </span>
          </li>
        ))}
      </ul>
    </li>
  );
}

export function UpdatesFeed({ updates }: { updates: Update[] }) {
  if (updates.length === 0) return <p className="t-body">No commits yet on any branch.</p>;
  return (
    <ul className="divide-y divide-hairline">
      {byAuthor(updates).map((person) => <Person key={person[0].author} updates={person} />)}
    </ul>
  );
}
