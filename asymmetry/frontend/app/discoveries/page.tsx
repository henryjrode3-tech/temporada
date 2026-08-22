import { getCandidates } from "@/lib/api";
import { DiscoveriesTable } from "./DiscoveriesTable";
import { EstimateLegend } from "@/components/Estimate";
import { Empty, PageHeader, Panel, SourceTag } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function DiscoveriesPage() {
  const res = await getCandidates({ limit: 200 });
  const items = [...res.data.items].sort((a, b) =>
    a.discovery_date < b.discovery_date ? 1 : -1,
  );

  return (
    <div className="space-y-5">
      <PageHeader
        title="Discoveries"
        subtitle="Everything the funnel has surfaced, newest first. Most of these will not survive contact with evidence, which is the point of keeping them all on one page."
        right={<SourceTag source={res.source} error={res.error} />}
      />

      <Panel
        title={`All candidates (${res.data.total})`}
        right={<EstimateLegend />}
      >
        {items.length === 0 ? (
          <Empty>No candidates returned.</Empty>
        ) : (
          <DiscoveriesTable candidates={items} />
        )}
      </Panel>
    </div>
  );
}
