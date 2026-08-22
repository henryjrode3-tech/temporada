import Link from "next/link";
import { notFound } from "next/navigation";
import { getCandidate } from "@/lib/api";
import { Tabs, type TabDef } from "@/components/detail/Tabs";
import { Overview } from "@/components/detail/Overview";
import { Scenarios } from "@/components/detail/Scenarios";
import { Valuation } from "@/components/detail/Valuation";
import { Scores } from "@/components/detail/Scores";
import { Risks } from "@/components/detail/Risks";
import { ThesisPanel } from "@/components/detail/ThesisPanel";
import { Debate } from "@/components/detail/Debate";
import { Sources } from "@/components/detail/Sources";
import { SignalCard } from "@/components/SignalCard";
import { VerdictChip } from "@/components/VerdictChip";
import { Money } from "@/components/Money";
import { Empty, Panel, RankDelta, SourceTag } from "@/components/ui";
import { relativeAge } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function CandidatePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const res = await getCandidate(id);
  const c = res.data;
  if (!c) notFound();

  const brokenConditions =
    c.thesis?.conditions.filter((x) => x.status === "broken").length ?? 0;
  const seriousFlags =
    c.red_flags?.flags.filter(
      (f) => f.severity === "critical" || f.severity === "high",
    ).length ?? 0;

  const tabs: TabDef[] = [
    { id: "overview", label: "Overview" },
    {
      id: "scenarios",
      label: "Scenarios",
      badge: c.scenarios?.clamped_scenarios.length
        ? `${c.scenarios.clamped_scenarios.length} clamped`
        : undefined,
    },
    { id: "valuation", label: "Valuation" },
    { id: "scores", label: "Scores" },
    { id: "signals", label: "Signals", badge: c.signals.length },
    {
      id: "risks",
      label: "Risks",
      badge: seriousFlags || c.red_flags?.flags.length,
      alert: seriousFlags > 0,
    },
    {
      id: "thesis",
      label: "Thesis",
      badge: brokenConditions ? `${brokenConditions} broken` : undefined,
      alert: brokenConditions > 0,
    },
    { id: "debate", label: "AI debate", badge: c.debate.length },
    { id: "sources", label: "Sources", badge: c.claims.length },
  ];

  const panels = [
    <Overview key="overview" c={c} />,
    <Scenarios key="scenarios" set={c.scenarios} />,
    <Valuation
      key="valuation"
      reverse={c.reverse_valuation}
      milestones={c.milestones}
      currentMarketCap={c.current_market_cap}
      currentRevenue={c.revenue}
    />,
    <Scores key="scores" composite={c.composite} dimensions={c.dimension_scores} />,
    <Panel key="signals" title={`Detected signals (${c.signals.length})`}>
      {c.signals.length === 0 ? (
        <Empty>No signals recorded for this candidate.</Empty>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {c.signals.map((s) => (
            <SignalCard key={s.detected_at + s.signal_type} signal={s} />
          ))}
        </div>
      )}
    </Panel>,
    <Risks key="risks" report={c.red_flags} />,
    <ThesisPanel key="thesis" thesis={c.thesis} />,
    <Debate key="debate" turns={c.debate} />,
    <Sources key="sources" claims={c.claims} />,
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-[12px] text-neutral-500">
        <Link href="/" className="underline-offset-2 hover:text-amber-300 hover:underline">
          Opportunities
        </Link>
        <span className="text-neutral-700">/</span>
        <span className="text-neutral-400">{c.name}</span>
        <span className="ml-auto">
          <SourceTag source={res.source} error={res.error} />
        </span>
      </div>

      <header className="border-b border-neutral-800 pb-4">
        <div className="flex flex-wrap items-center gap-2.5">
          {c.rank !== null ? (
            <span className="inline-flex h-7 min-w-7 items-center justify-center rounded bg-neutral-800 px-2 text-[13px] font-semibold tabular-nums text-amber-300">
              {c.rank}
            </span>
          ) : (
            <span
              title="Not ranked — screened out or thesis closed"
              className="inline-flex h-7 items-center rounded bg-neutral-800/60 px-2 text-[11px] uppercase tracking-wider text-neutral-500"
            >
              unranked
            </span>
          )}
          <RankDelta change={c.rank_change} />
          <h1 className="text-xl font-semibold tracking-tight text-neutral-50">
            {c.name}
          </h1>
          {c.ticker ? (
            <span className="font-mono text-[13px] text-neutral-500">
              {c.ticker}
            </span>
          ) : null}
          <VerdictChip verdict={c.verdict} />
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[12px] text-neutral-500">
          <span className="text-neutral-400">{c.sector}</span>
          {c.industry ? (
            <>
              <span className="text-neutral-700">/</span>
              <span>{c.industry}</span>
            </>
          ) : null}
          <span className="text-neutral-700">·</span>
          <span className="tabular-nums">
            <Money value={c.current_market_cap} />
          </span>
          <span className="text-neutral-700">·</span>
          <span>updated {relativeAge(c.last_updated)}</span>
        </div>
      </header>

      <Tabs tabs={tabs} panels={panels} />
    </div>
  );
}
