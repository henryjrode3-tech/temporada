import { Empty, Panel } from "@/components/ui";
import { titleCase } from "@/lib/format";
import type { DebatePosition, DebateTurn } from "@/lib/types";

const POSITION: Record<
  DebatePosition,
  { chip: string; border: string; align: string; label: string }
> = {
  bull: {
    chip: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
    border: "border-l-emerald-500/50",
    align: "lg:mr-16",
    label: "For",
  },
  bear: {
    chip: "bg-rose-500/10 text-rose-300 ring-rose-500/30",
    border: "border-l-rose-500/50",
    align: "lg:ml-16",
    label: "Against",
  },
  neutral: {
    chip: "bg-neutral-700/40 text-neutral-400 ring-neutral-600/40",
    border: "border-l-neutral-600",
    align: "lg:mx-8",
    label: "Qualifying",
  },
};

export function Debate({ turns }: { turns: DebateTurn[] }) {
  if (turns.length === 0) {
    return (
      <Panel title="Agent debate">
        <Empty>
          No debate was run. Candidates rejected at deterministic screening never
          reach the multi-agent stage.
        </Empty>
      </Panel>
    );
  }

  const counts = {
    bull: turns.filter((t) => t.position === "bull").length,
    bear: turns.filter((t) => t.position === "bear").length,
    neutral: turns.filter((t) => t.position === "neutral").length,
  };

  return (
    <Panel
      title="Agent debate"
      right={
        <span className="flex flex-wrap items-center gap-2 text-[11px] text-neutral-500">
          <span className="text-emerald-400">{counts.bull} for</span>
          <span className="text-neutral-700">·</span>
          <span className="text-rose-400">{counts.bear} against</span>
          <span className="text-neutral-700">·</span>
          <span>{counts.neutral} qualifying</span>
        </span>
      }
    >
      <ol className="space-y-3">
        {turns.map((t, i) => {
          const p = POSITION[t.position];
          return (
            <li
              key={`${t.agent}-${i}`}
              className={`rounded-md border border-l-2 border-neutral-800 bg-neutral-950/40 p-3 ${p.border} ${p.align}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-[11px] text-neutral-400">
                  {t.agent}
                </span>
                <span
                  className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wider ring-1 ring-inset ${p.chip}`}
                >
                  {p.label}
                </span>
                <span className="ml-auto text-[10px] tabular-nums text-neutral-700">
                  turn {i + 1}
                </span>
              </div>
              <p className="mt-2 text-[13px] leading-relaxed text-neutral-300">
                {t.argument}
              </p>
            </li>
          );
        })}
      </ol>
      <p className="mt-4 text-[11px] leading-relaxed text-neutral-600">
        Positions are assigned to agents before they read the evidence, so the
        debate records disagreement rather than manufacturing consensus. Agent
        names map to the specialist roles in the analysis stage:{" "}
        {Array.from(new Set(turns.map((t) => titleCase(t.agent)))).join(", ")}.
      </p>
    </Panel>
  );
}
