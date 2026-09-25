export const BOOKING_STATE = Object.freeze({
  SCHEDULED: "scheduled",
  IN_PROGRESS: "in_progress",
  AWAITING_CONFIRM: "awaiting_confirm",
  COMPLETED: "completed",
  CANCELLED_CUSTOMER: "cancelled_customer",
  CANCELLED_PROVIDER: "cancelled_provider",
  DISPUTED: "disputed",
});

export const BOOKING_STATE_LABEL = Object.freeze({
  [BOOKING_STATE.SCHEDULED]: "Scheduled",
  [BOOKING_STATE.IN_PROGRESS]: "In progress",
  [BOOKING_STATE.AWAITING_CONFIRM]: "Awaiting confirmation",
  [BOOKING_STATE.COMPLETED]: "Completed",
  [BOOKING_STATE.CANCELLED_CUSTOMER]: "Cancelled by customer",
  [BOOKING_STATE.CANCELLED_PROVIDER]: "Cancelled by provider",
  [BOOKING_STATE.DISPUTED]: "Disputed",
});

export const BOOKING_STATE_TONE = Object.freeze({
  [BOOKING_STATE.SCHEDULED]: "info",
  [BOOKING_STATE.IN_PROGRESS]: "info",
  [BOOKING_STATE.AWAITING_CONFIRM]: "warn",
  [BOOKING_STATE.COMPLETED]: "good",
  [BOOKING_STATE.CANCELLED_CUSTOMER]: "muted",
  [BOOKING_STATE.CANCELLED_PROVIDER]: "bad",
  [BOOKING_STATE.DISPUTED]: "bad",
});

export const OPEN_BOOKING_STATES = Object.freeze([
  BOOKING_STATE.SCHEDULED,
  BOOKING_STATE.IN_PROGRESS,
  BOOKING_STATE.AWAITING_CONFIRM,
]);

export const CANCELLABLE_STATES = Object.freeze([
  BOOKING_STATE.SCHEDULED,
  BOOKING_STATE.IN_PROGRESS,
]);

export const REQUEST_STATE = Object.freeze({
  OPEN: "open",
  ACCEPTED: "accepted",
  WITHDRAWN: "withdrawn",
  EXPIRED: "expired",
});

export const REQUEST_STATE_LABEL = Object.freeze({
  [REQUEST_STATE.OPEN]: "Waiting for a provider",
  [REQUEST_STATE.ACCEPTED]: "Accepted",
  [REQUEST_STATE.WITHDRAWN]: "Withdrawn",
  [REQUEST_STATE.EXPIRED]: "Expired unanswered",
});

export const TRUST_TIER = Object.freeze({
  NEW: "new",
  RISING: "rising",
  ESTABLISHED: "established",
  TRUSTED_PRO: "trusted_pro",
  UNDER_REVIEW: "under_review",
});

export const TRUST_TIER_LABEL = Object.freeze({
  [TRUST_TIER.NEW]: "New",
  [TRUST_TIER.RISING]: "Rising",
  [TRUST_TIER.ESTABLISHED]: "Established",
  [TRUST_TIER.TRUSTED_PRO]: "Trusted Pro",
  [TRUST_TIER.UNDER_REVIEW]: "Under review",
});

export const TRUST_TIER_BLURB = Object.freeze({
  [TRUST_TIER.NEW]: "Not enough completed jobs yet to judge. Shown honestly as new.",
  [TRUST_TIER.RISING]: "A good early record that is still building history.",
  [TRUST_TIER.ESTABLISHED]: "Proven, reliable and well reviewed over many jobs.",
  [TRUST_TIER.TRUSTED_PRO]: "A long, consistently strong record.",
  [TRUST_TIER.UNDER_REVIEW]: "Flagged for review. Booking is paused.",
});

export const ROLE = Object.freeze({
  CUSTOMER: "customer",
  PROVIDER: "provider",
  ADMIN: "admin",
});

export const PRICE_FLAG_LABEL = Object.freeze({
  low: "Below typical price",
  normal: "Typical price",
  high: "Above typical price",
});

export const PRICING_MODEL_LABEL = Object.freeze({
  fixed: "Fixed price",
  hourly: "Per hour",
  visit_quote: "Visit fee, then quote",
});

export const WEEKDAYS = Object.freeze([
  "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]);

export const LEDGER_KIND_LABEL = Object.freeze({
  earning: "Earning",
  commission: "Platform commission",
  cash_retained: "Cash kept by you",
  settlement: "Paid to platform",
  payout: "Paid to you",
  adjustment: "Adjustment",
});

export const COMPARE_LIMIT = 3;
