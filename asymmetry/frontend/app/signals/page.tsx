import { getSignalFeed } from "@/lib/api";
import { SignalCard } from "@/components/SignalCard";
import { StatCard } from "@/components/StatCard";
import { Callout, Empty, PageHeader, Panel, SourceTag } from "@/components/ui";
import { STRENGTH_ORDER } from "@/lib/format";
import type { SignalStrength } from "@/lib/types";

export const dynamic = "force-dynamic";

const STRENGTH_NOTE: Record<SignalStrength, string> = {
  extreme:
    "Departures large enough that the baseline is unlikely to be the right model any more.",
  strong: "Clear departures from baseline that change what is worth checking next.",
  moderate: "Real movement, not yet decisive on its own.",
  weak: "Recorded for completeness; below the significance threshold.",
};

export default async function SignalsPage() {
  const res = await getSignalFeed(80);
  const feed = res.data;

  const counts = STRENGTH_ORDER.map((s) => ({
    strength: s,
    n: feed.filter((f) => f.signal.strength === s).length,
  }));

  return (
    <div className="space-y-5">
      <PageHeader
        title="Signal feed"
        subtitle="Measured departures from a baseline: hiring, filings, patents, procurement, yields, utilisation. Signals are evidence about the world, not opinions about a price."
        right={<SourceTag source={res.source} error={res.error} />}
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <StatCard label="Signals in feed" value={feed.length} />
        {counts.map((c) => (
          <StatCard
            key={c.strength}
            label={c.strength}
            value={c.n}
            accent={c.strength === "extreme"}
            hint={STRENGTH_NOTE[c.strength]}
          />
        ))}
      </div>

      <Callout tone="note">
        A signal is a change in a measurable quantity against its own history. It
        carries a z-score so that a large percentage move on a tiny base is not
        mistaken for a large event. Signals that run against a thesis are shown
        with the same prominence as those that support it.
      </Callout>

      {STRENGTH_ORDER.map((strength) => {
        const items = feed.filter((f) => f.signal.strength === strength);
        if (items.length === 0) return null;
        return (
          <Panel
            key={strength}
            title={
              <span className="flex items-center gap-2">
                {strength}
                <span className="font-normal normal-case tracking-normal text-neutral-500">
                  {items.length}
                </span>
              </span>
            }
          >
            <div className="grid gap-3 lg:grid-cols-2">
              {items.map((f, i) => (
                <SignalCard
                  key={`${f.signal.signal_type}-${f.signal.detected_at}-${i}`}
                  signal={f.signal}
                  candidateName={f.candidate_name}
                  candidateId={f.candidate_id}
                  ticker={f.ticker}
                />
              ))}
            </div>
          </Panel>
        );
      })}

      {feed.length === 0 ? <Empty>No signals returned.</Empty> : null}
    </div>
  );
}
