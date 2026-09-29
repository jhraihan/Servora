import { Link } from "react-router-dom";

import ServiceSearch from "../components/ServiceSearch";
import { ErrorMessage, PageLoader } from "../components/ui";
import { useCategories } from "../hooks/useCatalogue";
import HomeHero from "./HomeHero";

const ICONS = {
  zap: "⚡", droplet: "💧", wind: "❄️", monitor: "💻",
  paintbrush: "🎨", sparkles: "✨", wrench: "🔧", car: "🚗",
};

const PROMISES = [
  {
    title: "Trust you can read",
    body: "Every provider shows verification, completion rate, cancellations and reply time — not just a star rating.",
  },
  {
    title: "Price agreed up front",
    body: "The price is locked when a provider accepts. See how it compares to the typical range before you book.",
  },
  {
    title: "Honest reviews",
    body: "Only customers with a completed job can review, and reviews stay sealed until both sides have rated.",
  },
];

export default function Home() {
  const { data: categories, isLoading, error } = useCategories();

  return (
    <div className="space-y-12">
      <HomeHero>
        <div className="mt-8 max-w-xl">
          <ServiceSearch tone="dark" placeholder="Try “AC not cooling”" />
        </div>
      </HomeHero>

      <section aria-labelledby="categories-heading">
        <div className="mb-5 flex items-end justify-between gap-4">
          <h2 id="categories-heading" className="section-title">Browse by category</h2>
          <Link to="/services" className="text-sm font-semibold text-brand-700">All 45 services</Link>
        </div>
        {isLoading && <PageLoader />}
        <ErrorMessage error={error} />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(categories ?? []).map((c) => (
            <Link
              key={c.id}
              to={`/services/${c.slug}`}
              className="card group p-4 transition hover:-translate-y-0.5 hover:shadow-lg"
            >
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-50 text-2xl" aria-hidden="true">
                {ICONS[c.icon] ?? "🛠️"}
              </span>
              <p className="mt-3 font-semibold text-ink group-hover:text-brand-700">{c.name}</p>
              <p className="text-xs text-slate-600">{c.serviceCount} services</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {PROMISES.map((p) => (
          <div key={p.title} className="card p-5">
            <h3 className="font-semibold text-ink">{p.title}</h3>
            <p className="mt-1.5 text-sm text-slate-600">{p.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
