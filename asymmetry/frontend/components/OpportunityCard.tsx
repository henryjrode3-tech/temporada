import Link from "next/link";
import { Money } from "./Money";
import { Multiple } from "./Multiple";
import { Pct } from "./Pct";
import { ScoreBadge } from "./ScoreBadge";
import { VerdictChip } from "./VerdictChip";
import { AsymmetryGauge } from "./AsymmetryGauge";
import { RankDelta } from "./ui";
import { STRENGTH_STYLE } from "./SignalCard";
import { formatPct, relativeAge } from "@/lib/format";
import type { Candidate } from "@/lib/types";

export function OpportunityCard({ candidate }: { candidate: Candidate }) {
  const s = candidate.scenario_summary;
  const signal = candidate.latest_signal;

  return (
    <article className="group rounded-lg border border-neutral-800 bg-neutral-900/40 transition-colors hover:border-neutral-700">
      <div className="flex flex-col gap-4 p-4 xl:flex-row">
        {/* Identity */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex h-6 min-w-6 items-center justify-center rounded bg-neutral-800 px-1.5 text-[12px] font-semibold tabular-nums text-amber-300">
              {candidate.rank ?? "—"}
            </span>
            <RankDelta change={candidate.rank_change} />
            <Link
              href={`/opportunities/${candidate.id}`}
              className="truncate text-[15px] font-semibold text-neutral-100 underline-offset-2 hover:text-amber-300 hover:underline"
            >
              {candidate.name}
            </Link>
            {candidate.ticker ? (
              <span className="font-mono text-[11px] text-neutral-500">
                {candidate.ticker}
              </span>
            ) : null}
            <VerdictChip verdict={candidate.verdict} size="sm" />
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-neutral-500">
            <span className="text-neutral-400">{candidate.sector}</span>
            {candidate.industry ? (
              <>
                <span className="text-neutral-700">/</span>
                <span>{candidate.industry}</span>
              </>
            ) : null}
            <span className="text-neutral-700">·</span>
            <span>updated {relativeAge(candidate.last_updated)}</span>
          </div>

          <p className="mt-2.5 text-[13px] leading-relaxed text-neutral-400">
            {candidate.description}
          </p>

          <p className="mt-2 border-l-2 border-neutral-800 pl-2.5 text-[12px] leading-relaxed text-neutral-500">
            <span className="text-neutral-600">Why it is on the list: </span>
            {candidate.verdict_reason}
          </p>

          <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-[11px]">
            <div>
              <dt className="inline text-neutral-600">Valuation </dt>
              <dd className="inline tabular-nums text-neutral-200">
                <Money value={candidate.current_market_cap} />
              </dd>
            </div>
            <div>
              <dt className="inline text-neutral-600">Revenue </dt>
              <dd className="inline tabular-nums text-neutral-200">
                <Money value={candidate.revenue} />
              </dd>
            </div>
            <div>
              <dt className="inline text-neutral-600">Growth </dt>
              <dd className="inline">
                <Pct value={candidate.revenue_growth} tone="signed" signed />
              </dd>
            </div>
            <div>
              <dt className="inline text-neutral-600">Net cash </dt>
              <dd className="inline tabular-nums text-neutral-200">
                <Money
                  value={
                    candidate.cash !== null && candidate.debt !== null
                      ? candidate.cash - candidate.debt
                      : null
                  }
                  signed
                />
              </dd>
            </div>
          </dl>

          {signal ? (
            <div className="mt-3 flex flex-wrap items-start gap-2 rounded-md border border-neutral-800 bg-neutral-950/40 px-2.5 py-2">
              <span
                className={`mt-0.5 inline-flex shrink-0 items-center rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ring-1 ring-inset ${STRENGTH_STYLE[signal.strength].chip}`}
              >
                {signal.strength}
              </span>
              <span className="min-w-0 flex-1 text-[12px] leading-relaxed text-neutral-400">
                <span className="font-mono text-[11px] text-neutral-500">
                  {signal.signal_type}
                </span>{" "}
                <span className="tabular-nums text-neutral-300">
                  {formatPct(signal.pct_change, { signed: true })}
                </span>{" "}
                — {signal.description}
              </span>
            </div>
          ) : null}
        </div>

        {/* Figures */}
        <div className="flex shrink-0 flex-col gap-3 border-neutral-800 xl:w-[19rem] xl:border-l xl:pl-4">
          <div className="flex items-start gap-4">
            <AsymmetryGauge
              value={candidate.asymmetry_score}
              size={116}
              sublabel="upside magnitude only"
            />
            <div className="flex flex-1 flex-col gap-2.5">
              <ScoreBadge label="Overall" value={candidate.overall_score} size="sm" />
              <ScoreBadge
                label="Confidence"
                value={candidate.confidence_score}
                tone="neutral"
                size="sm"
              />
              <ScoreBadge
                label="Risk"
                value={candidate.risk_score}
                tone="bad"
                size="sm"
              />
            </div>
          </div>

          {s ? (
            <div className="grid grid-cols-3 gap-2 rounded-md border border-neutral-800 bg-neutral-950/40 p-2.5">
              <Figure
                label="Median"
                value={<Multiple value={s.median_multiple} estimate />}
                hint="typical branch"
              />
              <Figure
                label="Expected"
                value={<Multiple value={s.expected_multiple} estimate />}
                hint="prob-weighted"
              />
              <Figure
                label="P(loss)"
                value={<Pct value={s.probability_of_loss} estimate />}
                hint="below 1x"
              />
            </div>
          ) : null}

          {s?.is_tail_dominated ? (
            <p className="rounded-md border border-amber-500/30 bg-amber-500/[0.06] px-2.5 py-2 text-[11px] leading-relaxed text-amber-200/80">
              Tail-dominated: the expected multiple rests mostly on one
              improbable branch. Read the median as the typical outcome.
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function Figure({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint: string;
}) {
  return (
    <div className="min-w-0">
      <div className="text-[10px] uppercase tracking-wider text-neutral-500">
        {label}
      </div>
      <div className="text-[15px] font-semibold tabular-nums text-neutral-100">
        {value}
      </div>
      <div className="truncate text-[10px] text-neutral-600">{hint}</div>
    </div>
  );
}
