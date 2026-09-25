import PropTypes from "prop-types";

import { BOOKING_STATE, TRUST_TIER } from "../constants/domain";

export const moneyType = PropTypes.oneOfType([PropTypes.string, PropTypes.number]);

export const tierType = PropTypes.oneOf(Object.values(TRUST_TIER));

export const bookingStateType = PropTypes.oneOf(Object.values(BOOKING_STATE));

export const locationShape = PropTypes.shape({
  id: PropTypes.number.isRequired,
  name: PropTypes.string.isRequired,
  fullName: PropTypes.string,
});

export const serviceAreaShape = PropTypes.shape({
  id: PropTypes.number.isRequired,
  location: locationShape,
});

export const providerSummaryShape = PropTypes.shape({
  id: PropTypes.number.isRequired,
  displayName: PropTypes.string.isRequired,
  experienceYears: PropTypes.number,
  identityVerified: PropTypes.bool,
  skillVerified: PropTypes.bool,
  phoneVerified: PropTypes.bool,
  trustScore: moneyType,
  trustTier: tierType,
  jobsCompleted: PropTypes.number,
  jobsCancelled: PropTypes.number,
  medianResponseSeconds: PropTypes.number,
  fromPrice: moneyType,
  serviceAreas: PropTypes.arrayOf(serviceAreaShape),
});

export const trustFactorShape = PropTypes.shape({
  key: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  score: PropTypes.number.isRequired,
  weight: PropTypes.number.isRequired,
  contribution: PropTypes.number.isRequired,
});

export const trustBreakdownShape = PropTypes.shape({
  score: PropTypes.number.isRequired,
  tier: tierType.isRequired,
  verification: PropTypes.shape({
    phone: PropTypes.bool,
    identity: PropTypes.bool,
    skill: PropTypes.bool,
    address: PropTypes.bool,
  }).isRequired,
  evidence: PropTypes.shape({
    jobsCompleted: PropTypes.number,
    jobsAccepted: PropTypes.number,
    jobsCancelled: PropTypes.number,
    completionRate: PropTypes.number,
    cancellationRate: PropTypes.number,
    medianResponseSeconds: PropTypes.number,
  }).isRequired,
  factors: PropTypes.arrayOf(trustFactorShape).isRequired,
  penalties: PropTypes.number,
});

export const bookingEventShape = PropTypes.shape({
  id: PropTypes.number.isRequired,
  fromState: PropTypes.string,
  toState: PropTypes.string.isRequired,
  actor: PropTypes.string.isRequired,
  reason: PropTypes.string,
  metadata: PropTypes.object,
  createdAt: PropTypes.string.isRequired,
});

export const bookingShape = PropTypes.shape({
  id: PropTypes.number.isRequired,
  providerId: PropTypes.number,
  providerName: PropTypes.string,
  customerName: PropTypes.string,
  customerPhone: PropTypes.string,
  address: PropTypes.string,
  cancelReason: PropTypes.string,
  cancelledBy: PropTypes.string,
  reviewSubmitted: PropTypes.bool,
  customerRated: PropTypes.bool,
  state: bookingStateType.isRequired,
  scheduledFor: PropTypes.string,
  agreedPrice: moneyType,
  finalPrice: moneyType,
  service: PropTypes.shape({ name: PropTypes.string }),
  events: PropTypes.arrayOf(bookingEventShape),
});
