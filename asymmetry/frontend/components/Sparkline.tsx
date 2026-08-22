/**
 * Hand-drawn SVG sparkline. No chart library, no external requests.
 */
export function Sparkline({
  values,
  width = 120,
  height = 32,
  stroke = "#fbbf24",
  fill = true,
  label,
}: {
  values: number[];
  width?: number;
  height?: number;
  stroke?: string;
  fill?: boolean;
  label?: string;
}) {
  if (values.length < 2) {
    return <div className="h-8 text-[11px] text-neutral-600">no history</div>;
  }
  const pad = 2;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const stepX = (width - pad * 2) / (values.length - 1);
  const points = values.map((v, i) => {
    const x = pad + i * stepX;
    const y = pad + (height - pad * 2) * (1 - (v - min) / span);
    return [x, y] as const;
  });
  const path = points
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");
  const area = `${path} L${points[points.length - 1][0].toFixed(2)},${height - pad} L${pad},${height - pad} Z`;
  const last = points[points.length - 1];
  const rising = values[values.length - 1] >= values[0];
  const gradId = `spark-${Math.round(values[0] * 1000)}-${values.length}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={label ?? "score history sparkline"}
      className="overflow-visible"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.28" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill ? <path d={area} fill={`url(#${gradId})`} /> : null}
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle
        cx={last[0]}
        cy={last[1]}
        r="2.2"
        fill={rising ? stroke : "#fb7185"}
      />
    </svg>
  );
}
