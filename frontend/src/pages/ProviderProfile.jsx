import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { providers } from "../api/endpoints";
import { Money, Stars } from "../components/domain";
import { TrustBreakdown } from "../components/Trust";
import { Badge, Button, ErrorMessage, PageLoader } from "../components/ui";
import { PRICE_FLAG_LABEL, WEEKDAYS } from "../constants/domain";
import { formatDate, formatTime, toDateInputValue } from "../lib/format";

export default function ProviderProfile() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const preferredService = params.get("service");

  const detail = useQuery({ queryKey: ["provider", id], queryFn: () => providers.detail(id) });
  const trust = useQuery({ queryKey: ["provider-trust", id], queryFn: () => providers.trust(id) });
  const reviews = useQuery({ queryKey: ["provider-reviews", id], queryFn: () => providers.reviews(id) });
  const calendar = useQuery({
    queryKey: ["provider-calendar", id],
    queryFn: () => providers.calendar(id, { start: toDateInputValue(new Date()), days: 7 }),
  });

  if (detail.isLoading) return <PageLoader />;
  if (detail.error) return <ErrorMessage error={detail.error} />;

  const p = detail.data;
  const bookable = p.offerings.filter((o) => o.isActive);
  const requestLink = `/request-service?provider=${p.id}${preferredService ? `&service=${preferredService}` : ""}`;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px] lg:grid-rows-[auto_auto_auto_1fr]">
        <header className="card p-5 lg:col-start-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="page-title">{p.displayName}</h1>
            {!p.identityVerified && <Badge tone="warn">Identity not yet verified</Badge>}
            {!p.isAcceptingWork && <Badge tone="muted">Not taking jobs right now</Badge>}
          </div>
          <p className="mt-1 text-sm text-slate-600">
            {p.experienceYears > 0 ? `${p.experienceYears} years of experience` : "Experience not stated"}
            {p.serviceAreas.length > 0 && ` · Serves ${p.serviceAreas.map((a) => a.location?.name).join(", ")}`}
          </p>
          {p.bio && <p className="mt-3 whitespace-pre-line text-slate-700">{p.bio}</p>}
          <div className="mt-5">
            <Button to={requestLink} size="lg" disabled={!p.isAcceptingWork || bookable.length === 0}>
              Request {p.displayName.split(" ")[0]}
            </Button>
          </div>
        </header>

        <aside className="space-y-4 lg:sticky lg:top-24 lg:col-start-2 lg:row-span-4 lg:row-start-1 lg:self-start">
          {trust.isLoading && <PageLoader />}
          <ErrorMessage error={trust.error} />
          {trust.data && <TrustBreakdown trust={trust.data} />}
          <Link to="/providers" className="block text-center text-sm font-semibold text-brand-700">← Back to providers</Link>
        </aside>

        <section className="card p-5 lg:col-start-1" aria-labelledby="prices-heading">
          <h2 id="prices-heading" className="section-title">Services and prices</h2>
          {bookable.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">No services listed yet.</p>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {bookable.map((o) => (
                <li key={o.id} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <p className="font-medium text-ink">{o.service?.name}</p>
                    {o.priceFlag && o.priceFlag !== "normal" && (
                      <p className={`text-xs ${o.priceFlag === "high" ? "text-amber-700" : "text-sky-700"}`}>
                        {PRICE_FLAG_LABEL[o.priceFlag]}
                      </p>
                    )}
                  </div>
                  <Money value={o.price} className="text-lg font-bold text-ink" />
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card p-5 lg:col-start-1" aria-labelledby="availability-heading">
          <h2 id="availability-heading" className="section-title">Availability this week</h2>
          {calendar.isLoading ? (
            <PageLoader />
          ) : (
            <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {(calendar.data ?? []).map((day) => (
                <li key={day.date} className={`rounded-xl border p-3 text-sm ${day.windows.length ? "border-brand-200 bg-brand-50" : "border-slate-200 bg-slate-50 text-slate-400"}`}>
                  <p className="font-semibold">{WEEKDAYS[(new Date(`${day.date}T00:00:00`).getDay() + 6) % 7].slice(0, 3)}, {formatDate(day.date).split(" ").slice(0, 2).join(" ")}</p>
                  {day.windows.length ? (
                    day.windows.map((w) => (
                      <p key={w.startTime} className="text-xs text-brand-800">{formatTime(w.startTime)}–{formatTime(w.endTime)}</p>
                    ))
                  ) : (
                    <p className="text-xs">Unavailable</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card p-5 lg:col-start-1 lg:self-start" aria-labelledby="reviews-heading">
          <h2 id="reviews-heading" className="section-title">
            Reviews {reviews.data?.count ? `(${reviews.data.count})` : ""}
          </h2>
          <p className="mt-1 text-xs text-slate-500">Only customers with a completed job can review. Reviews are revealed once both sides have rated.</p>
          {reviews.data?.results.length === 0 && <p className="mt-3 text-sm text-slate-500">No published reviews yet.</p>}
          <ul className="mt-2 divide-y divide-slate-100">
            {(reviews.data?.results ?? []).map((r) => (
              <li key={r.id} className="py-4">
                <div className="flex items-center justify-between">
                  <Stars value={r.rating} />
                  <span className="text-xs text-slate-500">{formatDate(r.createdAt)}</span>
                </div>
                <p className="mt-1 text-sm font-medium text-ink">{r.customerName}</p>
                {r.comment && <p className="mt-1 text-sm text-slate-700">{r.comment}</p>}
                {r.reply && (
                  <div className="mt-2 rounded-xl bg-slate-50 p-3 text-sm">
                    <p className="text-xs font-semibold text-slate-500">Reply from {p.displayName}</p>
                    <p className="mt-0.5 text-slate-700">{r.reply.body}</p>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
    </div>
  );
}
