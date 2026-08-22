/**
 * Semicircular gauge drawn as an SVG arc. Shows upside magnitude only —
 * it says nothing about how likely that upside is, which is deliberately
 * carried by a separate confidence figure.
 */
export function AsymmetryGauge({
  value,
  size = 132,
  label = "Asymmetry",
  sublabel,
}: {
  value: number;
  size?: number;
  label?: string;
  sublabel?: string;
}) {
  const v = Math.max(0, Math.min(100, value));
  const w = size;
  const h = size * 0.62;
  const cx = w / 2;
  const cy = h - 6;
  const r = w / 2 - 10;
  const stroke = 9;

  const pointOnArc = (t: number) => {
    const angle = Math.PI * (1 - t);
    return [cx + r * Math.cos(angle), cy - r * Math.sin(angle)] as const;
  };
  const [sx, sy] = pointOnArc(0);
  const [ex, ey] = pointOnArc(1);
  const [vx, vy] = pointOnArc(v / 100);
  const largeArc = v > 50 ? 1 : 0;

  const color = v >= 75 ? "#34d399" : v >= 50 ? "#fbbf24" : v >= 30 ? "#38bdf8" : "#a3a3a3";

  return (
    <div className="flex flex-col items-center">
      <svg width={w} height={h + 6} viewBox={`0 0 ${w} ${h + 6}`} role="img" aria-label={`${label} ${v} of 100`}>
        <path
          d={`M ${sx} ${sy} A ${r} ${r} 0 1 1 ${ex} ${ey}`}
          fill="none"
          stroke="#262626"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <path
          d={`M ${sx} ${sy} A ${r} ${r} 0 ${largeArc} 1 ${vx} ${vy}`}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        {[25, 50, 75].map((t) => {
          const [tx, ty] = pointOnArc(t / 100);
          const [ix, iy] = [
            cx + (r - stroke / 2 - 3) * Math.cos(Math.PI * (1 - t / 100)),
            cy - (r - stroke / 2 - 3) * Math.sin(Math.PI * (1 - t / 100)),
          ];
          return (
            <line
              key={t}
              x1={tx}
              y1={ty}
              x2={ix}
              y2={iy}
              stroke="#0a0a0a"
              strokeWidth="1.5"
            />
          );
        })}
        <text
          x={cx}
          y={cy - 6}
          textAnchor="middle"
          className="fill-neutral-100 tabular-nums"
          style={{ fontSize: size * 0.22, fontWeight: 600 }}
        >
          {Math.round(v)}
        </text>
      </svg>
      <div className="-mt-1 text-[10px] uppercase tracking-wider text-neutral-500">
        {label}
      </div>
      {sublabel ? (
        <div className="mt-0.5 max-w-[16rem] text-center text-[11px] leading-snug text-neutral-500">
          {sublabel}
        </div>
      ) : null}
    </div>
  );
}
