import Link from "next/link";
import { getCandidates } from "@/lib/api";
import { Money } from "@/components/Money";
import { Multiple } from "@/components/Multiple";
import { Pct } from "@/components/Pct";
import { VerdictChip } from "@/components/VerdictChip";
import { EstimateLegend } from "@/components/Estimate";
import { Callout, Empty, PageHeader, Panel, ScrollTable, SourceTag, Td, Th } from "@/components/ui";
import { relativeAge, VERDICT_ORDER } from "@/lib/format";
import type { Candidate, Verdict } from "@/lib/types";

export const dynamic = "force-dynamic";

const VERDICT_NOTE: Record<Verdict, string> = {
  TOP_OPPORTUNITY:
    "Strongest asymmetry with the evidence to support it. Under continuous review.",
  INVESTIGATE:
    "Thesis is plausible and the next step is specific work, not more reading.",
  WATCH:
    "Right idea, wrong price or too early. Revisit on a named trigger rather than on a schedule.",
  INTERESTING:
    "Genuinely good business, limited asymmetry. Kept for context and comparison.",
  HIGH_RISK:
    "Distribution is wide and the downside branch is severe. Sized as an option if at all.",
  THESIS_WEAKENING:
    "Conditions written in advance are moving against the thesis. Conviction reduced.",
  THESIS_INVALIDATED:
    "A falsifying condition has failed on evidence. Retained as a record of what went wrong.",
  REJECTED:
    "Screened out deterministically. No analytical budget was spent.",
};

export default async function WatchlistPage() {
  const res = await getCandidates({ limit: 200 });
  const groups = VERDICT_ORDER.map((v) => ({
    verdict: v,
    items: res.data.items
      .filter((c) => c.verdict === v)
      .sort((a, b) => b.overall_score - a.overall_score),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Watchlist"
        subtitle="Grouped by research posture. A verdict says what to do with attention, never what to do with capital."
        right={<SourceTag source={res.source} error={res.error} />}
      />

      <Callout tone="note">
        Verdicts are research states. The engine has no vocabulary for an
        instruction to transact and does not compute one.
      </Callout>

      {groups.length === 0 ? (
        <Empty>No candidates returned.</Empty>
      ) : (
        groups.map((g) => (
          <Panel
            key={g.verdict}
            title={
              <span className="flex flex-wrap items-center gap-2">
                <VerdictChip verdict={g.verdict} size="sm" />
                <span className="font-normal normal-case tracking-normal text-neutral-500">
                  {g.items.length} candidate{g.items.length > 1 ? "s" : ""}
                </span>
              </span>
            }
            right={<EstimateLegend />}
          >
            <p className="mb-3 text-[12px] leading-relaxed text-neutral-500">
              {VERDICT_NOTE[g.verdict]}
            </p>
            <GroupTable items={g.items} />
          </Panel>
        ))
      )}
    </div>
  );
}

function GroupTable({ items }: { items: Candidate[] }) {
  return (
    <ScrollTable>
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <Th>Candidate</Th>
            <Th>Sector</Th>
            <Th align="right">Valuation</Th>
            <Th align="right">Asymmetry</Th>
            <Th align="right">Overall</Th>
            <Th align="right">Confidence</Th>
            <Th align="right">Median ×</Th>
            <Th align="right">P(loss)</Th>
            <Th>Latest signal</Th>
            <Th align="right">Updated</Th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
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
                <Money value={c.current_market_cap} />
              </Td>
              <Td align="right" className="font-semibold text-amber-300">
                <span className="tabular-nums">{c.asymmetry_score}</span>
              </Td>
              <Td align="right">
                <span className="tabular-nums">{c.overall_score.toFixed(1)}</span>
              </Td>
              <Td align="right" className="text-neutral-400">
                <span className="tabular-nums">{c.confidence_score.toFixed(0)}</span>
              </Td>
              <Td align="right">
                <Multiple value={c.scenario_summary?.median_multiple} estimate />
              </Td>
              <Td align="right">
                <Pct value={c.scenario_summary?.probability_of_loss} estimate />
              </Td>
              <Td className="max-w-[22rem] truncate text-neutral-500">
                {c.latest_signal ? (
                  <>
                    <span className="font-mono text-[11px] text-neutral-400">
                      {c.latest_signal.signal_type}
                    </span>{" "}
                    <span className="text-neutral-600">
                      {c.latest_signal.strength}
                    </span>
                  </>
                ) : (
                  "—"
                )}
              </Td>
              <Td align="right" className="text-neutral-500">
                {relativeAge(c.last_updated)}
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollTable>
  );
}
