import { ArrowRight, CheckCircle } from "@phosphor-icons/react/dist/ssr";
import Image from "next/image";
import type { Week, WeekItem } from "@/lib/types";

const dayFormat = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });

function range(start: string, end: string): string {
  return `${dayFormat.format(new Date(start))} to ${dayFormat.format(new Date(end))}`;
}

function Item({ item, done, avatars }: { item: WeekItem; done: boolean; avatars: Map<string, string> }) {
  const avatar = item.who ? avatars.get(item.who) : undefined;
  return (
    <li className="flex items-start gap-3">
      {done ? (
        <CheckCircle aria-label="Done" size={18} weight="fill" className="mt-0.5 shrink-0 text-ink" />
      ) : (
        <ArrowRight aria-label="Next" size={18} className="mt-0.5 shrink-0 text-accent" />
      )}
      <span className="t-body flex-1 text-ink">{item.text}</span>
      {avatar && (
        <Image src={avatar} alt={item.who ?? ""} title={item.who} width={22} height={22}
          className="mt-0.5 shrink-0 rounded-full shadow-[0_0_0_1px_var(--image-outline)]" />
      )}
    </li>
  );
}

export function WeekSummary({ week, avatars }: { week: Week; avatars: Map<string, string> }) {
  return (
    <section aria-label="This week and next" className="grid gap-8 border-b border-hairline py-8 md:grid-cols-2 md:gap-14">
      <div>
        <h2 className="t-heading">This week <span className="t-label t-data ml-1.5 font-normal">{range(week.start, week.end)}</span></h2>
        <ul className="mt-4 space-y-3">
          {week.done.map((item) => <Item key={item.text} item={item} done avatars={avatars} />)}
        </ul>
      </div>
      <div>
        <h2 className="t-heading">Next week</h2>
        <ul className="mt-4 space-y-3">
          {week.next.map((item) => <Item key={item.text} item={item} done={false} avatars={avatars} />)}
        </ul>
      </div>
    </section>
  );
}
