import { Link, useParams } from "react-router-dom";

import { EmptyState, ErrorMessage, PageHeader, PageLoader } from "../components/ui";
import { Money } from "../components/domain";
import { PRICING_MODEL_LABEL } from "../constants/domain";
import { useCategories, useCategory } from "../hooks/useCatalogue";

export function Services() {
  const { data, isLoading, error } = useCategories();

  return (
    <>
      <PageHeader title="All services" subtitle="Choose a category to see what our providers offer." />
      {isLoading && <PageLoader />}
      <ErrorMessage error={error} />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {(data ?? []).map((c) => (
          <Link key={c.id} to={`/services/${c.slug}`} className="card p-5 transition hover:border-brand-300 hover:shadow-md">
            <p className="font-semibold text-ink">{c.name}</p>
            <p className="mt-1 text-sm text-slate-600">{c.description}</p>
            <p className="mt-3 text-xs font-medium text-brand-700">{c.serviceCount} services →</p>
          </Link>
        ))}
      </div>
    </>
  );
}

export function CategoryServices() {
  const { categorySlug } = useParams();
  const { data: category, isLoading, error } = useCategory(categorySlug);

  if (isLoading) return <PageLoader />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <>
      <Link to="/services" className="text-sm font-semibold text-brand-700">← All services</Link>
      <div className="mt-3">
        <PageHeader title={category.name} subtitle={category.description} />
      </div>
      {category.services.length === 0 ? (
        <EmptyState title="No services here yet" body="Check back soon — we are adding providers every week." />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {category.services.map((s) => (
            <li key={s.id} className="card flex flex-col p-5">
              <p className="font-semibold text-ink">{s.name}</p>
              <p className="mt-1 text-xs text-slate-500">{PRICING_MODEL_LABEL[s.pricingModel]}</p>
              <p className="mt-3 text-sm text-slate-600">
                {s.priceMin && s.priceMax ? (
                  <>Typical price <Money value={s.priceMin} /> – <Money value={s.priceMax} /></>
                ) : (
                  "Priced after the provider sees the job"
                )}
              </p>
              <div className="mt-4 flex gap-2">
                <Link to={`/providers?service=${s.id}`} className="rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800">
                  Find providers
                </Link>
                <Link to={`/request-service?service=${s.id}`} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                  Request a job
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
