import { BarChart, type BarDatum } from "@/components/BarChart";
import { Money } from "@/components/Money";
import { Multiple } from "@/components/Multiple";
import { Pct } from "@/components/Pct";
import { EstimateLegend } from "@/components/Estimate";
import { Callout, Panel, ScrollTable, Td, Th } from "@/components/ui";
import { formatMultiple, titleCase } from "@/lib/format";
import type { ScenarioName, ScenarioSet } from "@/lib/types";

const SCENARIO_COLOR: Record<ScenarioName, string> = {
  bear: "#fb7185",
  base: "#38bdf8",
  bull: "#34d399",
  extreme_bull: "#fbbf24",
};

const SCENARIO_LABEL: Record<ScenarioName, string> = {
  bear: "Bear",
  base: "Base",
  bull: "Bull",
  extreme_bull: "Extreme bull",
};

export function Scenarios({ set }: { set: ScenarioSet | null }) {
  if (!set) {
    return (
      <Panel title="Scenarios">
        <p className="text-[13px] text-neutral-500">
          No scenario set has been generated for this candidate.
        </p>
      </Panel>
    );
  }

  const bars: BarDatum[] = set.scenarios.map((s) => ({
    label: SCENARIO_LABEL[s.name],
    note: `p = ${(s.probability * 100).toFixed(0)}%`,
    value: s.per_share_multiple,
    display: formatMultiple(s.per_share_multiple),
    color: SCENARIO_COLOR[s.name],
    hatched: s.was_clamped,
  }));

  const clamped = set.scenarios.filter((s) => s.was_clamped);

  return (
    <div className="space-y-4">
      {set.is_tail_dominated ? (
        <Callout tone="warn" title="Expected value rests on one improbable branch">
          The extreme branch contributes{" "}
          <span className="tabular-nums">
            {(set.tail_contribution * 100).toFixed(0)}%
          </span>{" "}
          of the probability-weighted upside. The expected multiple of{" "}
          <span className="tabular-nums">
            {formatMultiple(set.expected_multiple)}
          </span>{" "}
          therefore describes an average nobody actually experiences. The median
          branch — <span className="tabular-nums">{formatMultiple(set.median_multiple)}</span>{" "}
          — is the better summary of a typical outcome, and the probability of
          ending below where it started is{" "}
          <span className="tabular-nums">
            {(set.probability_of_loss * 100).toFixed(0)}%
          </span>
          .
        </Callout>
      ) : null}

      {clamped.length > 0 ? (
        <Callout
          tone="accent"
          title={`${clamped.length} scenario${clamped.length > 1 ? "s were" : " was"} clamped by the model`}
        >
          <p className="mb-2">
            The engine reins in projections that imply growth rates or market
            shares outside what comparable businesses have achieved. The figures
            shown are the clamped ones; the reasons are recorded below.
          </p>
          <ul className="space-y-1.5">
            {clamped.map((s) => (
              <li key={s.name} className="flex gap-2">
                <span className="shrink-0 font-mono text-[11px] uppercase text-cyan-300/80">
                  {s.name}
                </span>
                <span className="text-cyan-100/70">{s.clamp_reason}</span>
              </li>
            ))}
          </ul>
        </Callout>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel
          title="Per-share multiple by branch"
          right={<EstimateLegend />}
        >
          <BarChart
            data={bars}
            baseline={1}
            baselineLabel="1.0x — capital preserved"
            ariaLabel="Per-share multiple by scenario"
          />
          <p className="mt-3 text-[11px] leading-relaxed text-neutral-600">
            Per-share multiples, so dilution assumed in each branch is already
            deducted. Hatched bars were clamped. Horizon:{" "}
            <span className="tabular-nums text-neutral-400">{set.years} years</span>{" "}
            from a current valuation of{" "}
            <span className="tabular-nums text-neutral-400">
              <Money value={set.current_market_cap} />
            </span>
            .
          </p>
        </Panel>

        <Panel title="Distribution summary" right={<EstimateLegend />}>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
            <Stat
              label="Median multiple"
              value={<Multiple value={set.median_multiple} estimate />}
              hint="typical branch"
              emphasis
            />
            <Stat
              label="Expected multiple"
              value={<Multiple value={set.expected_multiple} estimate />}
              hint="probability-weighted"
            />
            <Stat
              label="Expected value"
              value={<Money value={set.expected_value} estimate />}
              hint="mean terminal valuation"
            />
            <Stat
              label="P(below 1x)"
              value={<Pct value={set.probability_of_loss} estimate />}
              hint="capital not preserved"
            />
            <Stat
              label="P(10x or better)"
              value={<Pct value={set.probability_of_10x} estimate />}
              hint="per share"
            />
            <Stat
              label="Payoff ratio"
              value={
                <span className="tabular-nums">
                  {set.payoff_ratio.toFixed(1)}
                </span>
              }
              hint="expected gain / expected loss"
            />
            <Stat
              label="Asymmetry score"
              value={
                <span className="tabular-nums text-amber-300">
                  {set.asymmetry_score}
                </span>
              }
              hint="log-compressed payoff, 0-100"
            />
            <Stat
              label="Tail contribution"
              value={<Pct value={set.tail_contribution} estimate />}
              hint="share of upside from extreme branch"
            />
            <Stat
              label="Clamped branches"
              value={
                <span className="tabular-nums">
                  {set.clamped_scenarios.length}
                </span>
              }
              hint={
                set.clamped_scenarios.length
                  ? set.clamped_scenarios.join(", ")
                  : "none"
              }
            />
          </dl>
        </Panel>
      </div>

      <Panel title="Branch detail" right={<EstimateLegend />}>
        <ScrollTable>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Branch</Th>
                <Th align="right">P</Th>
                <Th align="right">Revenue</Th>
                <Th align="right">Earnings</Th>
                <Th align="right">Valuation</Th>
                <Th align="right">Mkt cap ×</Th>
                <Th align="right">Per share ×</Th>
                <Th align="right">CAGR</Th>
                <Th align="right">Per-share CAGR</Th>
                <Th align="right">Implied rev CAGR</Th>
                <Th>Path</Th>
                <Th>Clamp</Th>
              </tr>
            </thead>
            <tbody>
              {set.scenarios.map((s) => (
                <tr key={s.name} className="hover:bg-neutral-800/20">
                  <Td>
                    <span className="inline-flex items-center gap-1.5">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ backgroundColor: SCENARIO_COLOR[s.name] }}
                      />
                      <span className="text-neutral-200">
                        {SCENARIO_LABEL[s.name]}
                      </span>
                    </span>
                  </Td>
                  <Td align="right">
                    <Pct value={s.probability} estimate />
                  </Td>
                  <Td align="right">
                    <Money value={s.revenue} estimate />
                  </Td>
                  <Td align="right">
                    <Money value={s.earnings} estimate />
                  </Td>
                  <Td align="right">
                    <Money value={s.future_market_cap} estimate />
                  </Td>
                  <Td align="right">
                    <Multiple value={s.market_cap_multiple} estimate />
                  </Td>
                  <Td align="right" className="font-semibold text-neutral-100">
                    <Multiple value={s.per_share_multiple} estimate />
                  </Td>
                  <Td align="right">
                    <Pct value={s.cagr} dp={1} estimate />
                  </Td>
                  <Td align="right">
                    <Pct value={s.per_share_cagr} dp={1} estimate />
                  </Td>
                  <Td align="right">
                    <Pct value={s.implied_revenue_cagr} dp={1} estimate />
                  </Td>
                  <Td className="text-neutral-500">{s.valuation_path}</Td>
                  <Td>
                    {s.was_clamped ? (
                      <span className="rounded bg-cyan-500/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-cyan-300 ring-1 ring-inset ring-cyan-500/30">
                        clamped
                      </span>
                    ) : (
                      <span className="text-neutral-700">—</span>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollTable>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        {set.scenarios.map((s) => (
          <Panel
            key={s.name}
            title={
              <span className="flex items-center gap-2">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: SCENARIO_COLOR[s.name] }}
                />
                {SCENARIO_LABEL[s.name]}
                <span className="font-normal normal-case tracking-normal text-neutral-500">
                  p = {(s.probability * 100).toFixed(0)}% ·{" "}
                  {formatMultiple(s.per_share_multiple)} per share
                </span>
              </span>
            }
          >
            <p className="text-[13px] leading-relaxed text-neutral-400">
              {s.narrative}
            </p>

            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">
                What has to happen
              </div>
              <ul className="mt-1.5 space-y-1">
                {s.drivers.map((d) => (
                  <li
                    key={d}
                    className="flex gap-2 text-[12px] leading-relaxed text-neutral-400"
                  >
                    <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-neutral-600" />
                    {d}
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">
                Assumptions
              </div>
              <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
                {Object.entries(s.assumptions).map(([k, v]) => (
                  <span key={k} className="text-[11px] text-neutral-500">
                    {titleCase(k)}{" "}
                    <span className="tabular-nums text-neutral-300">
                      {v === null ? "—" : v}
                    </span>
                  </span>
                ))}
              </div>
            </div>

            {s.was_clamped ? (
              <div className="mt-3 rounded border border-cyan-500/25 bg-cyan-500/[0.05] px-2.5 py-2 text-[11px] leading-relaxed text-cyan-100/70">
                <span className="font-semibold uppercase tracking-wider text-cyan-300">
                  Clamped ·{" "}
                </span>
                {s.clamp_reason}
              </div>
            ) : null}
          </Panel>
        ))}
      </div>

      <Callout tone="note" title="Disclaimer">
        {set.disclaimer}
      </Callout>
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  emphasis = false,
}: {
  label: string;
  value: React.ReactNode;
  hint: string;
  emphasis?: boolean;
}) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wider text-neutral-500">
        {label}
      </dt>
      <dd
        className={`mt-0.5 font-semibold tabular-nums ${
          emphasis ? "text-[19px] text-neutral-50" : "text-[16px] text-neutral-100"
        }`}
      >
        {value}
      </dd>
      <div className="text-[10px] leading-snug text-neutral-600">{hint}</div>
    </div>
  );
}
