import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import PropTypes from "prop-types";
import { useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";

import { bookings, me, requests } from "../api/endpoints";
import {
  BookingStateBadge, BookingTimeline, Money, RequestStateBadge, StarInput,
} from "../components/domain";
import { bookingShape } from "../components/propShapes";
import {
  Badge, Button, EmptyState, ErrorMessage, Field, PageHeader, PageLoader,
} from "../components/ui";
import {
  BOOKING_STATE, BOOKING_STATE_LABEL, CANCELLABLE_STATES, REQUEST_STATE,
} from "../constants/domain";
import { useSession } from "../hooks/useSession";
import { formatDateTime } from "../lib/format";

const TABS = [
  { key: "", label: "All" },
  { key: BOOKING_STATE.SCHEDULED, label: "Upcoming" },
  { key: BOOKING_STATE.AWAITING_CONFIRM, label: "To confirm" },
  { key: BOOKING_STATE.COMPLETED, label: "Completed" },
];

export function MyRequests() {
  const queryClient = useQueryClient();
  const location = useLocation();
  const { data, isLoading, error } = useQuery({ queryKey: ["my-requests"], queryFn: () => requests.list() });
  const withdraw = useMutation({
    mutationFn: requests.withdraw,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["my-requests"] }),
  });

  return (
    <>
      <PageHeader title="My requests" subtitle="Jobs you have posted and who has responded." action={<Button to="/request-service">New request</Button>} />
      {location.state?.created && (
        <div role="status" className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Request sent. Matching providers have been notified — you will see a booking here as soon as one accepts.
        </div>
      )}
      <ErrorMessage error={error || withdraw.error} />
      {isLoading ? (
        <PageLoader />
      ) : data.length === 0 ? (
        <EmptyState title="No requests yet" body="Tell us what needs fixing and local providers will respond." action={<Button to="/request-service">Request a service</Button>} />
      ) : (
        <ul className="space-y-3">
          {data.map((r) => (
            <li key={r.id} className="card p-5" data-testid="request-row">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-ink">{r.service?.name}</p>
                  <p className="text-sm text-slate-500">{r.location?.fullName} · {formatDateTime(r.preferredStart)}</p>
                </div>
                <RequestStateBadge state={r.state} />
              </div>
              <p className="mt-2 line-clamp-2 text-sm text-slate-700">{r.description}</p>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="text-slate-500">
                  {r.responseCount} response{r.responseCount === 1 ? "" : "s"}
                  {r.state === REQUEST_STATE.OPEN && ` · expires ${formatDateTime(r.expiresAt)}`}
                </span>
                {r.state === REQUEST_STATE.OPEN && (
                  <Button variant="ghost" size="sm" loading={withdraw.isPending && withdraw.variables === r.id} onClick={() => withdraw.mutate(r.id)}>
                    Withdraw
                  </Button>
                )}
                {r.state === REQUEST_STATE.ACCEPTED && (
                  <Link to="/my-bookings" className="font-semibold text-brand-700">View booking →</Link>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export function BookingList({ basePath, title, subtitle }) {
  const [params, setParams] = useSearchParams();
  const state = params.get("state") ?? "";
  const { data, isLoading, error } = useQuery({
    queryKey: ["bookings", state],
    queryFn: () => bookings.list({ state, page_size: 50 }),
  });

  return (
    <>
      <PageHeader title={title} subtitle={subtitle} />
      <div className="mb-4 flex gap-2 overflow-x-auto pb-1" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={state === t.key}
            onClick={() => setParams(t.key ? { state: t.key } : {})}
            className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium ${state === t.key ? "bg-brand-700 text-white" : "bg-white text-slate-700 ring-1 ring-slate-200"}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <ErrorMessage error={error} />
      {isLoading ? (
        <PageLoader />
      ) : data.results.length === 0 ? (
        <EmptyState title="Nothing here yet" body="Bookings appear once a provider accepts a request." />
      ) : (
        <ul className="space-y-3">
          {data.results.map((b) => (
            <li key={b.id}>
              <Link to={`${basePath}/${b.id}`} className="card flex items-center justify-between gap-3 p-5 hover:border-brand-300" data-testid="booking-row">
                <div>
                  <p className="font-semibold text-ink">{b.service?.name}</p>
                  <p className="text-sm text-slate-500">{b.providerName} · {formatDateTime(b.scheduledFor)}</p>
                </div>
                <div className="text-right">
                  <BookingStateBadge state={b.state} />
                  <p className="mt-1 text-sm font-semibold text-ink"><Money value={b.finalPrice ?? b.agreedPrice} /></p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

BookingList.propTypes = {
  basePath: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
  subtitle: PropTypes.string,
};

export function BookingDetail() {
  const { id } = useParams();
  const { isProvider } = useSession();
  const queryClient = useQueryClient();
  const { data: booking, isLoading, error } = useQuery({
    queryKey: ["booking", id],
    queryFn: () => bookings.detail(id),
  });

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ["booking", id] });
    queryClient.invalidateQueries({ queryKey: ["bookings"] });
    queryClient.invalidateQueries({ queryKey: ["provider-dashboard"] });
  }

  if (isLoading) return <PageLoader />;
  if (error) return <ErrorMessage error={error} />;

  const listPath = isProvider ? "/provider/bookings" : "/my-bookings";

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Link to={listPath} className="text-sm font-semibold text-brand-700">← All bookings</Link>

      <section className="card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="page-title">{booking.service?.name}</h1>
            <p className="mt-1 text-sm text-slate-600">Booking #{booking.id} · {formatDateTime(booking.scheduledFor)}</p>
          </div>
          <BookingStateBadge state={booking.state} />
        </div>

        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
          {isProvider ? (
            <div>
              <dt className="text-slate-500">Customer</dt>
              <dd className="font-medium text-ink">{booking.customerName || "Customer"}</dd>
              {booking.customerPhone && (
                <dd><a href={`tel:${booking.customerPhone}`} className="font-semibold text-brand-700">{booking.customerPhone}</a></dd>
              )}
            </div>
          ) : (
            <div>
              <dt className="text-slate-500">Provider</dt>
              <dd><Link to={`/providers/${booking.providerId}`} className="font-medium text-brand-700">{booking.providerName}</Link></dd>
            </div>
          )}
          <div>
            <dt className="text-slate-500">Address</dt>
            <dd className="whitespace-pre-line text-ink">{booking.address}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Agreed price</dt>
            <dd className="text-lg font-bold text-ink"><Money value={booking.agreedPrice} /></dd>
          </div>
          {booking.finalPrice && (
            <div>
              <dt className="text-slate-500">Amount recorded by provider</dt>
              <dd className="text-lg font-bold text-ink"><Money value={booking.finalPrice} /></dd>
            </div>
          )}
        </dl>

        {booking.cancelReason && (
          <p className="mt-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
            Cancelled by {booking.cancelledBy}: “{booking.cancelReason}”
          </p>
        )}
      </section>

      {isProvider ? <ProviderActions booking={booking} onDone={refresh} /> : <CustomerActions booking={booking} onDone={refresh} />}

      <section className="card p-5">
        <h2 className="section-title mb-4">Timeline</h2>
        <BookingTimeline events={booking.events} />
      </section>
    </div>
  );
}

function ReasonForm({ label, buttonLabel, variant = "danger", onSubmit, pending, error }) {
  const [reason, setReason] = useState("");
  const fieldId = `reason-${buttonLabel.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(reason);
      }}
    >
      <Field label={label} htmlFor={fieldId}>
        <textarea id={fieldId} className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
      </Field>
      <ErrorMessage error={error} />
      <Button type="submit" variant={variant} loading={pending} disabled={!reason.trim()}>{buttonLabel}</Button>
    </form>
  );
}

ReasonForm.propTypes = {
  label: PropTypes.string.isRequired,
  buttonLabel: PropTypes.string.isRequired,
  variant: PropTypes.string,
  onSubmit: PropTypes.func.isRequired,
  pending: PropTypes.bool,
  error: PropTypes.instanceOf(Error),
};

function CustomerActions({ booking, onDone }) {
  const [amount, setAmount] = useState(booking.finalPrice ?? booking.agreedPrice ?? "");
  const [mode, setMode] = useState(null);
  const confirm = useMutation({ mutationFn: () => bookings.confirm(booking.id, amount), onSuccess: onDone });
  const cancel = useMutation({ mutationFn: (reason) => bookings.cancel(booking.id, reason), onSuccess: onDone });
  const dispute = useMutation({ mutationFn: (reason) => bookings.dispute(booking.id, reason), onSuccess: onDone });

  if (booking.state === BOOKING_STATE.AWAITING_CONFIRM) {
    return (
      <section className="card space-y-4 border-amber-200 bg-amber-50/40 p-5">
        <h2 className="section-title">Is the job done?</h2>
        <p className="text-sm text-slate-700">
          {booking.providerName} has marked this job complete. Confirm the amount you actually paid in cash.
          If it does not match what they recorded, our team reviews it before anything is settled.
        </p>
        <Field label="Amount you paid (৳)" htmlFor="confirm-amount">
          <input id="confirm-amount" type="number" min="0" step="1" inputMode="decimal" className="input" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </Field>
        <ErrorMessage error={confirm.error} />
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => confirm.mutate()} loading={confirm.isPending} disabled={amount === ""}>Confirm and pay</Button>
          <Button variant="ghost" onClick={() => setMode(mode === "dispute" ? null : "dispute")}>Something went wrong</Button>
        </div>
        {mode === "dispute" && (
          <ReasonForm label="What went wrong?" buttonLabel="Open a dispute" onSubmit={dispute.mutate} pending={dispute.isPending} error={dispute.error} />
        )}
      </section>
    );
  }

  if (booking.state === BOOKING_STATE.COMPLETED) {
    return (
      <section className="card p-5">
        {booking.reviewSubmitted ? (
          <p className="text-sm text-slate-700">
            Thanks for your review. It will be published once {booking.providerName} has rated this job too, or after 14 days.
          </p>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-700">How did {booking.providerName} do? Your review helps other customers.</p>
            <Button to={`/review/${booking.id}`}>Leave a review</Button>
          </div>
        )}
      </section>
    );
  }

  if (CANCELLABLE_STATES.includes(booking.state)) {
    return (
      <section className="card p-5">
        {mode === "cancel" ? (
          <ReasonForm label="Why are you cancelling?" buttonLabel="Cancel booking" onSubmit={cancel.mutate} pending={cancel.isPending} error={cancel.error} />
        ) : (
          <Button variant="secondary" onClick={() => setMode("cancel")}>Cancel booking</Button>
        )}
      </section>
    );
  }

  return null;
}

CustomerActions.propTypes = { booking: bookingShape.isRequired, onDone: PropTypes.func.isRequired };

function ProviderActions({ booking, onDone }) {
  const [finalPrice, setFinalPrice] = useState(booking.agreedPrice ?? "");
  const [cancelling, setCancelling] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");

  const start = useMutation({ mutationFn: () => bookings.start(booking.id), onSuccess: onDone });
  const complete = useMutation({ mutationFn: () => bookings.complete(booking.id, finalPrice), onSuccess: onDone });
  const cancel = useMutation({ mutationFn: (reason) => bookings.cancel(booking.id, reason), onSuccess: onDone });
  const rate = useMutation({
    mutationFn: () => me.rateCustomer({ bookingId: booking.id, rating, comment }),
    onSuccess: onDone,
  });

  const cancelBlock = CANCELLABLE_STATES.includes(booking.state) && (
    <div className="border-t border-slate-100 pt-4">
      {cancelling ? (
        <ReasonForm label="Why are you cancelling? This counts against your trust score." buttonLabel="Cancel job" onSubmit={cancel.mutate} pending={cancel.isPending} error={cancel.error} />
      ) : (
        <Button variant="ghost" onClick={() => setCancelling(true)}>Cancel this job</Button>
      )}
    </div>
  );

  if (booking.state === BOOKING_STATE.SCHEDULED) {
    return (
      <section className="card space-y-4 p-5">
        <p className="text-sm text-slate-700">Tap start when you arrive at the customer&apos;s address.</p>
        <ErrorMessage error={start.error} />
        <Button onClick={() => start.mutate()} loading={start.isPending}>I have arrived — start job</Button>
        {cancelBlock}
      </section>
    );
  }

  if (booking.state === BOOKING_STATE.IN_PROGRESS) {
    return (
      <section className="card space-y-4 p-5">
        <Field label="Amount collected in cash (৳)" htmlFor="final-price" hint="The customer confirms this amount next.">
          <input id="final-price" type="number" min="0" step="1" inputMode="decimal" className="input" value={finalPrice} onChange={(e) => setFinalPrice(e.target.value)} />
        </Field>
        <ErrorMessage error={complete.error} />
        <Button onClick={() => complete.mutate()} loading={complete.isPending} disabled={finalPrice === ""}>Mark job complete</Button>
        {cancelBlock}
      </section>
    );
  }

  if (booking.state === BOOKING_STATE.AWAITING_CONFIRM) {
    return (
      <section className="card p-5 text-sm text-slate-700">
        Waiting for the customer to confirm. If they do not respond, the job confirms automatically after 72 hours.
      </section>
    );
  }

  if (booking.state === BOOKING_STATE.COMPLETED) {
    if (booking.customerRated) {
      return (
        <section className="card p-5 text-sm text-slate-700">
          You rated this customer. Their review of you is now published, or will be as soon as they submit it.
        </section>
      );
    }
    return (
      <section className="card space-y-4 p-5">
        <div>
          <h2 className="section-title">Rate this customer</h2>
          <p className="mt-1 text-sm text-slate-600">
            Reviews are double-blind: the customer&apos;s review of you stays sealed until you rate them too.
          </p>
        </div>
        <StarInput name="customer-rating" label="Your rating" value={rating} onChange={setRating} />
        <Field label="Comment (optional)" htmlFor="rate-comment">
          <textarea id="rate-comment" className="input" rows={2} value={comment} onChange={(e) => setComment(e.target.value)} />
        </Field>
        <ErrorMessage error={rate.error} />
        <Button onClick={() => rate.mutate()} loading={rate.isPending} disabled={!rating}>Submit rating</Button>
      </section>
    );
  }

  return (
    <section className="card p-5 text-sm text-slate-600">
      This booking is {BOOKING_STATE_LABEL[booking.state]?.toLowerCase()}. <Badge>No further action</Badge>
    </section>
  );
}

ProviderActions.propTypes = { booking: bookingShape.isRequired, onDone: PropTypes.func.isRequired };
