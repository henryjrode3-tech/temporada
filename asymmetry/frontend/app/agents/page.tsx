import Link from "next/link";
import { getAgentRuns } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { BarChart, type BarDatum } from "@/components/BarChart";
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
import { formatDateTime, formatNumber } from "@/lib/format";
import type { AgentRun } from "@/lib/types";

export const dynamic = "force-dynamic";

const MODEL_COLOR: Record<string, string> = {
  deterministic: "#737373",
  "claude-haiku": "#38bdf8",
  "claude-sonnet": "#34d399",
  "claude-opus": "#fbbf24",
};

function usd(n: number): string {
  if (n === 0) return "$0";
  if (n < 0.01) return `$${n.toFixed(4)}`;
  return `$${n.toFixed(2)}`;
}

export default async function AgentsPage() {
  const res = await getAgentRuns(120);
  const runs = res.data;

  const totalCost = runs.reduce((a, r) => a + r.cost_usd, 0);
  const totalIn = runs.reduce((a, r) => a + r.tokens_in, 0);
  const totalOut = runs.reduce((a, r) => a + r.tokens_out, 0);
  const cacheHits = runs.filter((r) => r.cache_hit).length;
  const errors = runs.filter((r) => r.status !== "ok").length;
  const medianLatency = (() => {
    const l = runs.map((r) => r.latency_ms).sort((a, b) => a - b);
    return l.length ? l[Math.floor(l.length / 2)] : 0;
  })();

  const byAgent = new Map<string, { cost: number; runs: number }>();
  for (const r of runs) {
    const cur = byAgent.get(r.agent_name) ?? { cost: 0, runs: 0 };
    cur.cost += r.cost_usd;
    cur.runs += 1;
    byAgent.set(r.agent_name, cur);
  }
  const costBars: BarDatum[] = [...byAgent.entries()]
    .sort((a, b) => b[1].cost - a[1].cost)
    .slice(0, 10)
    .map(([agent, v]) => ({
      label: agent.replace(/_agent$/, ""),
      note: `${v.runs} runs`,
      value: v.cost,
      display: usd(v.cost),
      color: "#fbbf24",
    }));

  const byModel = new Map<string, { cost: number; runs: number; tokens: number }>();
  for (const r of runs) {
    const cur = byModel.get(r.model) ?? { cost: 0, runs: 0, tokens: 0 };
    cur.cost += r.cost_usd;
    cur.runs += 1;
    cur.tokens += r.tokens_in + r.tokens_out;
    byModel.set(r.model, cur);
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Agent activity"
        subtitle="Every model call is content-hash cached, so re-running the pipeline is nearly free and agent outputs stay reproducible. Cost is tracked per call rather than estimated after the fact."
        right={<SourceTag source={res.source} error={res.error} />}
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        <StatCard label="Runs shown" value={runs.length} />
        <StatCard label="Total cost" value={usd(totalCost)} accent />
        <StatCard
          label="Tokens in"
          value={formatNumber(totalIn)}
          hint="cached calls consume none"
        />
        <StatCard label="Tokens out" value={formatNumber(totalOut)} />
        <StatCard
          label="Cache hit rate"
          value={
            runs.length ? `${((cacheHits / runs.length) * 100).toFixed(0)}%` : "—"
          }
          hint={`${cacheHits} of ${runs.length} calls`}
        />
        <StatCard
          label="Median latency"
          value={`${formatNumber(medianLatency)} ms`}
          hint={errors ? `${errors} failed run${errors > 1 ? "s" : ""}` : "no failures"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Cost by agent">
          {costBars.length === 0 ? (
            <Empty>No runs.</Empty>
          ) : (
            <BarChart data={costBars} ariaLabel="Cost by agent" labelWidth={112} />
          )}
        </Panel>

        <Panel title="Cost by model tier">
          <ScrollTable>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <Th>Model</Th>
                  <Th align="right">Runs</Th>
                  <Th align="right">Tokens</Th>
                  <Th align="right">Cost</Th>
                  <Th align="right">Cost / run</Th>
                </tr>
              </thead>
              <tbody>
                {[...byModel.entries()]
                  .sort((a, b) => b[1].cost - a[1].cost)
                  .map(([model, v]) => (
                    <tr key={model} className="hover:bg-neutral-800/20">
                      <Td>
                        <span className="inline-flex items-center gap-2">
                          <span
                            className="h-2 w-2 rounded-full"
                            style={{
                              backgroundColor: MODEL_COLOR[model] ?? "#737373",
                            }}
                          />
                          <span className="font-mono text-[11.5px] text-neutral-200">
                            {model}
                          </span>
                        </span>
                      </Td>
                      <Td align="right">
                        <span className="tabular-nums">{v.runs}</span>
                      </Td>
                      <Td align="right">
                        <span className="tabular-nums">
                          {formatNumber(v.tokens)}
                        </span>
                      </Td>
                      <Td align="right">
                        <span className="tabular-nums">{usd(v.cost)}</span>
                      </Td>
                      <Td align="right" className="text-neutral-400">
                        <span className="tabular-nums">
                          {usd(v.cost / Math.max(1, v.runs))}
                        </span>
                      </Td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </ScrollTable>
          <Callout tone="note">
            The funnel spends nothing on stage 1, cents on stage 2 triage, and
            reserves the expensive multi-agent stage for the small share of
            candidates that survive both.
          </Callout>
        </Panel>
      </div>

      <Panel title={`Run log (${runs.length})`}>
        {runs.length === 0 ? (
          <Empty>No agent runs returned.</Empty>
        ) : (
          <ScrollTable>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <Th>When</Th>
                  <Th>Agent</Th>
                  <Th>Stage</Th>
                  <Th>Candidate</Th>
                  <Th>Model</Th>
                  <Th align="right">Tokens in</Th>
                  <Th align="right">Tokens out</Th>
                  <Th align="right">Cost</Th>
                  <Th align="right">Latency</Th>
                  <Th align="center">Cache</Th>
                  <Th align="center">Status</Th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r: AgentRun) => (
                  <tr key={r.id} className="hover:bg-neutral-800/20">
                    <Td className="text-neutral-500">
                      {formatDateTime(r.created_at)}
                    </Td>
                    <Td className="font-mono text-[11.5px] text-neutral-200">
                      {r.agent_name}
                    </Td>
                    <Td className="text-neutral-500">{r.stage}</Td>
                    <Td>
                      <Link
                        href={`/opportunities/${r.candidate_id}`}
                        className="text-neutral-300 underline-offset-2 hover:text-amber-300 hover:underline"
                      >
                        {r.candidate_name}
                      </Link>
                    </Td>
                    <Td>
                      <span className="inline-flex items-center gap-1.5">
                        <span
                          className="h-1.5 w-1.5 rounded-full"
                          style={{
                            backgroundColor: MODEL_COLOR[r.model] ?? "#737373",
                          }}
                        />
                        <span className="font-mono text-[11px] text-neutral-400">
                          {r.model}
                        </span>
                      </span>
                    </Td>
                    <Td align="right">
                      <span className="tabular-nums">
                        {formatNumber(r.tokens_in)}
                      </span>
                    </Td>
                    <Td align="right">
                      <span className="tabular-nums">
                        {formatNumber(r.tokens_out)}
                      </span>
                    </Td>
                    <Td align="right">
                      <span className="tabular-nums">{usd(r.cost_usd)}</span>
                    </Td>
                    <Td align="right" className="text-neutral-400">
                      <span className="tabular-nums">
                        {formatNumber(r.latency_ms)} ms
                      </span>
                    </Td>
                    <Td align="center">
                      {r.cache_hit ? (
                        <span className="rounded bg-cyan-500/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-cyan-300 ring-1 ring-inset ring-cyan-500/30">
                          hit
                        </span>
                      ) : (
                        <span className="text-neutral-700">—</span>
                      )}
                    </Td>
                    <Td align="center">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wider ring-1 ring-inset ${
                          r.status === "ok"
                            ? "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30"
                            : "bg-rose-500/15 text-rose-300 ring-rose-500/30"
                        }`}
                      >
                        {r.status}
                      </span>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollTable>
        )}
      </Panel>
    </div>
  );
}
