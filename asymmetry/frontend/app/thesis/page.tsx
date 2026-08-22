import Link from "next/link";
import { getTheses } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { CONDITION_STYLE } from "@/components/detail/ThesisPanel";
import { Callout, Empty, PageHeader, Panel, SourceTag } from "@/components/ui";
import { formatDate, titleCase } from "@/lib/format";
import type { ConditionStatus, ThesisEntry } from "@/lib/types";

export const dynamic = "force-dynamic";

const ORDER: ConditionStatus[] = ["broken", "at_risk", "unknown", "holding"];

function countBy(t: ThesisEntry, status: ConditionStatus): number {
  return t.conditions.filter((c) => c.status === status).length;
}

/** Theses with broken conditions come first — a failed prediction is the most
 *  informative thing on this page. */
function severity(t: ThesisEntry): number {
  return countBy(t, "broken") * 100 + countBy(t, "at_risk") * 10;
}

export default async function ThesisPage() {
  const res = await getTheses();
  const theses = [...res.data].sort((a, b) => severity(b) - severity(a));

  const totals = ORDER.map((s) => ({
    status: s,
    n: theses.reduce((acc, t) => acc + countBy(t, s), 0),
  }));
  const withBroken = theses.filter((t) => countBy(t, "broken") > 0).length;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Thesis tracker"
        subtitle="Each thesis was written with the conditions that would falsify it. This page exists to make those conditions harder to quietly forget."
        right={<SourceTag source={res.source} error={res.error} />}
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <StatCard label="Theses tracked" value={theses.length} />
        <StatCard
          label="With broken conditions"
          value={withBroken}
          accent={withBroken > 0}
          hint="a written prediction has failed"
        />
        {totals
          .filter((t) => t.status !== "unknown")
          .map((t) => (
            <StatCard
              key={t.status}
              label={`${CONDITION_STYLE[t.status].label} conditions`}
              value={t.n}
            />
          ))}
      </div>

      <Callout tone="note">
        A condition marked broken does not automatically close a thesis, and a
        thesis with every condition holding is not thereby correct. The value is
        in having written the test down before the evidence arrived.
      </Callout>

      {theses.length === 0 ? (
        <Empty>No theses returned.</Empty>
      ) : (
        <div className="space-y-4">
          {theses.map((t) => {
            const broken = countBy(t, "broken");
            const atRisk = countBy(t, "at_risk");
            return (
              <Panel
                key={t.candidate_id}
                className={
                  broken > 0
                    ? "border-rose-500/25"
                    : atRisk > 0
                      ? "border-amber-500/20"
                      : ""
                }
                title={
                  <span className="flex flex-wrap items-center gap-2">
                    <Link
                      href={`/opportunities/${t.candidate_id}`}
                      className="text-[13px] font-semibold normal-case tracking-normal text-neutral-100 underline-offset-2 hover:text-amber-300 hover:underline"
                    >
                      {t.candidate_name}
                    </Link>
                    <span className="rounded bg-neutral-800 px-1.5 py-0.5 text-[10px] font-normal normal-case tracking-normal text-neutral-400">
                      {titleCase(t.status)}
                    </span>
                    {broken > 0 ? (
                      <span className="rounded bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-normal normal-case tracking-normal text-rose-300 ring-1 ring-inset ring-rose-500/30">
                        {broken} broken
                      </span>
                    ) : null}
                    {atRisk > 0 ? (
                      <span className="rounded bg-amber-500/12 px-1.5 py-0.5 text-[10px] font-normal normal-case tracking-normal text-amber-300 ring-1 ring-inset ring-amber-500/30">
                        {atRisk} at risk
                      </span>
                    ) : null}
                  </span>
                }
                right={
                  <span className="text-[11px] text-neutral-500">
                    written {formatDate(t.created_at)}
                  </span>
                }
              >
                <p className="max-w-4xl text-[13.5px] leading-relaxed text-neutral-300">
                  {t.statement}
                </p>

                <div className="mt-3 grid gap-2 border-t border-neutral-800 pt-3 lg:grid-cols-2">
                  {[...t.conditions]
                    .sort(
                      (a, b) =>
                        ORDER.indexOf(a.status) - ORDER.indexOf(b.status),
                    )
                    .map((c) => {
                      const style = CONDITION_STYLE[c.status];
                      return (
                        <div
                          key={c.text}
                          className="relative overflow-hidden rounded border border-neutral-800 bg-neutral-950/40 pl-2.5"
                        >
                          <div
                            className={`absolute left-0 top-0 h-full w-[3px] ${style.rail}`}
                          />
                          <div className="p-2.5">
                            <div className="flex items-start gap-2">
                              <span
                                className={`mt-px inline-flex shrink-0 items-center rounded px-1.5 py-0.5 text-[9.5px] uppercase tracking-wider ring-1 ring-inset ${style.chip}`}
                              >
                                {style.label}
                              </span>
                              <span className="min-w-0 flex-1 text-[12.5px] leading-relaxed text-neutral-200">
                                {c.text}
                              </span>
                            </div>
                            {c.note ? (
                              <p className="mt-1 text-[11.5px] leading-relaxed text-neutral-500">
                                {c.note}
                              </p>
                            ) : null}
                          </div>
                        </div>
                      );
                    })}
                </div>
              </Panel>
            );
          })}
        </div>
      )}
    </div>
  );
}
