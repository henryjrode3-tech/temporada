import type { Severity, SignalStrength, Verdict } from "./types";

export function formatMoney(
  value: number | null | undefined,
  opts: { signed?: boolean } = {},
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value < 0 ? "-" : opts.signed && value > 0 ? "+" : "";
  const n = Math.abs(value);
  const units: [number, string][] = [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (const [scale, suffix] of units) {
    if (n >= scale) {
      const scaled = n / scale;
      const dp = scaled >= 100 ? 0 : scaled >= 10 ? 1 : scaled >= 1 ? 1 : 2;
      return `${sign}$${scaled.toFixed(dp)}${suffix}`;
    }
  }
  return `${sign}$${n.toFixed(0)}`;
}

export function formatMultiple(
  value: number | null | undefined,
  dp?: number,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const places = dp ?? (Math.abs(value) >= 100 ? 0 : Math.abs(value) >= 10 ? 1 : 2);
  return `${value.toFixed(places)}x`;
}

export function formatPct(
  value: number | null | undefined,
  opts: { dp?: number; signed?: boolean } = {},
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const dp = opts.dp ?? (Math.abs(value) < 0.1 ? 1 : 0);
  const pct = value * 100;
  const sign = opts.signed && pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(dp)}%`;
}

export function formatNumber(value: number, dp = 0): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    timeZone: "UTC",
  });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return `${formatDate(value)} ${d.toISOString().slice(11, 16)}Z`;
}

/** Deterministic relative age, computed against a fixed reference so that
 *  server and client renders agree. */
export function relativeAge(value: string | null | undefined, now = NOW): string {
  if (!value) return "—";
  const d = new Date(value).getTime();
  if (Number.isNaN(d)) return value;
  const days = Math.floor((now - d) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "1d ago";
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

/** Reference "now" for the fixture dataset. */
export const NOW = Date.UTC(2026, 7, 22, 12, 0, 0);

export const VERDICT_LABEL: Record<Verdict, string> = {
  TOP_OPPORTUNITY: "Top opportunity",
  INVESTIGATE: "Investigate",
  WATCH: "Watch",
  INTERESTING: "Interesting",
  HIGH_RISK: "High risk",
  THESIS_WEAKENING: "Thesis weakening",
  THESIS_INVALIDATED: "Thesis invalidated",
  REJECTED: "Rejected",
};

/** Research posture ordering, strongest interest first. */
export const VERDICT_ORDER: Verdict[] = [
  "TOP_OPPORTUNITY",
  "INVESTIGATE",
  "WATCH",
  "INTERESTING",
  "HIGH_RISK",
  "THESIS_WEAKENING",
  "THESIS_INVALIDATED",
  "REJECTED",
];

export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"];

export const STRENGTH_ORDER: SignalStrength[] = [
  "extreme",
  "strong",
  "moderate",
  "weak",
];

export function titleCase(value: string): string {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}
