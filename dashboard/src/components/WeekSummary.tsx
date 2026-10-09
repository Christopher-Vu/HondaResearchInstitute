import { ArrowRight, CheckCircle } from "@phosphor-icons/react/dist/ssr";
import Image from "next/image";
import type { Week, WeekItem } from "@/lib/types";

const dayFormat = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });

function range(start: string, end: string): string {
  return `${dayFormat.format(new Date(start))} to ${dayFormat.format(new Date(end))}`;
}

function DoneItem({ item, avatars }: { item: WeekItem; avatars: Map<string, string> }) {
  return (
    <li className="flex items-start gap-3">
      <CheckCircle aria-label="Done" size={18} weight="fill" className="mt-0.5 shrink-0 text-ink" />
      <span className="t-body flex-1 text-ink">{item.text}</span>
      {item.who && <span className="mt-0.5" title={item.who}><Avatar login={item.who} avatars={avatars} alt={item.who} /></span>}
    </li>
  );
}

function Avatar({ login, avatars, alt = "" }: { login: string; avatars: Map<string, string>; alt?: string }) {
  const avatar = avatars.get(login);
  if (!avatar) return null;
  return (
    <Image src={avatar} alt={alt} width={22} height={22}
      className="shrink-0 rounded-full shadow-[0_0_0_1px_var(--image-outline)]" />
  );
}

function byPerson(items: WeekItem[]): [string, WeekItem[]][] {
  const groups = new Map<string, WeekItem[]>();
  for (const item of items) {
    const who = item.who ?? "Unassigned";
    groups.set(who, [...(groups.get(who) ?? []), item]);
  }
  return [...groups];
}

function PersonPlan({ who, items, avatars }: { who: string; items: WeekItem[]; avatars: Map<string, string> }) {
  return (
    <li>
      <p className="t-title flex items-center gap-2 text-ink">
        <Avatar login={who} avatars={avatars} />
        {who}
      </p>
      <ul className="mt-2 space-y-2 pl-[30px]">
        {items.map((item) => (
          <li key={item.text} className="flex items-start gap-3">
            <ArrowRight aria-hidden size={18} className="mt-0.5 shrink-0 text-accent" />
            <span className="t-body flex-1 text-ink">{item.text}</span>
          </li>
        ))}
      </ul>
    </li>
  );
}

export function WeekSummary({ week, avatars }: { week: Week; avatars: Map<string, string> }) {
  return (
    <section aria-label="This week and next" className="grid gap-8 border-b border-hairline py-8 md:grid-cols-2 md:gap-14">
      <div>
        <h2 className="t-heading">This week <span className="t-label t-data ml-1.5 font-normal">{range(week.start, week.end)}</span></h2>
        <ul className="mt-4 space-y-3">
          {week.done.map((item) => <DoneItem key={item.text} item={item} avatars={avatars} />)}
        </ul>
      </div>
      <div>
        <h2 className="t-heading">Next week</h2>
        <ul className="mt-4 space-y-5">
          {byPerson(week.next).map(([who, items]) => <PersonPlan key={who} who={who} items={items} avatars={avatars} />)}
        </ul>
      </div>
    </section>
  );
}
