import PropTypes from "prop-types";
import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import CategoryIcon from "../components/CategoryIcon";
import { Money } from "../components/domain";
import { ErrorMessage, PageLoader } from "../components/ui";
import { categoryTheme } from "../constants/categories";
import { useAllServices, useCategories } from "../hooks/useCatalogue";

function ServiceCard({ service, theme }) {
  return (
    <li className="group relative overflow-hidden rounded-3xl border border-white/70 bg-white/85 p-4 shadow-[0_10px_34px_-24px_rgba(18,38,26,0.5)] backdrop-blur-xl transition hover:-translate-y-0.5 hover:shadow-[0_18px_40px_-22px_rgba(18,38,26,0.45)]">
      <span
        aria-hidden="true"
        className={`absolute -top-10 -right-8 h-24 w-24 rounded-full bg-gradient-to-br ${theme.gradient} opacity-20 blur-2xl transition group-hover:opacity-35`}
      />
      <div className="relative flex items-start gap-3">
        <span
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${theme.gradient} text-white shadow-lg ${theme.glow}`}
        >
          <CategoryIcon name={service.categoryIcon} className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-ink">{service.name}</p>
          <p className="mt-0.5 text-xs font-medium" style={{ color: theme.accent }}>
            {service.categoryName}
          </p>
          <p className="mt-2 text-sm text-slate-600">
            {service.priceMin && service.priceMax ? (
              <>
                From <Money value={service.priceMin} className="font-semibold text-ink" />
              </>
            ) : (
              "Quoted after a visit"
            )}
          </p>
        </div>
      </div>
      <div className="relative mt-3 flex gap-2">
        <Link
          to={`/providers?service=${service.id}`}
          className="flex-1 rounded-full bg-ink px-4 py-2.5 text-center text-sm font-semibold text-white transition hover:bg-brand-900"
        >
          Find providers
        </Link>
        <Link
          to={`/request-service?service=${service.id}`}
          className="rounded-full border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-white"
        >
          Request
        </Link>
      </div>
    </li>
  );
}

ServiceCard.propTypes = {
  service: PropTypes.object.isRequired,
  theme: PropTypes.object.isRequired,
};

function ServiceBrowser({ initialCategory }) {
  const { data: categories, error: catError } = useCategories();
  const { data: services, isLoading, error } = useAllServices();
  const [params, setParams] = useSearchParams();
  const [active, setActive] = useState(initialCategory ?? params.get("category") ?? "");

  const byCategory = useMemo(() => {
    const rows = services ?? [];
    return active ? rows.filter((s) => s.categorySlug === active) : rows;
  }, [services, active]);

  function pick(slug) {
    setActive(slug);
    const next = new URLSearchParams(params);
    if (slug) next.set("category", slug);
    else next.delete("category");
    setParams(next, { replace: true });
  }

  const activeCategory = (categories ?? []).find((c) => c.slug === active);

  return (
    <>
      <div className="mb-6 min-h-[4.5rem]">
        <h1 className="page-title">
          {activeCategory ? activeCategory.name : "Every service"}
        </h1>
        <p className="mt-1.5 text-slate-600">
          {activeCategory
            ? activeCategory.description
            : "Every service we cover, one tap from a provider."}
        </p>
      </div>

      <div className="sticky top-16 z-10 -mx-4 mb-6 bg-canvas/85 px-4 py-3 backdrop-blur-xl lg:top-0">
        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <div className="flex min-h-[2.75rem] gap-2">
            <button
              type="button"
              onClick={() => pick("")}
              className={`chip ${active === "" ? "chip-active" : "chip-idle"}`}
            >
              All {(services ?? []).length}
            </button>
            {(categories ?? []).map((c) => {
              const theme = categoryTheme(c.slug);
              const on = active === c.slug;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => pick(c.slug)}
                  className={`chip ${on ? "text-white" : "chip-idle"}`}
                  style={on ? { backgroundColor: theme.accent } : undefined}
                >
                  <CategoryIcon name={c.icon} className="h-4 w-4" />
                  {c.name}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {isLoading && <PageLoader />}
      <ErrorMessage error={error || catError} />

      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {byCategory.map((s) => (
          <ServiceCard key={s.id} service={s} theme={categoryTheme(s.categorySlug)} />
        ))}
      </ul>
    </>
  );
}

ServiceBrowser.propTypes = { initialCategory: PropTypes.string };

export function Services() {
  return <ServiceBrowser />;
}

export function CategoryServices() {
  const { categorySlug } = useParams();
  return <ServiceBrowser key={categorySlug} initialCategory={categorySlug} />;
}
