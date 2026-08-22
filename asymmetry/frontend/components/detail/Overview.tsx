import { AsymmetryGauge } from "@/components/AsymmetryGauge";
import { ScoreBadge } from "@/components/ScoreBadge";
import { Money } from "@/components/Money";
import { Multiple } from "@/components/Multiple";
import { Pct } from "@/components/Pct";
import { SignalCard } from "@/components/SignalCard";
import { EstimateLegend } from "@/components/Estimate";
import { Callout, Panel } from "@/components/ui";
import { ScoreHistory } from "./ScoreHistory";
import { formatDate } from "@/lib/format";
import type { CandidateDetail } from "@/lib/types";

export function Overview({ c }: { c: CandidateDetail }) {
  const s = c.scenarios;
  const netCash =
    c.cash !== null && c.debt !== null ? c.cash - c.debt : null;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <Panel title="What this is">
          <p className="text-[14px] leading-relaxed text-neutral-300">
            {c.description}
          </p>
          <div className="mt-3 border-t border-neutral-800 pt-3">
            <div className="text-[10px] uppercase tracking-wider text-neutral-500">
              Why the engine reached this verdict
            </div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-neutral-400">
              {c.verdict_reason}
            </p>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 border-t border-neutral-800 pt-3 sm:grid-cols-3">
            <Field label="Current valuation" value={<Money value={c.current_market_cap} />} />
            <Field label="Revenue" value={<Money value={c.revenue} />} />
            <Field
              label="Revenue growth"
              value={<Pct value={c.revenue_growth} tone="signed" signed />}
            />
            <Field label="Cash" value={<Money value={c.cash} />} />
            <Field label="Debt" value={<Money value={c.debt} />} />
            <Field label="Net cash" value={<Money value={netCash} signed />} />
            <Field label="Asset type" value={<span className="text-[14px]">{c.asset_type.replace(/_/g, " ")}</span>} />
            <Field label="Discovered" value={<span className="text-[14px]">{formatDate(c.discovery_date)}</span>} />
            <Field label="Last updated" value={<span className="text-[14px]">{formatDate(c.last_updated)}</span>} />
          </dl>
        </Panel>

        <Panel title="Scores" right={<EstimateLegend />}>
          <div className="flex justify-center">
            <AsymmetryGauge
              value={c.asymmetry_score}
              size={150}
              sublabel="Size of the upside relative to the downside. Says nothing about likelihood."
            />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 border-t border-neutral-800 pt-4">
            <ScoreBadge label="Overall" value={c.overall_score} />
            <ScoreBadge label="Confidence" value={c.confidence_score} tone="neutral" />
            <ScoreBadge label="Risk" value={c.risk_score} tone="bad" />
            <ScoreBadge label="Red flags" value={c.red_flag_score} tone="bad" />
          </div>
        </Panel>
      </div>

      {s ? (
        <Panel title="Scenario summary" right={<EstimateLegend />}>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Big
              label="Median multiple"
              value={<Multiple value={s.median_multiple} estimate />}
              hint={`over ${s.years} years, per share`}
              emphasis
            />
            <Big
              label="Expected multiple"
              value={<Multiple value={s.expected_multiple} estimate />}
              hint="probability-weighted"
            />
            <Big
              label="P(below 1x)"
              value={<Pct value={s.probability_of_loss} estimate />}
              hint="capital not preserved"
            />
            <Big
              label="P(10x or better)"
              value={<Pct value={s.probability_of_10x} estimate />}
              hint="per share"
            />
          </div>
          {s.is_tail_dominated ? (
            <div className="mt-4">
              <Callout tone="warn" title="Tail-dominated distribution">
                {(s.tail_contribution * 100).toFixed(0)}% of the
                probability-weighted upside comes from the single extreme branch.
                Read the median, not the mean: the expected multiple describes an
                average that no individual outcome resembles.
              </Callout>
            </div>
          ) : null}
          {s.clamped_scenarios.length > 0 ? (
            <div className="mt-3">
              <Callout tone="accent" title="Clamped projections">
                {s.clamped_scenarios.length} branch
                {s.clamped_scenarios.length > 1 ? "es were" : " was"} reined in by
                the model ({s.clamped_scenarios.join(", ")}). The reasons are
                recorded in full on the Scenarios tab.
              </Callout>
            </div>
          ) : null}
        </Panel>
      ) : null}

      <ScoreHistory history={c.score_history} />

      {c.signals.length > 0 ? (
        <Panel title="Most recent signals">
          <div className="grid gap-3 lg:grid-cols-2">
            {c.signals.slice(0, 2).map((sig) => (
              <SignalCard key={sig.detected_at + sig.signal_type} signal={sig} />
            ))}
          </div>
        </Panel>
      ) : null}
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wider text-neutral-500">
        {label}
      </dt>
      <dd className="mt-0.5 text-[15px] font-medium tabular-nums text-neutral-100">
        {value}
      </dd>
    </div>
  );
}

function Big({
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
      <div className="text-[10px] uppercase tracking-wider text-neutral-500">
        {label}
      </div>
      <div
        className={`mt-0.5 font-semibold tabular-nums ${
          emphasis ? "text-[26px] text-amber-300" : "text-[22px] text-neutral-100"
        }`}
      >
        {value}
      </div>
      <div className="text-[10px] text-neutral-600">{hint}</div>
    </div>
  );
}
