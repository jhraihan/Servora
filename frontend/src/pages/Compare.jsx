import { useQueries } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { providers } from "../api/endpoints";
import { Money } from "../components/domain";
import { TrustBadge } from "../components/Trust";
import { Button, EmptyState, PageHeader, PageLoader } from "../components/ui";
import { formatDuration, formatPercent } from "../lib/format";
import { useCompareStore } from "../store/compare";

function yes(value) {
  return value ? "✓" : "—";
}

export default function Compare() {
  const ids = useCompareStore((s) => s.ids);
  const toggle = useCompareStore((s) => s.toggle);
  const clear = useCompareStore((s) => s.clear);

  const details = useQueries({
    queries: ids.map((id) => ({ queryKey: ["provider", String(id)], queryFn: () => providers.detail(id) })),
  });
  const trusts = useQueries({
    queries: ids.map((id) => ({ queryKey: ["provider-trust", String(id)], queryFn: () => providers.trust(id) })),
  });

  if (ids.length === 0) {
    return (
      <EmptyState
        title="Nothing to compare yet"
        body="Tap “Compare” on up to three providers to see them side by side."
        action={<Button to="/providers">Browse providers</Button>}
      />
    );
  }

  if (details.some((q) => q.isLoading) || trusts.some((q) => q.isLoading)) return <PageLoader />;

  const columns = ids.map((id, i) => ({ id, p: details[i].data, t: trusts[i].data })).filter((c) => c.p && c.t);

  const rows = [
    ["Trust", (c) => <TrustBadge score={c.t.score} tier={c.t.tier} />],
    ["Identity verified", (c) => yes(c.t.verification.identity)],
    ["Trade certificate", (c) => yes(c.t.verification.skill)],
    ["Jobs completed", (c) => c.t.evidence.jobsCompleted],
    ["Completion rate", (c) => formatPercent(c.t.evidence.completionRate)],
    ["Cancellation rate", (c) => formatPercent(c.t.evidence.cancellationRate)],
    ["Typical response", (c) => formatDuration(c.t.evidence.medianResponseSeconds)],
    ["Lowest price", (c) => {
      const prices = c.p.offerings.filter((o) => o.isActive).map((o) => Number(o.price));
      return prices.length ? <Money value={Math.min(...prices)} /> : "—";
    }],
    ["Experience", (c) => (c.p.experienceYears ? `${c.p.experienceYears} yrs` : "—")],
  ];

  return (
    <>
      <PageHeader
        title="Compare providers"
        subtitle="The same facts, side by side."
        action={<Button variant="secondary" size="sm" onClick={clear}>Clear all</Button>}
      />
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          <thead>
            <tr className="border-b border-slate-200">
              <th scope="col" className="p-4 text-left text-xs font-medium uppercase text-slate-500">Provider</th>
              {columns.map((c) => (
                <th key={c.id} scope="col" className="p-4 text-left align-top">
                  <Link to={`/providers/${c.id}`} className="font-semibold text-ink hover:text-brand-700">{c.p.displayName}</Link>
                  <button type="button" onClick={() => toggle(c.id)} className="mt-1 block text-xs font-medium text-slate-500 hover:text-rose-700">
                    Remove
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, render]) => (
              <tr key={label} className="border-b border-slate-100 last:border-0">
                <th scope="row" className="p-4 text-left font-medium text-slate-600">{label}</th>
                {columns.map((c) => (
                  <td key={c.id} className="p-4 tabular-nums text-ink">{render(c)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
