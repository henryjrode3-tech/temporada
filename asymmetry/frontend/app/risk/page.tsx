import Link from "next/link";
import { getCandidates } from "@/lib/api";
import { Money } from "@/components/Money";
import { Multiple } from "@/components/Multiple";
import { Pct } from "@/components/Pct";
import { StatCard } from "@/components/StatCard";
import { VerdictChip } from "@/components/VerdictChip";
import { EstimateLegend } from "@/components/Estimate";
import {
  Callout,
  Empty,
  PageHeader,
  Panel,
  ScrollTable,
  SourceTag,
  Td,
  Th,
} from "@/components/ui";

export const dynamic = "force-dynamic";

function riskBand(score: number): { label: string; cls: string } {
  if (score >= 75) return { label: "severe", cls: "text-rose-400" };
  if (score >= 50) return { label: "elevated", cls: "text-orange-400" };
  if (score >= 25) return { label: "moderate", cls: "text-amber-400" };
  return { label: "contained", cls: "text-neutral-400" };
}

export default async function RiskPage() {
  const res = await getCandidates({ limit: 200 });
  const items = [...res.data.items].sort((a, b) => {
    if (b.red_flag_score !== a.red_flag_score)
      return b.red_flag_score - a.red_flag_score;
    return b.risk_score - a.risk_score;
  });

  const tailDominated = items.filter(
    (c) => c.scenario_summary?.is_tail_dominated,
  );
  const meanRedFlag =
    items.length > 0
      ? items.reduce((a, c) => a + c.red_flag_score, 0) / items.length
      : 0;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Risk register"
        subtitle="Sorted by red-flag weight. Red-flag points are subtracted from the composite in the open, so a low score here is the difference between a good business and a good-looking one."
        right={<SourceTag source={res.source} error={res.error} />}
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Candidates" value={items.length} />
        <StatCard
          label="Mean red-flag score"
          value={meanRedFlag.toFixed(1)}
          hint="lower is better"
        />
        <StatCard
          label="Severe risk (75+)"
          value={items.filter((c) => c.risk_score >= 75).length}
          accent
        />
        <StatCard
          label="Tail-dominated"
          value={tailDominated.length}
          hint="expected value rests on one improbable branch"
        />
      </div>

      {tailDominated.length > 0 ? (
        <Callout tone="warn" title="Tail-dominated distributions">
          For{" "}
          {tailDominated.map((c, i) => (
            <span key={c.id}>
              {i > 0 ? ", " : ""}
              <Link
                href={`/opportunities/${c.id}`}
                className="underline underline-offset-2 hover:text-amber-100"
              >
                {c.name}
              </Link>
            </span>
          ))}
          , most of the probability-weighted upside comes from a single
          improbable branch. The expected multiple describes an average that no
          individual outcome resembles; the median is the honest summary.
        </Callout>
      ) : null}

      <Panel title="Red-flag ranking" right={<EstimateLegend />}>
        {items.length === 0 ? (
          <Empty>No candidates returned.</Empty>
        ) : (
          <ScrollTable>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <Th>Candidate</Th>
                  <Th>Sector</Th>
                  <Th align="right">Red flags</Th>
                  <Th align="right">Risk</Th>
                  <Th>Band</Th>
                  <Th align="right">Confidence</Th>
                  <Th align="right">P(loss)</Th>
                  <Th align="right">Median ×</Th>
                  <Th align="right">Expected ×</Th>
                  <Th>Tail</Th>
                  <Th align="right">Valuation</Th>
                  <Th>Verdict</Th>
                </tr>
              </thead>
              <tbody>
                {items.map((c) => {
                  const band = riskBand(c.risk_score);
                  return (
                    <tr key={c.id} className="hover:bg-neutral-800/20">
                      <Td>
                        <Link
                          href={`/opportunities/${c.id}`}
                          className="font-medium text-neutral-100 underline-offset-2 hover:text-amber-300 hover:underline"
                        >
                          {c.name}
                        </Link>
                        {c.ticker ? (
                          <span className="ml-2 font-mono text-[11px] text-neutral-600">
                            {c.ticker}
                          </span>
                        ) : null}
                      </Td>
                      <Td className="text-neutral-400">{c.sector}</Td>
                      <Td align="right">
                        <span className="inline-flex items-center gap-2">
                          <span className="h-1 w-12 overflow-hidden rounded-full bg-neutral-800">
                            <span
                              className="block h-full rounded-full bg-rose-500"
                              style={{
                                width: `${Math.min(100, c.red_flag_score)}%`,
                              }}
                            />
                          </span>
                          <span className="tabular-nums text-neutral-200">
                            {c.red_flag_score}
                          </span>
                        </span>
                      </Td>
                      <Td align="right" className={band.cls}>
                        <span className="tabular-nums">{c.risk_score}</span>
                      </Td>
                      <Td className={`uppercase ${band.cls}`}>
                        <span className="text-[10px] tracking-wider">
                          {band.label}
                        </span>
                      </Td>
                      <Td align="right" className="text-neutral-400">
                        <span className="tabular-nums">
                          {c.confidence_score.toFixed(0)}
                        </span>
                      </Td>
                      <Td align="right">
                        <Pct
                          value={c.scenario_summary?.probability_of_loss}
                          estimate
                        />
                      </Td>
                      <Td align="right">
                        <Multiple
                          value={c.scenario_summary?.median_multiple}
                          estimate
                        />
                      </Td>
                      <Td align="right" className="text-neutral-400">
                        <Multiple
                          value={c.scenario_summary?.expected_multiple}
                          estimate
                        />
                      </Td>
                      <Td>
                        {c.scenario_summary?.is_tail_dominated ? (
                          <span
                            title="Expected value rests on one improbable branch — read the median instead"
                            className="rounded bg-amber-500/12 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-amber-300 ring-1 ring-inset ring-amber-500/30"
                          >
                            dominated
                          </span>
                        ) : (
                          <span className="text-neutral-700">—</span>
                        )}
                      </Td>
                      <Td align="right">
                        <Money value={c.current_market_cap} />
                      </Td>
                      <Td>
                        <VerdictChip verdict={c.verdict} size="sm" />
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </ScrollTable>
        )}
      </Panel>
    </div>
  );
}
