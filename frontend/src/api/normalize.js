function list(items, mapper) {
  return Array.isArray(items) ? items.map(mapper) : [];
}

export function page(raw, mapper) {
  if (Array.isArray(raw)) {
    return { count: raw.length, next: null, previous: null, results: raw.map(mapper) };
  }
  return {
    count: raw?.count ?? 0,
    next: raw?.next ?? null,
    previous: raw?.previous ?? null,
    results: list(raw?.results, mapper),
  };
}

export function user(raw) {
  if (!raw) return null;
  return {
    id: raw.id,
    phone: raw.phone,
    email: raw.email,
    fullName: raw.full_name ?? "",
    phoneVerified: Boolean(raw.phone_verified),
    activeRole: raw.active_role,
    roles: raw.roles ?? [],
    hasCustomerProfile: Boolean(raw.customer_profile),
    providerId: raw.provider_profile?.id ?? null,
  };
}

export function category(raw) {
  return {
    id: raw.id,
    name: raw.name,
    slug: raw.slug,
    description: raw.description ?? "",
    icon: raw.icon ?? "",
    serviceCount: raw.service_count ?? null,
    services: list(raw.services, service),
  };
}

export function service(raw) {
  if (!raw) return null;
  return {
    id: raw.id,
    name: raw.name,
    slug: raw.slug,
    description: raw.description ?? "",
    categoryId: raw.category,
    categorySlug: raw.category_slug,
    categoryName: raw.category_name,
    pricingModel: raw.pricing_model,
    priceMin: raw.suggested_price_min,
    priceMax: raw.suggested_price_max,
    durationMinutes: raw.typical_duration_minutes,
  };
}

export function location(raw) {
  if (!raw) return null;
  return {
    id: raw.id,
    name: raw.name,
    slug: raw.slug,
    level: raw.level,
    parentId: raw.parent,
    parentName: raw.parent_name,
    fullName: raw.full_name ?? raw.name,
    children: list(raw.children, location),
  };
}

export function serviceArea(raw) {
  return {
    id: raw.id,
    locationId: raw.location,
    location: location(raw.location_detail),
    travelSurcharge: raw.travel_surcharge,
  };
}

export function offering(raw) {
  return {
    id: raw.id,
    serviceId: raw.service,
    service: service(raw.service_detail),
    price: raw.price,
    priceFlag: raw.price_flag,
    durationMinutes: raw.estimated_duration_minutes,
    notes: raw.notes ?? "",
    isActive: Boolean(raw.is_active),
  };
}

export function availabilityWindow(raw) {
  return {
    id: raw.id,
    weekday: raw.weekday,
    weekdayName: raw.weekday_name,
    startTime: raw.start_time?.slice(0, 5),
    endTime: raw.end_time?.slice(0, 5),
  };
}

export function calendar(raw) {
  return list(raw?.days, (day) => ({
    date: day.date,
    windows: list(day.windows, (w) => ({
      startTime: w.start_time.slice(0, 5),
      endTime: w.end_time.slice(0, 5),
    })),
  }));
}

function providerCore(raw) {
  return {
    id: raw.id,
    displayName: raw.display_name,
    experienceYears: raw.experience_years ?? 0,
    identityVerified: Boolean(raw.identity_verified),
    skillVerified: Boolean(raw.skill_verified),
    phoneVerified: Boolean(raw.phone_verified),
    trustScore: raw.trust_score,
    trustTier: raw.trust_tier,
    jobsCompleted: raw.jobs_completed ?? 0,
    jobsCancelled: raw.jobs_cancelled ?? 0,
    medianResponseSeconds: raw.median_response_seconds ?? null,
    serviceAreas: list(raw.service_areas, serviceArea),
  };
}

export function providerSummary(raw) {
  return { ...providerCore(raw), fromPrice: raw.from_price ?? null };
}

export function providerDetail(raw) {
  return {
    ...providerCore(raw),
    bio: raw.bio ?? "",
    isAcceptingWork: Boolean(raw.is_accepting_work),
    addressVerified: Boolean(raw.address_verified),
    jobsAccepted: raw.jobs_accepted ?? 0,
    trustComputedAt: raw.trust_computed_at,
    offerings: list(raw.offerings, offering),
    availability: list(raw.availability, availabilityWindow),
    workPhotos: list(raw.work_photos, (p) => ({
      id: p.id,
      image: p.image,
      caption: p.caption ?? "",
    })),
  };
}

export function trustBreakdown(raw) {
  const evidence = raw.evidence ?? {};
  const verification = raw.verification ?? {};
  return {
    score: raw.score,
    tier: raw.tier,
    algoVersion: raw.algo_version,
    computedAt: raw.computed_at,
    penalties: raw.penalties ?? 0,
    verification: {
      phone: Boolean(verification.phone_verified),
      identity: Boolean(verification.identity_verified),
      skill: Boolean(verification.skill_verified),
      address: Boolean(verification.address_verified),
    },
    evidence: {
      jobsCompleted: evidence.jobs_completed ?? 0,
      jobsAccepted: evidence.jobs_accepted ?? 0,
      jobsCancelled: evidence.jobs_cancelled ?? 0,
      completionRate: evidence.completion_rate ?? null,
      cancellationRate: evidence.cancellation_rate ?? null,
      medianResponseSeconds: evidence.median_response_seconds ?? null,
    },
    factors: list(raw.factors, (f) => ({
      key: f.key,
      label: f.label,
      score: f.score,
      weight: f.weight,
      contribution: f.contribution,
    })),
  };
}

