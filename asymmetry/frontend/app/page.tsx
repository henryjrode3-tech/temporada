import { getStats, getTopOpportunities } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { OpportunityCard } from "@/components/OpportunityCard";
import { VerdictChip, VERDICT_DOT } from "@/components/VerdictChip";
import { EstimateLegend } from "@/components/Estimate";
import { Callout, Empty, PageHeader, SourceTag } from "@/components/ui";
import { formatDateTime, VERDICT_ORDER } from "@/lib/format";
import type { Verdict } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [stats, top] = await Promise.all([getStats(), getTopOpportunities(10)]);
  const s = stats.data;
  const total = Object.values(s.by_verdict).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Top asymmetric opportunities"
        subtitle="Ranked by composite score. Asymmetry measures the size of the upside relative to the downside; it deliberately says nothing about how likely that upside is, which is carried separately by confidence."
        right={<SourceTag source={top.source} error={top.error} />}
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        <StatCard label="Candidates tracked" value={s.total_candidates} />
        <StatCard
          label="Mean asymmetry"
          value={s.avg_asymmetry.toFixed(1)}
          accent
          hint="across all tracked candidates"
        />
        <StatCard
          label="Signals, 7d"
          value={s.signals_last_7d}
          hint="detected changes above threshold"
        />
        <StatCard
          label="Under active study"
          value={
            (s.by_verdict.TOP_OPPORTUNITY ?? 0) + (s.by_verdict.INVESTIGATE ?? 0)
          }
          hint="top opportunity + investigate"
        />
        <StatCard
          label="Theses in trouble"
          value={
            (s.by_verdict.THESIS_WEAKENING ?? 0) +
            (s.by_verdict.THESIS_INVALIDATED ?? 0)
          }
          hint="weakening or invalidated"
        />
        <StatCard
          label="Last pipeline run"
          value={
            <span className="text-[13px] font-medium">
              {formatDateTime(s.last_pipeline_run)}
            </span>
          }
          hint={`LLM mode: ${s.llm_mode}`}
        />
      </div>

      <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-[12px] font-semibold uppercase tracking-wider text-neutral-400">
            Verdict distribution
          </h2>
          <EstimateLegend />
        </div>
        <div className="flex h-2 w-full overflow-hidden rounded-full bg-neutral-800">
          {VERDICT_ORDER.filter((v) => s.by_verdict[v]).map((v) => (
            <div
              key={v}
              className={VERDICT_DOT[v as Verdict]}
              style={{ width: `${((s.by_verdict[v] ?? 0) / total) * 100}%` }}
              title={`${v}: ${s.by_verdict[v]}`}
            />
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
          {VERDICT_ORDER.filter((v) => s.by_verdict[v]).map((v) => (
            <span key={v} className="inline-flex items-center gap-1.5">
              <VerdictChip verdict={v} size="sm" />
              <span className="text-[12px] tabular-nums text-neutral-400">
                {s.by_verdict[v]}
              </span>
            </span>
          ))}
        </div>
      </div>

      <Callout tone="note">
        Every multiple, probability and score below is a model estimate produced
        from stated assumptions, not a forecast and not advice. Estimated figures
        are marked with a dotted underline. This system has no notion of an
        instruction to transact.
      </Callout>

      {top.data.length === 0 ? (
        <Empty>No ranked candidates returned.</Empty>
      ) : (
        <div className="space-y-3">
          {top.data.map((c) => (
            <OpportunityCard key={c.id} candidate={c} />
          ))}
        </div>
      )}
    </div>
  );
}
