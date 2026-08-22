import { Callout, Empty, Panel } from "@/components/ui";
import { formatDate, titleCase } from "@/lib/format";
import type { ConditionStatus, Thesis } from "@/lib/types";

export const CONDITION_STYLE: Record<
  ConditionStatus,
  { chip: string; rail: string; label: string }
> = {
  holding: {
    chip: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
    rail: "bg-emerald-500",
    label: "Holding",
  },
  at_risk: {
    chip: "bg-amber-500/12 text-amber-300 ring-amber-500/35",
    rail: "bg-amber-500",
    label: "At risk",
  },
  broken: {
    chip: "bg-rose-500/15 text-rose-300 ring-rose-500/40",
    rail: "bg-rose-500",
    label: "Broken",
  },
  unknown: {
    chip: "bg-neutral-700/40 text-neutral-400 ring-neutral-600/40",
    rail: "bg-neutral-600",
    label: "Unknown",
  },
};

export function ThesisPanel({ thesis }: { thesis: Thesis | null }) {
  if (!thesis) {
    return (
      <Panel title="Thesis">
        <Empty>No thesis has been written for this candidate.</Empty>
      </Panel>
    );
  }

  const broken = thesis.conditions.filter((c) => c.status === "broken").length;
  const atRisk = thesis.conditions.filter((c) => c.status === "at_risk").length;

  return (
    <div className="space-y-4">
      <Panel
        title="Thesis"
        right={
          <span className="text-[11px] text-neutral-500">
            written {formatDate(thesis.created_at)} · status{" "}
            <span className="text-neutral-300">
              {titleCase(thesis.status)}
            </span>
          </span>
        }
      >
        <p className="max-w-4xl text-[14px] leading-relaxed text-neutral-200">
          {thesis.statement}
        </p>
      </Panel>

      {broken > 0 ? (
        <Callout
          tone="danger"
          title={`${broken} falsifying condition${broken > 1 ? "s have" : " has"} broken`}
        >
          A thesis is only useful if it can fail. These conditions were written
          in advance to say what would count as being wrong, and they now read as
          broken.
        </Callout>
      ) : atRisk > 0 ? (
        <Callout tone="warn" title={`${atRisk} condition${atRisk > 1 ? "s" : ""} at risk`}>
          Not yet falsifying, but the evidence has moved against the thesis on
          these points.
        </Callout>
      ) : null}

      <Panel title={`Falsifying conditions (${thesis.conditions.length})`}>
        <ul className="space-y-2.5">
          {thesis.conditions.map((c) => {
            const style = CONDITION_STYLE[c.status];
            return (
              <li
                key={c.text}
                className="relative overflow-hidden rounded-md border border-neutral-800 bg-neutral-950/40 pl-3"
              >
                <div className={`absolute left-0 top-0 h-full w-[3px] ${style.rail}`} />
                <div className="p-3">
                  <div className="flex flex-wrap items-start gap-2">
                    <span
                      className={`mt-0.5 inline-flex shrink-0 items-center rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wider ring-1 ring-inset ${style.chip}`}
                    >
                      {style.label}
                    </span>
                    <span className="min-w-0 flex-1 text-[13px] leading-relaxed text-neutral-200">
                      {c.text}
                    </span>
                  </div>
                  {c.note ? (
                    <p className="mt-1.5 pl-0 text-[12px] leading-relaxed text-neutral-500">
                      {c.note}
                    </p>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      </Panel>
    </div>
  );
}
