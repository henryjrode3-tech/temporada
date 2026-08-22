import { Money } from "@/components/Money";
import { Pct } from "@/components/Pct";
import { EstimateLegend } from "@/components/Estimate";
import { Callout, Panel, ScrollTable, Td, Th } from "@/components/ui";
import { formatMultiple } from "@/lib/format";
import type { Milestone, ReverseValuation } from "@/lib/types";

export function Valuation({
  reverse,
  milestones,
  currentMarketCap,
  currentRevenue,
}: {
  reverse: ReverseValuation | null;
  milestones: Milestone[];
  currentMarketCap: number | null;
  currentRevenue: number | null;
}) {
  const reachable = milestones.filter((m) => m.reachable);
  const ceiling = reachable[reachable.length - 1];

  return (
    <div className="space-y-4">
      {reverse ? (
        <Panel title="Reverse valuation" right={<EstimateLegend />}>
          <div className="grid gap-4 lg:grid-cols-[minmax(0,18rem)_1fr]">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 lg:grid-cols-1">
              <Field
                label={`Revenue required in ${reverse.years} years`}
                value={<Money value={reverse.required_revenue} estimate />}
              />
              <Field
                label="Implied market share"
                value={
                  <Pct value={reverse.required_market_share} dp={0} estimate />
                }
              />
              <Field
                label="From today's revenue"
                value={<Money value={currentRevenue} />}
              />
              <Field
                label="From today's valuation"
                value={<Money value={currentMarketCap} />}
              />
            </dl>
            <div className="rounded-md border border-neutral-800 bg-neutral-950/40 p-3">
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">
                What the price is already asking for
              </div>
              <p className="mt-1.5 text-[13px] leading-relaxed text-neutral-300">
                {reverse.verdict}
              </p>
            </div>
          </div>
        </Panel>
      ) : null}

      <Panel
        title="Milestone ladder"
        right={
          ceiling ? (
            <span className="text-[11px] text-neutral-500">
              highest modelled reachable rung:{" "}
              <span className="text-neutral-300">{ceiling.label}</span>
            </span>
          ) : null
        }
      >
        <ScrollTable>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Rung</Th>
                <Th align="center">Modelled reachable</Th>
                <Th align="right">Revenue required</Th>
                <Th align="right">Market share required</Th>
                <Th align="right">Multiple from here</Th>
                <Th align="right">Implied CAGR</Th>
                <Th>Commentary</Th>
              </tr>
            </thead>
            <tbody>
              {milestones.map((m) => (
                <tr
                  key={m.label}
                  className={m.reachable ? "hover:bg-neutral-800/20" : "opacity-55"}
                >
                  <Td className="font-medium text-neutral-100">{m.label}</Td>
                  <Td align="center">
                    {m.reachable ? (
                      <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-emerald-300 ring-1 ring-inset ring-emerald-500/30">
                        yes
                      </span>
                    ) : (
                      <span className="rounded bg-neutral-800 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-neutral-500 ring-1 ring-inset ring-neutral-700">
                        rejected
                      </span>
                    )}
                  </Td>
                  <Td align="right">
                    <Money value={m.required_revenue} estimate />
                  </Td>
                  <Td align="right">
                    <Pct value={m.required_market_share} dp={0} estimate />
                  </Td>
                  <Td align="right">{formatMultiple(m.multiple_from_here, 0)}</Td>
                  <Td align="right">
                    <Pct value={m.implied_cagr} dp={1} estimate />
                  </Td>
                  <Td className="max-w-[34rem] whitespace-normal text-neutral-400">
                    {m.commentary}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollTable>
      </Panel>

      <Callout tone="note">
        The ladder is read from the top down: each rung states the revenue and
        market share the business would have to reach for that multiple to make
        arithmetic sense. Rungs marked rejected exceed the modelled market or
        require a growth rate no comparable business has sustained, and the
        engine refuses to publish them as outcomes.
      </Callout>
    </div>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wider text-neutral-500">
        {label}
      </dt>
      <dd className="mt-0.5 text-[17px] font-semibold tabular-nums text-neutral-100">
        {value}
      </dd>
    </div>
  );
}
