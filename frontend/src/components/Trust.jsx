import PropTypes from "prop-types";
import { useState } from "react";

import { TRUST_TIER, TRUST_TIER_BLURB, TRUST_TIER_LABEL } from "../constants/domain";
import { formatDuration, formatPercent } from "../lib/format";
import { moneyType, tierType, trustBreakdownShape } from "./propShapes";

const TIER_STYLE = {
  [TRUST_TIER.NEW]: "bg-slate-100 text-slate-700 ring-slate-300",
  [TRUST_TIER.RISING]: "bg-sky-50 text-sky-800 ring-sky-200",
  [TRUST_TIER.ESTABLISHED]: "bg-brand-50 text-brand-800 ring-brand-200",
  [TRUST_TIER.TRUSTED_PRO]: "bg-emerald-50 text-emerald-800 ring-emerald-300",
  [TRUST_TIER.UNDER_REVIEW]: "bg-rose-50 text-rose-800 ring-rose-200",
};

export function TrustBadge({ score, tier, size = "md" }) {
  const rounded = Math.round(Number(score ?? 0));
  const big = size === "lg";
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full ring-1 ring-inset ${TIER_STYLE[tier] ?? TIER_STYLE.new} ${big ? "px-3.5 py-1.5" : "px-2.5 py-1"}`}
      title={TRUST_TIER_BLURB[tier]}
    >
      <ShieldIcon className={big ? "h-5 w-5" : "h-4 w-4"} />
      <span className={`font-semibold uppercase tracking-wide ${big ? "text-sm" : "text-[11px]"}`}>
        {TRUST_TIER_LABEL[tier] ?? tier}
      </span>
      <span className={`font-bold tabular-nums ${big ? "text-base" : "text-xs"}`}>
        {rounded}
        <span className="font-medium">/100</span>
      </span>
    </span>
  );
}

TrustBadge.propTypes = {
  score: moneyType,
  tier: tierType.isRequired,
  size: PropTypes.oneOf(["md", "lg"]),
};

function ShieldIcon({ className }) {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className={className}>
      <path
        fillRule="evenodd"
        d="M10 1.5l6.5 2.4v5c0 4.2-2.8 7.9-6.5 9.4C6.3 16.8 3.5 13.1 3.5 8.9v-5L10 1.5zm3.2 6.3a.8.8 0 00-1.2-1l-2.8 3.2-1.2-1.2a.8.8 0 10-1.1 1.1l1.8 1.8a.8.8 0 001.2 0l3.3-3.9z"
        clipRule="evenodd"
      />
    </svg>
  );
}

ShieldIcon.propTypes = { className: PropTypes.string };

function Check({ ok, label }) {
  return (
    <li className="flex items-center justify-between py-2 text-sm">
      <span className="text-slate-700">{label}</span>
      {ok ? (
        <span className="inline-flex items-center gap-1 font-semibold text-emerald-700">
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
            <path fillRule="evenodd" d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z" clipRule="evenodd" />
          </svg>
          Verified
        </span>
      ) : (
        <span className="text-slate-500">Not yet</span>
      )}
    </li>
  );
}

Check.propTypes = { ok: PropTypes.bool, label: PropTypes.string.isRequired };

function Fact({ label, value, warn = false }) {
  return (
    <li className="flex items-center justify-between py-2 text-sm">
      <span className="text-slate-700">{label}</span>
      <span className={`font-semibold tabular-nums ${warn ? "text-rose-700" : "text-ink"}`}>{value}</span>
    </li>
  );
}

Fact.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.node.isRequired,
  warn: PropTypes.bool,
};

function FactorBar({ factor }) {
  const width = Math.max(0, Math.min(100, factor.score));
  const tone = width >= 75 ? "bg-emerald-500" : width >= 50 ? "bg-brand-500" : width >= 30 ? "bg-amber-500" : "bg-rose-500";
  return (
    <li className="py-2">
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-slate-700">{factor.label}</span>
        <span className="tabular-nums text-slate-500">
          <span className="font-semibold text-ink">{Math.round(factor.score)}</span>
          <span className="text-xs"> · weight {Math.round(factor.weight * 100)}%</span>
        </span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100" role="meter" aria-valuenow={Math.round(width)} aria-valuemin={0} aria-valuemax={100} aria-label={factor.label}>
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${width}%` }} />
      </div>
    </li>
  );
}

FactorBar.propTypes = {
  factor: PropTypes.shape({
    label: PropTypes.string.isRequired,
    score: PropTypes.number.isRequired,
    weight: PropTypes.number.isRequired,
  }).isRequired,
};

export function TrustBreakdown({ trust }) {
  const [explained, setExplained] = useState(false);
  const { evidence, verification } = trust;
  const cancellationHigh = (evidence.cancellationRate ?? 0) >= 15;

  return (
    <section className="card @container overflow-hidden" aria-labelledby="trust-heading">
      <div className="border-b border-slate-100 bg-gradient-to-br from-brand-50 to-white p-5">
        <h2 id="trust-heading" className="text-xs font-semibold uppercase tracking-wider text-brand-800">
          Provider trust
        </h2>
        <div className="mt-2">
          <TrustBadge score={trust.score} tier={trust.tier} size="lg" />
        </div>
        <p className="mt-2 text-sm text-slate-600">{TRUST_TIER_BLURB[trust.tier]}</p>
      </div>

      <div className="grid gap-x-8 p-5 @lg:grid-cols-2">
        <ul className="divide-y divide-slate-100">
          <Check ok={verification.identity} label="Identity verified (NID)" />
          <Check ok={verification.phone} label="Phone verified" />
          <Check ok={verification.skill} label="Trade certificate" />
          <Check ok={verification.address} label="Address confirmed" />
        </ul>
        <ul className="divide-y divide-slate-100">
          <Fact label="Jobs completed" value={evidence.jobsCompleted} />
          <Fact label="Completion rate" value={formatPercent(evidence.completionRate)} />
          <Fact label="Cancellation rate" value={formatPercent(evidence.cancellationRate)} warn={cancellationHigh} />
          <Fact label="Typical response" value={formatDuration(evidence.medianResponseSeconds)} />
        </ul>
      </div>

      <div className="border-t border-slate-100 px-5 py-4">
        <button
          type="button"
          onClick={() => setExplained((v) => !v)}
          className="text-sm font-semibold text-brand-700 hover:text-brand-800"
          aria-expanded={explained}
        >
          {explained ? "Hide how trust is scored" : "How trust is scored"}
        </button>
        {explained && (
          <div className="mt-3">
            <p className="text-sm text-slate-600">
              Trust is calculated from what this provider has actually done on ShebaLocal, not from
              a single star rating. Each factor is scored out of 100 and weighted:
            </p>
            <ul className="mt-2 divide-y divide-slate-100">
              {trust.factors.map((factor) => (
                <FactorBar key={factor.key} factor={factor} />
              ))}
            </ul>
            {trust.penalties > 0 && (
              <p className="mt-2 text-sm font-medium text-rose-700">
                {trust.penalties} points deducted for recent upheld disputes or no-shows.
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

TrustBreakdown.propTypes = { trust: trustBreakdownShape.isRequired };
