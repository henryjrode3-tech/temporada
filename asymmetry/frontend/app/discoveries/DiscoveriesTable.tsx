"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Money } from "@/components/Money";
import { Multiple } from "@/components/Multiple";
import { Pct } from "@/components/Pct";
import { VerdictChip } from "@/components/VerdictChip";
import { RankDelta, ScrollTable, Td, Th } from "@/components/ui";
import { formatDate } from "@/lib/format";
import type { Candidate } from "@/lib/types";

type SortKey =
  | "discovery_date"
  | "name"
  | "sector"
  | "current_market_cap"
  | "revenue_growth"
  | "overall_score"
  | "asymmetry_score"
  | "confidence_score"
  | "risk_score"
  | "median_multiple";

const COLUMNS: { key: SortKey; label: string; align: "left" | "right" }[] = [
  { key: "discovery_date", label: "Discovered", align: "left" },
  { key: "name", label: "Candidate", align: "left" },
  { key: "sector", label: "Sector", align: "left" },
  { key: "current_market_cap", label: "Valuation", align: "right" },
  { key: "revenue_growth", label: "Growth", align: "right" },
  { key: "asymmetry_score", label: "Asymmetry", align: "right" },
  { key: "overall_score", label: "Overall", align: "right" },
  { key: "confidence_score", label: "Confidence", align: "right" },
  { key: "risk_score", label: "Risk", align: "right" },
  { key: "median_multiple", label: "Median ×", align: "right" },
];

function valueOf(c: Candidate, key: SortKey): string | number {
  switch (key) {
    case "median_multiple":
      return c.scenario_summary?.median_multiple ?? -1;
    case "revenue_growth":
      return c.revenue_growth ?? -99;
    case "current_market_cap":
      return c.current_market_cap ?? -1;
    case "name":
    case "sector":
    case "discovery_date":
      return c[key];
    default:
      return c[key];
  }
}

export function DiscoveriesTable({ candidates }: { candidates: Candidate[] }) {
  const [sort, setSort] = useState<SortKey>("discovery_date");
  const [asc, setAsc] = useState(false);
  const [sector, setSector] = useState<string>("all");

  const sectors = useMemo(
    () => Array.from(new Set(candidates.map((c) => c.sector))).sort(),
    [candidates],
  );

  const rows = useMemo(() => {
    const filtered =
      sector === "all"
        ? candidates
        : candidates.filter((c) => c.sector === sector);
    return [...filtered].sort((a, b) => {
      const va = valueOf(a, sort);
      const vb = valueOf(b, sort);
      const cmp =
        typeof va === "string" && typeof vb === "string"
          ? va.localeCompare(vb)
          : Number(va) - Number(vb);
      return asc ? cmp : -cmp;
    });
  }, [candidates, sector, sort, asc]);

  function toggle(key: SortKey) {
    if (key === sort) setAsc((v) => !v);
    else {
      setSort(key);
      setAsc(key === "name" || key === "sector");
    }
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <label className="text-[11px] uppercase tracking-wider text-neutral-500">
          Sector
        </label>
        <select
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          className="rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-[12px] text-neutral-200 outline-none focus:border-amber-500/50"
        >
          <option value="all">All sectors ({candidates.length})</option>
          {sectors.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <span className="text-[11px] text-neutral-600">
          {rows.length} shown · click a column header to sort
        </span>
      </div>

      <ScrollTable>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <Th key={col.key} align={col.align}>
                  <button
                    type="button"
                    onClick={() => toggle(col.key)}
                    className={`inline-flex items-center gap-1 uppercase tracking-wider transition-colors hover:text-neutral-200 ${
                      sort === col.key ? "text-amber-300" : ""
                    }`}
                  >
                    {col.label}
                    {sort === col.key ? (
                      <svg width="7" height="7" viewBox="0 0 8 8" aria-hidden="true">
                        <path
                          d={asc ? "M4 0 L8 8 L0 8 Z" : "M4 8 L0 0 L8 0 Z"}
                          fill="currentColor"
                        />
                      </svg>
                    ) : null}
                  </button>
                </Th>
              ))}
              <Th>Verdict</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} className="hover:bg-neutral-800/20">
                <Td className="text-neutral-500">{formatDate(c.discovery_date)}</Td>
                <Td>
                  <span className="flex items-center gap-2">
                    <Link
                      href={`/opportunities/${c.id}`}
                      className="font-medium text-neutral-100 underline-offset-2 hover:text-amber-300 hover:underline"
                    >
                      {c.name}
                    </Link>
                    {c.ticker ? (
                      <span className="font-mono text-[11px] text-neutral-600">
                        {c.ticker}
                      </span>
                    ) : null}
                    <RankDelta change={c.rank_change} />
                  </span>
                </Td>
                <Td className="text-neutral-400">{c.sector}</Td>
                <Td align="right">
                  <Money value={c.current_market_cap} />
                </Td>
                <Td align="right">
                  <Pct value={c.revenue_growth} tone="signed" signed />
                </Td>
                <Td align="right" className="font-semibold text-amber-300">
                  <span className="tabular-nums">{c.asymmetry_score}</span>
                </Td>
                <Td align="right">
                  <span className="tabular-nums">{c.overall_score.toFixed(1)}</span>
                </Td>
                <Td align="right" className="text-neutral-400">
                  <span className="tabular-nums">
                    {c.confidence_score.toFixed(0)}
                  </span>
                </Td>
                <Td align="right">
                  <span
                    className={`tabular-nums ${
                      c.risk_score >= 70
                        ? "text-rose-400"
                        : c.risk_score >= 45
                          ? "text-amber-400"
                          : "text-neutral-400"
                    }`}
                  >
                    {c.risk_score}
                  </span>
                </Td>
                <Td align="right">
                  <Multiple value={c.scenario_summary?.median_multiple} estimate />
                </Td>
                <Td>
                  <VerdictChip verdict={c.verdict} size="sm" />
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollTable>
    </div>
  );
}