export function trustSnapshot(raw) {
  return {
    id: raw.id,
    score: raw.score,
    tier: raw.tier,
    trigger: raw.trigger,
    createdAt: raw.created_at,
  };
}

export function review(raw) {
  return {
    id: raw.id,
    bookingId: raw.booking,
    providerId: raw.provider,
    customerName: raw.customer_name,
    rating: raw.rating,
    punctuality: raw.punctuality,
    quality: raw.quality,
    professionalism: raw.professionalism,
    priceFairness: raw.price_fairness,
    comment: raw.comment ?? "",
    reply: raw.reply ? { body: raw.reply.body, createdAt: raw.reply.created_at } : null,
    wasEdited: Boolean(raw.was_edited),
    createdAt: raw.created_at,
    isPublished: raw.is_published ?? true,
    isEditable: raw.is_editable ?? false,
    revealDeadline: raw.reveal_deadline ?? null,
    isHidden: Boolean(raw.is_hidden),
  };
}

export function providerResponse(raw) {
  return {
    id: raw.id,
    providerId: raw.provider,
    providerName: raw.provider_name,
    decision: raw.decision,
    reason: raw.reason ?? "",
    responseSeconds: raw.response_seconds,
    createdAt: raw.created_at,
  };
}

export function serviceRequest(raw) {
  return {
    id: raw.id,
    serviceId: raw.service,
    service: service(raw.service_detail),
    locationId: raw.location,
    location: location(raw.location_detail),
    address: raw.address ?? null,
    description: raw.description ?? "",
    kind: raw.kind,
    targetProviderId: raw.target_provider ?? null,
    preferredStart: raw.preferred_start,
    preferredEnd: raw.preferred_end,
    state: raw.state,
    expiresAt: raw.expires_at,
    closedAt: raw.closed_at,
    responseCount: raw.response_count ?? 0,
    createdAt: raw.created_at,
    responses: list(raw.responses, providerResponse),
  };
}

export function bookingEvent(raw) {
  return {
    id: raw.id,
    fromState: raw.from_state || null,
    toState: raw.to_state,
    actor: raw.actor,
    reason: raw.reason ?? "",
    metadata: raw.metadata ?? {},
    createdAt: raw.created_at,
  };
}

export function booking(raw) {
  return {
    id: raw.id,
    requestId: raw.request,
    providerId: raw.provider,
    providerName: raw.provider_name,
    service: service(raw.service_detail),
    address: raw.address,
    state: raw.state,
    scheduledFor: raw.scheduled_for,
    agreedPrice: raw.agreed_price,
    finalPrice: raw.final_price,
    customerConfirmedPrice: raw.customer_confirmed_price,
    acceptedAt: raw.accepted_at,
    startedAt: raw.started_at,
    completedAt: raw.completed_at,
    confirmedAt: raw.confirmed_at,
    cancelledAt: raw.cancelled_at,
    cancelledBy: raw.cancelled_by || null,
    cancelReason: raw.cancel_reason ?? "",
    autoConfirmed: Boolean(raw.auto_confirmed),
    createdAt: raw.created_at,
    events: list(raw.events, bookingEvent),
    customerName: raw.customer_name ?? null,
    customerPhone: raw.customer_phone ?? null,
    reviewSubmitted: Boolean(raw.review_submitted),
    customerRated: Boolean(raw.customer_rated),
  };
}

function totals(raw) {
  return {
    gross: raw?.gross ?? "0.00",
    commission: raw?.commission ?? "0.00",
    net: raw?.net ?? "0.00",
    jobs: raw?.jobs ?? 0,
  };
}

export function earnings(raw) {
  const summary = raw.summary ?? {};
  return {
    currency: raw.currency,
    period: raw.period,
    start: raw.start,
    end: raw.end,
    summary: {
      ...totals(summary),
      balance: summary.balance ?? "0.00",
      outstandingPayable: summary.outstanding_payable ?? "0.00",
      outstandingReceivable: summary.outstanding_receivable ?? "0.00",
      flaggedPayments: summary.flagged_payments ?? 0,
    },
    periods: list(raw.periods, (row) => ({ period: row.period, ...totals(row) })),
  };
}

export function ledgerEntry(raw) {
  return {
    id: raw.id,
    kind: raw.kind,
    amount: raw.amount,
    bookingId: raw.booking,
    description: raw.description ?? "",
    reference: raw.reference ?? "",
    createdAt: raw.created_at,
  };
}

export function dashboard(raw) {
  return {
    trust: {
      score: raw.trust?.score,
      tier: raw.trust?.tier,
      computedAt: raw.trust?.computed_at,
    },
    openRequests: raw.requests?.open ?? 0,
    bookings: {
      upcoming: raw.bookings?.upcoming ?? 0,
      inProgress: raw.bookings?.in_progress ?? 0,
      awaitingConfirm: raw.bookings?.awaiting_confirm ?? 0,
      next: list(raw.bookings?.next, booking),
    },
    earnings: {
      thisMonth: totals(raw.earnings?.this_month),
      outstandingPayable: raw.earnings?.outstanding_payable ?? "0.00",
    },
    isAcceptingWork: Boolean(raw.is_accepting_work),
  };
}

export function verificationDocument(raw) {
  return {
    id: raw.id,
    documentType: raw.document_type,
    documentTypeLabel: raw.document_type_display,
    status: raw.status,
    rejectionReason: raw.rejection_reason ?? "",
    createdAt: raw.created_at,
    reviewedAt: raw.reviewed_at,
  };
}
