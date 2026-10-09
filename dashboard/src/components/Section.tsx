import type { ReactNode } from "react";

export function Section({ id, title, aside, children, className = "" }: {
  id: string;
  title: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section aria-labelledby={id} className={`border-t border-hairline pt-5 ${className}`}>
      <div className="mb-5 flex items-baseline justify-between gap-4">
        <h2 id={id} className="t-heading">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

export function Failure({ what }: { what: string }) {
  return <p className="t-body">GitHub did not answer, so {what} will show after the next refresh.</p>;
}
