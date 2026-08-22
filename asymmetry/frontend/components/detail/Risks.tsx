import { Callout, Empty, Panel } from "@/components/ui";
import { SEVERITY_ORDER } from "@/lib/format";
import type { RedFlagReport, Severity } from "@/lib/types";

export const SEVERITY_STYLE: Record<
  Severity,
  { chip: string; rail: string; text: string }
> = {
  critical: {
    chip: "bg-rose-500/15 text-rose-300 ring-rose-500/40",
    rail: "bg-rose-500",
    text: "text-rose-200/80",
  },
  high: {
    chip: "bg-orange-500/12 text-orange-300 ring-orange-500/35",
    rail: "bg-orange-500",
    text: "text-orange-200/80",
  },
  medium: {
    chip: "bg-amber-500/10 text-amber-300 ring-amber-500/30",
    rail: "bg-amber-500",
    text: "text-amber-200/80",
  },
  low: {
    chip: "bg-neutral-700/40 text-neutral-400 ring-neutral-600/40",
    rail: "bg-neutral-600",
    text: "text-neutral-400",
  },
};

export function Risks({ report }: { report: RedFlagReport | null }) {
  if (!report || report.flags.length === 0) {
    return (
      <Panel title="Red flags">
        <Empty>No red flags recorded for this candidate.</Empty>
      </Panel>
    );
  }

  const grouped = SEVERITY_ORDER.map((sev) => ({
    severity: sev,
    flags: report.flags.filter((f) => f.severity === sev),
  })).filter((g) => g.flags.length > 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric label="Red-flag score" value={report.red_flag_score} tone="bad" />
        <Metric
          label="Penalty applied"
          value={`-${report.penalty_points}`}
          tone="bad"
          hint="subtracted from the composite"
        />
        <Metric label="Flags raised" value={report.flags.length} />
        <Metric
          label="Critical or high"
          value={
            report.flags.filter(
              (f) => f.severity === "critical" || f.severity === "high",
            ).length
          }
          tone="bad"
        />
      </div>

      {grouped.map((g) => (
        <Panel
          key={g.severity}
          title={
            <span className="flex items-center gap-2">
              <span
                className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wider ring-1 ring-inset ${SEVERITY_STYLE[g.severity].chip}`}
              >
                {g.severity}
              </span>
              <span className="font-normal text-neutral-500">
                {g.flags.length} flag{g.flags.length > 1 ? "s" : ""}
              </span>
            </span>
          }
        >
          <ul className="space-y-2.5">
            {g.flags.map((f) => (
              <li
                key={f.code}
                className="relative overflow-hidden rounded-md border border-neutral-800 bg-neutral-950/40 pl-3"
              >
                <div
                  className={`absolute left-0 top-0 h-full w-[3px] ${SEVERITY_STYLE[g.severity].rail}`}
                />
                <div className="p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[11px] text-neutral-500">
                      {f.code}
                    </span>
                    <span className="text-[13px] font-medium text-neutral-100">
                      {f.title}
                    </span>
                    <span className="ml-auto rounded bg-neutral-800 px-1.5 py-0.5 text-[11px] tabular-nums text-neutral-300">
                      -{f.points}
                    </span>
                  </div>
                  <p className="mt-1.5 text-[12.5px] leading-relaxed text-neutral-400">
                    {f.detail}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      ))}

      <Callout tone="note">
        Penalty points are itemised and subtracted from the base score in the
        open, so the final composite can always be reconstructed from its parts.
        Nothing is quietly removed.
      </Callout>
    </div>
  );
}

function Metric({
  label,
  value,
  hint,
  tone = "normal",
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "normal" | "bad";
}) {
  return (
    <div className="rounded-md border border-neutral-800 bg-neutral-900/60 px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wider text-neutral-500">
        {label}
      </div>
      <div
        className={`mt-0.5 text-xl font-semibold tabular-nums ${
          tone === "bad" ? "text-rose-300" : "text-neutral-100"
        }`}
      >
        {value}
      </div>
      {hint ? (
        <div className="text-[10px] leading-snug text-neutral-600">{hint}</div>
      ) : null}
    </div>
  );
}
