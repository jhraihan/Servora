import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { providers } from "../api/endpoints";
import LocationSelect from "../components/LocationSelect";
import { ProviderCard } from "../components/domain";
import { Button, EmptyState, ErrorMessage, PageHeader, PageLoader } from "../components/ui";
import { TRUST_TIER, TRUST_TIER_LABEL } from "../constants/domain";
import { useAllServices } from "../hooks/useCatalogue";

const PAGE_SIZE = 10;

const FILTER_KEYS = ["service", "location", "tier", "min_trust", "verified_only", "available_on", "ordering"];

export default function ProviderSearch() {
  const [params, setParams] = useSearchParams();
  const { data: services } = useAllServices();
  const [filtersOpen, setFiltersOpen] = useState(false);

  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? ""]));
  const page = Number(params.get("page") ?? 1);

  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["provider-search", filters, page],
    queryFn: () => providers.search({ ...filters, page, page_size: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });

  function update(key, value) {
    const next = new URLSearchParams(params);
    if (value === "" || value === null || value === false) next.delete(key);
    else next.set(key, String(value));
    next.delete("page");
    setParams(next);
  }

  function goToPage(n) {
    const next = new URLSearchParams(params);
    next.set("page", String(n));
    setParams(next);
    window.scrollTo({ top: 0 });
  }

  const selectedService = (services ?? []).find((s) => String(s.id) === filters.service);
  const activeCount = FILTER_KEYS.filter((k) => k !== "ordering" && filters[k]).length;

  return (
    <>
      <PageHeader
        title={selectedService ? `${selectedService.name} providers` : "Browse providers"}
        subtitle="Ranked by trust — measured from real jobs, not self-reported."
      />

      <button
        type="button"
        onClick={() => setFiltersOpen((v) => !v)}
        aria-expanded={filtersOpen}
        aria-controls="search-filters"
        className="mb-4 flex w-full items-center justify-between rounded-xl bg-white px-4 py-3 text-sm font-semibold text-slate-800 ring-1 ring-slate-200 lg:hidden"
      >
        <span>Filters{activeCount > 0 && ` (${activeCount} active)`}</span>
        <span aria-hidden="true">{filtersOpen ? "▲" : "▼"}</span>
      </button>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside id="search-filters" className={`card h-fit space-y-4 p-4 lg:block ${filtersOpen ? "" : "hidden"}`} aria-label="Filters">
          <div>
            <label htmlFor="f-service" className="label">Service</label>
            <select id="f-service" className="input" value={filters.service} onChange={(e) => update("service", e.target.value)}>
              <option value="">Any service</option>
              {(services ?? []).map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="f-location" className="label">Area</label>
            <LocationSelect
              id="f-location"
              value={filters.location ? Number(filters.location) : null}
              onChange={(v) => update("location", v)}
            />
          </div>
          <div>
            <label htmlFor="f-date" className="label">Available on</label>
            <input id="f-date" type="date" className="input" value={filters.available_on} onChange={(e) => update("available_on", e.target.value)} />
          </div>
          <div>
            <label htmlFor="f-tier" className="label">Trust tier</label>
            <select id="f-tier" className="input" value={filters.tier} onChange={(e) => update("tier", e.target.value)}>
              <option value="">Any tier</option>
              {[TRUST_TIER.TRUSTED_PRO, TRUST_TIER.ESTABLISHED, TRUST_TIER.RISING, TRUST_TIER.NEW].map((t) => (
                <option key={t} value={t}>{TRUST_TIER_LABEL[t]}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="f-sort" className="label">Sort by</label>
            <select id="f-sort" className="input" value={filters.ordering} onChange={(e) => update("ordering", e.target.value)}>
              <option value="">Highest trust</option>
              <option value="price">Lowest price</option>
              <option value="distance">Nearest</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-700"
              checked={filters.verified_only === "true"}
              onChange={(e) => update("verified_only", e.target.checked ? "true" : "")}
            />
            Identity-verified only
          </label>
        </aside>

        <section aria-live="polite">
          <ErrorMessage error={error} />
          {isLoading ? (
            <PageLoader />
          ) : data?.results.length === 0 ? (
            <EmptyState
              title="No providers match yet"
              body="Try another area or remove a filter. You can also post a request and let providers come to you."
              action={<Button to={`/request-service${filters.service ? `?service=${filters.service}` : ""}`}>Post a request</Button>}
            />
          ) : (
            <>
              <p className="mb-3 text-sm text-slate-500">
                {data.count} provider{data.count === 1 ? "" : "s"} {isFetching && "· updating…"}
              </p>
              <div className="space-y-3">
                {data.results.map((p) => (
                  <ProviderCard key={p.id} provider={p} serviceId={filters.service || undefined} />
                ))}
              </div>
              {(data.next || data.previous) && (
                <div className="mt-6 flex justify-between">
                  <Button variant="secondary" disabled={!data.previous} onClick={() => goToPage(page - 1)}>Previous</Button>
                  <Button variant="secondary" disabled={!data.next} onClick={() => goToPage(page + 1)}>Next</Button>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </>
  );
}
