export interface BarDatum {
  label: string;
  value: number;
  /** Text drawn at the end of the bar. Falls back to the raw value. */
  display?: string;
  color?: string;
  /** Muted second line under the label. */
  note?: string;
  /** Draws a hatched overlay — used to mark clamped scenarios. */
  hatched?: boolean;
}

/**
 * Horizontal SVG bar chart. Hand-written, no chart library.
 * A reference line at `baseline` marks break-even where that is meaningful.
 */
export function BarChart({
  data,
  height = 26,
  gap = 10,
  labelWidth = 128,
  baseline,
  baselineLabel,
  max,
  ariaLabel = "bar chart",
}: {
  data: BarDatum[];
  height?: number;
  gap?: number;
  labelWidth?: number;
  baseline?: number;
  baselineLabel?: string;
  max?: number;
  ariaLabel?: string;
}) {
  if (data.length === 0) {
    return <div className="text-[11px] text-neutral-600">no data</div>;
  }
  const chartWidth = 420;
  const plotX = labelWidth;
  const plotW = chartWidth - labelWidth - 56;
  const top = baselineLabel ? 16 : 4;
  const totalH = top + data.length * (height + gap);
  const upper = max ?? Math.max(...data.map((d) => d.value), baseline ?? 0) * 1.05;
  const scale = (v: number) => (upper > 0 ? (Math.max(0, v) / upper) * plotW : 0);

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${chartWidth} ${totalH}`}
        width="100%"
        preserveAspectRatio="xMinYMin meet"
        role="img"
        aria-label={ariaLabel}
        style={{ minWidth: 320, maxWidth: 620 }}
      >
        <defs>
          <pattern
            id="clamp-hatch"
            width="6"
            height="6"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <line x1="0" y1="0" x2="0" y2="6" stroke="#0a0a0a" strokeWidth="2.5" />
          </pattern>
        </defs>

        {baseline !== undefined && upper > 0 ? (
          <g>
            <line
              x1={plotX + scale(baseline)}
              y1={top - 12}
              x2={plotX + scale(baseline)}
              y2={totalH - 2}
              stroke="#525252"
              strokeWidth="1"
              strokeDasharray="3 3"
            />
            {baselineLabel ? (
              <text
                x={plotX + scale(baseline) + 4}
                y={top - 5}
                className="fill-neutral-500"
                style={{ fontSize: 9 }}
              >
                {baselineLabel}
              </text>
            ) : null}
          </g>
        ) : null}

        {data.map((d, i) => {
          const y = top + i * (height + gap);
          const w = Math.max(scale(d.value), 1.5);
          const color = d.color ?? "#fbbf24";
          return (
            <g key={`${d.label}-${i}`}>
              <text
                x={plotX - 8}
                y={y + height / 2 - (d.note ? 3 : 0)}
                textAnchor="end"
                dominantBaseline="middle"
                className="fill-neutral-300"
                style={{ fontSize: 11 }}
              >
                {d.label}
              </text>
              {d.note ? (
                <text
                  x={plotX - 8}
                  y={y + height / 2 + 9}
                  textAnchor="end"
                  dominantBaseline="middle"
                  className="fill-neutral-600"
                  style={{ fontSize: 9 }}
                >
                  {d.note}
                </text>
              ) : null}
              <rect
                x={plotX}
                y={y + 3}
                width={plotW}
                height={height - 6}
                rx="2"
                fill="#171717"
              />
              <rect
                x={plotX}
                y={y + 3}
                width={w}
                height={height - 6}
                rx="2"
                fill={color}
                opacity={0.9}
              />
              {d.hatched ? (
                <rect
                  x={plotX}
                  y={y + 3}
                  width={w}
                  height={height - 6}
                  rx="2"
                  fill="url(#clamp-hatch)"
                  opacity={0.35}
                />
              ) : null}
              <text
                x={plotX + plotW + 8}
                y={y + height / 2}
                dominantBaseline="middle"
                className="fill-neutral-200 tabular-nums"
                style={{ fontSize: 11, fontWeight: 600 }}
              >
                {d.display ?? d.value.toFixed(2)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
