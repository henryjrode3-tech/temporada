import { TierBadge } from "@/components/TierBadge";
import { Pct } from "@/components/Pct";
import { Callout, Empty, Panel, ScrollTable, Td, Th } from "@/components/ui";
import { formatDate } from "@/lib/format";
import type { Claim } from "@/lib/types";

export function Sources({ claims }: { claims: Claim[] }) {
  if (claims.length === 0) {
    return (
      <Panel title="Sources">
        <Empty>No claims have been extracted for this candidate.</Empty>
      </Panel>
    );
  }

  const sorted = [...claims].sort((a, b) => {
    if (a.source_tier !== b.source_tier) return a.source_tier - b.source_tier;
    return (b.published_at ?? "").localeCompare(a.published_at ?? "");
  });
  const byTier = sorted.reduce<Record<number, number>>((acc, c) => {
    acc[c.source_tier] = (acc[c.source_tier] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      <Panel
        title={`Claims and sources (${claims.length})`}
        right={
          <span className="flex items-center gap-2 text-[11px] text-neutral-500">
            {Object.entries(byTier)
              .sort(([a], [b]) => Number(a) - Number(b))
              .map(([tier, n]) => (
                <span key={tier} className="inline-flex items-center gap-1">
                  <TierBadge tier={Number(tier)} />
                  <span className="tabular-nums">{n}</span>
                </span>
              ))}
          </span>
        }
      >
        <ScrollTable>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Tier</Th>
                <Th>Claim</Th>
                <Th>Source</Th>
                <Th align="right">Published</Th>
                <Th align="right">Confidence</Th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((c) => (
                <tr key={c.id} className="hover:bg-neutral-800/20">
                  <Td>
                    <TierBadge tier={c.source_tier} />
                  </Td>
                  <Td className="max-w-[46rem] whitespace-normal text-neutral-200">
                    {c.claim}
                  </Td>
                  <Td className="text-neutral-400">
                    {c.source_url ? (
                      <a
                        href={c.source_url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="underline-offset-2 hover:text-amber-300 hover:underline"
                      >
                        {c.source_name}
                      </a>
                    ) : (
                      c.source_name
                    )}
                  </Td>
                  <Td align="right" className="text-neutral-400">
                    {formatDate(c.published_at)}
                  </Td>
                  <Td align="right">
                    <Pct value={c.confidence} dp={0} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollTable>
      </Panel>

      <Callout tone="note">
        Every claim carries a publication date, and all reads pass through an
        as-of filter, so a historical run physically cannot see a source
        published after the date being simulated. Tier 3 and 4 material is
        recorded for context but carries little or no weight in the composite.
      </Callout>
    </div>
  );
}
