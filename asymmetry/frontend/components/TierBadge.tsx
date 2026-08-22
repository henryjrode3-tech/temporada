const TIERS: Record<number, { label: string; cls: string; hint: string }> = {
  1: {
    label: "T1",
    cls: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
    hint: "Tier 1 — primary filing, register or verified measurement",
  },
  2: {
    label: "T2",
    cls: "bg-cyan-500/10 text-cyan-300 ring-cyan-500/30",
    hint: "Tier 2 — company disclosure, transcript or technical publication",
  },
  3: {
    label: "T3",
    cls: "bg-amber-500/10 text-amber-300 ring-amber-500/30",
    hint: "Tier 3 — press, commentary or unattributed remark; low evidential weight",
  },
  4: {
    label: "T4",
    cls: "bg-neutral-700/40 text-neutral-400 ring-neutral-600/40",
    hint: "Tier 4 — unverified or promotional; carries no weight in the composite",
  },
};

export function TierBadge({ tier }: { tier: number }) {
  const t = TIERS[tier] ?? TIERS[4];
  return (
    <span
      title={t.hint}
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold tabular-nums ring-1 ring-inset ${t.cls}`}
    >
      {t.label}
    </span>
  );
}
