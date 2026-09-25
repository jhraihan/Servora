import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import LocationSelect from "../components/LocationSelect";
import { Button, ErrorMessage, PageLoader } from "../components/ui";
import { useAllServices, useCategories } from "../hooks/useCatalogue";

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
  const navigate = useNavigate();
  const { data: categories, isLoading, error } = useCategories();
  const { data: services } = useAllServices();
  const [serviceId, setServiceId] = useState("");
  const [locationId, setLocationId] = useState(null);

  function search(event) {
    event.preventDefault();
    const params = new URLSearchParams();
    if (serviceId) params.set("service", serviceId);
    if (locationId) params.set("location", locationId);
    navigate(`/providers?${params.toString()}`);
  }

  return (
    <div className="space-y-12">
      <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-brand-800 to-brand-600 px-5 py-10 text-white sm:px-10 sm:py-14">
        <p className="text-sm font-semibold uppercase tracking-wider text-brand-100">Dhaka&apos;s verified tradespeople</p>
        <h1 className="mt-2 max-w-2xl text-3xl font-bold leading-tight sm:text-5xl">
          Find a technician you can actually trust.
        </h1>
        <p className="mt-3 max-w-xl text-brand-100">
          Electricians, plumbers, AC technicians and more — ranked by what they have really done, not by who shouts loudest.
        </p>

        <form onSubmit={search} className="mt-8 grid gap-3 rounded-2xl bg-white p-3 text-slate-800 shadow-lg sm:grid-cols-[1fr_1fr_auto]">
          <div>
            <label htmlFor="home-service" className="sr-only">Service</label>
            <select id="home-service" className="input" value={serviceId} onChange={(e) => setServiceId(e.target.value)}>
              <option value="">What do you need?</option>
              {(services ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} — {s.categoryName}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="home-location" className="sr-only">Area</label>
            <LocationSelect id="home-location" value={locationId} onChange={setLocationId} placeholder="Where?" />
          </div>
          <Button type="submit" size="lg">Find providers</Button>
        </form>
      </section>

      <section aria-labelledby="categories-heading">
        <div className="mb-4 flex items-end justify-between">
          <h2 id="categories-heading" className="section-title">Browse by category</h2>
          <Link to="/services" className="text-sm font-semibold text-brand-700">All services</Link>
        </div>
        {isLoading && <PageLoader />}
        <ErrorMessage error={error} />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(categories ?? []).map((c) => (
            <Link key={c.id} to={`/services/${c.slug}`} className="card group p-4 transition hover:border-brand-300 hover:shadow-md">
              <span className="text-2xl" aria-hidden="true">{ICONS[c.icon] ?? "🛠️"}</span>
              <p className="mt-2 font-semibold text-ink group-hover:text-brand-700">{c.name}</p>
              <p className="text-xs text-slate-500">{c.serviceCount} services</p>
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
