import { Panel } from "@/components/ui";
import { Sparkline } from "@/components/Sparkline";
import type { ScorePoint } from "@/lib/types";

/**
 * Two-series SVG line chart, hand-drawn. Overall score and asymmetry score are
 * plotted on the same 0-100 axis but are deliberately never combined.
 */
export function ScoreHistory({
  history,
  title = "Score history",
}: {
  history: ScorePoint[];
  title?: string;
}) {
  if (history.length < 2) {
    return (
      <Panel title={title}>
        <p className="text-[12px] text-neutral-600">
          Not enough snapshots to draw a history.
        </p>
      </Panel>
    );
  }

  const w = 640;
  const h = 190;
  const padL = 30;
  const padR = 12;
  const padT = 12;
  const padB = 26;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;
  const stepX = plotW / (history.length - 1);
  const y = (v: number) => padT + plotH * (1 - Math.max(0, Math.min(100, v)) / 100);

  const line = (key: "overall_score" | "asymmetry_score") =>
    history
      .map(
        (p, i) =>
          `${i === 0 ? "M" : "L"}${(padL + i * stepX).toFixed(2)},${y(p[key]).toFixed(2)}`,
      )
      .join(" ");

  const first = history[0];
  const last = history[history.length - 1];
  const deltaOverall = last.overall_score - first.overall_score;
  const deltaAsym = last.asymmetry_score - first.asymmetry_score;

  return (
    <Panel
      title={title}
      right={
        <div className="flex items-center gap-4 text-[11px]">
          <Legend color="#fbbf24" label="Overall" delta={deltaOverall} />
          <Legend color="#38bdf8" label="Asymmetry" delta={deltaAsym} />
        </div>
      }
    >
      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${w} ${h}`}
          width="100%"
          preserveAspectRatio="xMinYMin meet"
          role="img"
          aria-label="Overall and asymmetry score history"
          style={{ minWidth: 380 }}
        >
          {[0, 25, 50, 75, 100].map((t) => (
            <g key={t}>
              <line
                x1={padL}
                y1={y(t)}
                x2={w - padR}
                y2={y(t)}
                stroke="#262626"
                strokeWidth="1"
              />
              <text
                x={padL - 6}
                y={y(t)}
                textAnchor="end"
                dominantBaseline="middle"
                className="fill-neutral-600 tabular-nums"
                style={{ fontSize: 9 }}
              >
                {t}
              </text>
            </g>
          ))}

          <path d={line("asymmetry_score")} fill="none" stroke="#38bdf8" strokeWidth="1.75" strokeLinejoin="round" />
          <path d={line("overall_score")} fill="none" stroke="#fbbf24" strokeWidth="1.75" strokeLinejoin="round" />

          {history.map((p, i) => (
            <g key={p.at}>
              <circle cx={padL + i * stepX} cy={y(p.asymmetry_score)} r="2" fill="#38bdf8" />
              <circle cx={padL + i * stepX} cy={y(p.overall_score)} r="2" fill="#fbbf24" />
              {i % 3 === 0 || i === history.length - 1 ? (
                <text
                  x={padL + i * stepX}
                  y={h - 8}
                  textAnchor="middle"
                  className="fill-neutral-600"
                  style={{ fontSize: 9 }}
                >
                  {p.at.slice(0, 7)}
                </text>
              ) : null}
            </g>
          ))}
        </svg>
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-neutral-600">
        Snapshots are append-only. Nothing is updated in place, so what the
        engine believed at an earlier date remains a query rather than an
        archaeology project.
      </p>
    </Panel>
  );
}

function Legend({
  color,
  label,
  delta,
}: {
  color: string;
  label: string;
  delta: number;
}) {
  return (
    <span className="inline-flex items-center gap-1.5 text-neutral-500">
      <span className="h-0.5 w-4 rounded" style={{ backgroundColor: color }} />
      {label}
      <span
        className={`tabular-nums ${
          delta > 0 ? "text-emerald-400" : delta < 0 ? "text-rose-400" : "text-neutral-500"
        }`}
      >
        {delta > 0 ? "+" : ""}
        {delta.toFixed(0)}
      </span>
    </span>
  );
}

export function MiniScoreHistory({ history }: { history: ScorePoint[] }) {
  return (
    <Sparkline
      values={history.map((p) => p.overall_score)}
      width={96}
      height={26}
      label="overall score history"
    />
  );
}
