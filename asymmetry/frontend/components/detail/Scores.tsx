import { BarChart, type BarDatum } from "@/components/BarChart";
import { Pct } from "@/components/Pct";
import { EstimateLegend } from "@/components/Estimate";
import { Callout, Panel, ScrollTable, Td, Th } from "@/components/ui";
import { DIMENSION_LABELS } from "@/lib/scoreMath";
import type { Composite, DimensionScore } from "@/lib/types";
import { titleCase } from "@/lib/format";

function label(dimension: string): string {
  return DIMENSION_LABELS[dimension] ?? titleCase(dimension);
}

export function Scores({
  composite,
  dimensions,
}: {
  composite: Composite | null;
  dimensions: DimensionScore[];
}) {
  if (!composite) {
    return (
      <Panel title="Score decomposition">
        <p className="text-[13px] text-neutral-500">
          No composite score has been computed for this candidate.
        </p>
      </Panel>
    );
  }

  const entries = Object.entries(composite.contributions).sort(
    (a, b) => b[1] - a[1],
  );
  const bars: BarDatum[] = entries.map(([dim, contribution]) => ({
    label: label(dim),
    note: `${composite.components[dim]} × ${(composite.weights[dim] * 100).toFixed(0)}%`,
    value: contribution,
    display: contribution.toFixed(1),
    color: contribution >= 10 ? "#34d399" : contribution >= 6 ? "#38bdf8" : "#737373",
  }));

  const byDimension = new Map(dimensions.map((d) => [d.dimension, d]));

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Panel
          title="Where the composite score comes from"
          right={<EstimateLegend />}
        >
          <BarChart
            data={bars}
            ariaLabel="Contribution to composite score by dimension"
            max={Math.max(...entries.map(([, v]) => v)) * 1.15}
          />
          <p className="mt-3 text-[11px] leading-relaxed text-neutral-600">
            Each bar is the dimension score multiplied by its fixed weight. The
            weights live in the scoring module rather than inside any prompt, so
            they are identical for every candidate.
          </p>
        </Panel>

        <Panel title="Arithmetic">
          <dl className="space-y-2.5 text-[13px]">
            <Row
              label="Base score"
              value={composite.base_score.toFixed(1)}
              hint="sum of weighted contributions"
            />
            <Row
              label="Red-flag penalty"
              value={`-${composite.penalty.toFixed(1)}`}
              hint="itemised below, never silently applied"
              tone="bad"
            />
            <div className="border-t border-neutral-800 pt-2.5">
              <Row
                label="Overall score"
                value={composite.overall_score.toFixed(1)}
                hint="base less penalty"
                emphasis
              />
            </div>
            <Row
              label="Confidence"
              value={composite.confidence_score.toFixed(1)}
              hint="mean evidential confidence across dimensions"
            />
          </dl>

          {composite.penalty_reasons.length > 0 ? (
            <div className="mt-3 border-t border-neutral-800 pt-3">
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">
                Penalty itemisation
              </div>
              <ul className="mt-1.5 space-y-1">
                {composite.penalty_reasons.map((r) => (
                  <li key={r} className="text-[11.5px] leading-relaxed text-rose-200/70">
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {composite.missing_dimensions.length > 0 ? (
            <div className="mt-3 border-t border-neutral-800 pt-3 text-[11px] text-amber-200/70">
              Not scored:{" "}
              {composite.missing_dimensions.map(label).join(", ")}. The weight of
              a missing dimension is not redistributed, so the composite is
              structurally conservative.
            </div>
          ) : null}
        </Panel>
      </div>

      <Panel title="Dimension detail">
        <ScrollTable>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Dimension</Th>
                <Th align="right">Score</Th>
                <Th align="right">Weight</Th>
                <Th align="right">Contribution</Th>
                <Th align="right">Confidence</Th>
                <Th>Rationale</Th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([dim, contribution]) => {
                const d = byDimension.get(dim);
                return (
                  <tr key={dim} className="hover:bg-neutral-800/20">
                    <Td className="font-medium text-neutral-100">{label(dim)}</Td>
                    <Td align="right">
                      <span className="tabular-nums">
                        {composite.components[dim]}
                      </span>
                    </Td>
                    <Td align="right" className="text-neutral-500">
                      <Pct value={composite.weights[dim]} dp={0} />
                    </Td>
                    <Td align="right" className="font-semibold text-neutral-100">
                      <span className="tabular-nums">
                        {contribution.toFixed(1)}
                      </span>
                    </Td>
                    <Td align="right">
                      <Pct value={d?.confidence} dp={0} />
                    </Td>
                    <Td className="max-w-[38rem] whitespace-normal text-neutral-400">
                      {d?.rationale ?? "—"}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </ScrollTable>
      </Panel>

      <Callout tone="note">
        Upside magnitude and likelihood are computed separately and never blended
        into one figure. A candidate can carry a high asymmetry score and a low
        confidence score at the same time; that combination is information, not a
        contradiction.
      </Callout>
    </div>
  );
}

function Row({
  label: rowLabel,
  value,
  hint,
  tone = "normal",
  emphasis = false,
}: {
  label: string;
  value: string;
  hint: string;
  tone?: "normal" | "bad";
  emphasis?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <div className="min-w-0">
        <div
          className={`${emphasis ? "text-[13px] font-semibold text-neutral-100" : "text-neutral-300"}`}
        >
          {rowLabel}
        </div>
        <div className="text-[10px] leading-snug text-neutral-600">{hint}</div>
      </div>
      <div
        className={`shrink-0 tabular-nums ${
          emphasis
            ? "text-[22px] font-semibold text-amber-300"
            : tone === "bad"
              ? "text-[15px] text-rose-400"
              : "text-[15px] text-neutral-200"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
