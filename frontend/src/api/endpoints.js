import { request, withQuery } from "./client";
import * as n from "./normalize";

export const auth = {
  async register({ phone, password, fullName, role }) {
    const data = await request("/auth/register/", {
      method: "POST",
      auth: false,
      body: { phone, password, full_name: fullName, role },
    });
    return { user: n.user(data.user), otpSent: Boolean(data.otp_sent) };
  },
  async login({ phone, password }) {
    const data = await request("/auth/login/", {
      method: "POST",
      auth: false,
      body: { phone, password },
    });
    return { access: data.access, refresh: data.refresh, user: n.user(data.user) };
  },
  sendOtp: (phone) =>
    request("/auth/otp/send/", { method: "POST", auth: false, body: { phone } }),
  async verifyOtp({ phone, code }) {
    const data = await request("/auth/otp/verify/", {
      method: "POST",
      auth: false,
      body: { phone, code },
    });
    return { verified: Boolean(data.verified), user: n.user(data.user) };
  },
  logout: (refresh) =>
    request("/auth/logout/", { method: "POST", body: { refresh } }),
  me: async () => n.user(await request("/me/")),
  switchRole: async (role) =>
    n.user(await request("/me/switch-role/", { method: "POST", body: { role } })),
  addProfile: async (role) =>
    n.user(await request("/me/add-profile/", { method: "POST", body: { role } })),
};

export const catalogue = {
  categories: async () =>
    (await request("/categories/", { auth: false })).map(n.category),
  category: async (slug) =>
    n.category(await request(`/categories/${slug}/`, { auth: false })),
  services: async (params) =>
    n.page(await request(withQuery("/services/", params), { auth: false }), n.service),
  locationTree: async () =>
    (await request("/locations/tree/", { auth: false })).map(n.location),
};

export const providers = {
  search: async (params) =>
    n.page(
      await request(withQuery("/providers/", params), { auth: false }),
      n.providerSummary,
    ),
  detail: async (id) =>
    n.providerDetail(await request(`/providers/${id}/`, { auth: false })),
  trust: async (id) =>
    n.trustBreakdown(await request(`/providers/${id}/trust/`, { auth: false })),
  reviews: async (id, params) =>
    n.page(
      await request(withQuery(`/providers/${id}/reviews/`, params), { auth: false }),
      n.review,
    ),
  calendar: async (id, params) =>
    n.calendar(
      await request(withQuery(`/providers/${id}/availability/`, params), { auth: false }),
    ),
};

export const me = {
  profile: async () => n.providerDetail(await request("/provider/profile/")),
  updateProfile: async (fields) =>
    n.providerDetail(
      await request("/provider/profile/", {
        method: "PATCH",
        body: {
          display_name: fields.displayName,
          bio: fields.bio,
          experience_years: fields.experienceYears,
        },
      }),
    ),
  setAcceptingWork: (accepting) =>
    request("/provider/accepting-work/", {
      method: "POST",
      body: { is_accepting_work: accepting },
    }),
  offerings: async () => (await request("/provider/services/")).map(n.offering),
  addOffering: async ({ serviceId, price }) =>
    n.offering(
      await request("/provider/services/", {
        method: "POST",
        body: { service: serviceId, price },
      }),
    ),
  updateOffering: async (id, fields) =>
    n.offering(
      await request(`/provider/services/${id}/`, {
        method: "PATCH",
        body: {
          ...(fields.price !== undefined && { price: fields.price }),
          ...(fields.isActive !== undefined && { is_active: fields.isActive }),
        },
      }),
    ),
  removeOffering: (id) =>
    request(`/provider/services/${id}/`, { method: "DELETE" }),
  serviceAreas: async () => (await request("/provider/service-areas/")).map(n.serviceArea),
  setServiceAreas: async (locationIds) =>
    (
      await request("/provider/service-areas/", {
        method: "PUT",
        body: { location_ids: locationIds },
      })
    ).map(n.serviceArea),
  availability: async () =>
    (await request("/provider/availability/")).map(n.availabilityWindow),
  setAvailability: async (windows) =>
    (
      await request("/provider/availability/", {
        method: "PUT",
        body: {
          windows: windows.map((w) => ({
            weekday: w.weekday,
            start_time: w.startTime,
            end_time: w.endTime,
          })),
        },
      })
    ).map(n.availabilityWindow),
  verification: async () =>
    (await request("/provider/verification/")).map(n.verificationDocument),
  uploadVerification: async ({ documentType, file }) => {
    const form = new FormData();
    form.append("document_type", documentType);
    form.append("file", file);
    return n.verificationDocument(
      await request("/provider/verification/", { method: "POST", form }),
    );
  },
  trustHistory: async () =>
    n.page(await request("/provider/trust-history/"), n.trustSnapshot),
  inbox: async () => (await request("/provider/inbox/")).map(n.serviceRequest),
  dashboard: async () => n.dashboard(await request("/provider/dashboard/")),
  earnings: async (params) =>
    n.earnings(await request(withQuery("/provider/earnings/", params))),
  ledger: async (params) =>
    n.page(await request(withQuery("/provider/ledger/", params)), n.ledgerEntry),
  receivedReviews: async () =>
    n.page(await request("/provider/reviews/"), n.review),
  rateCustomer: ({ bookingId, rating, comment }) =>
    request("/provider/rate-customer/", {
      method: "POST",
      body: { booking: bookingId, rating, comment },
    }),
};

export const requests = {
  list: async (params) =>
    (await request(withQuery("/requests/", params))).map(n.serviceRequest),
  detail: async (id) => n.serviceRequest(await request(`/requests/${id}/`)),
  create: async (fields) =>
    n.serviceRequest(
      await request("/requests/", {
        method: "POST",
        body: {
          service: fields.serviceId,
          location: fields.locationId,
          address: fields.address,
          description: fields.description,
          preferred_start: fields.preferredStart,
          preferred_end: fields.preferredEnd,
          target_provider: fields.targetProviderId ?? null,
        },
      }),
    ),
  withdraw: (id) => request(`/requests/${id}/withdraw/`, { method: "POST", body: {} }),
  async respond(id, { accept, reason }) {
    const data = await request(`/requests/${id}/respond/`, {
      method: "POST",
      body: { accept, reason: reason ?? "" },
    });
    return data?.id ? n.booking(data) : null;
  },
};

export const bookings = {
  list: async (params) =>
    n.page(await request(withQuery("/bookings/", params)), n.booking),
  detail: async (id) => n.booking(await request(`/bookings/${id}/`)),
  start: async (id) =>
    n.booking(await request(`/bookings/${id}/start/`, { method: "POST", body: {} })),
  complete: async (id, finalPrice) =>
    n.booking(
      await request(`/bookings/${id}/complete/`, {
        method: "POST",
        body: finalPrice ? { final_price: finalPrice } : {},
      }),
    ),
  confirm: async (id, confirmedPrice) =>
    n.booking(
      await request(`/bookings/${id}/confirm/`, {
        method: "POST",
        body: confirmedPrice ? { confirmed_price: confirmedPrice } : {},
      }),
    ),
  cancel: async (id, reason) =>
    n.booking(
      await request(`/bookings/${id}/cancel/`, { method: "POST", body: { reason } }),
    ),
  dispute: async (id, reason) =>
    n.booking(
      await request(`/bookings/${id}/dispute/`, { method: "POST", body: { reason } }),
    ),
};

export const reviews = {
  mine: async () => (await request("/reviews/")).map(n.review),
  create: async (fields) =>
    n.review(
      await request("/reviews/", {
        method: "POST",
        body: {
          booking: fields.bookingId,
          rating: fields.rating,
          punctuality: fields.punctuality || null,
          quality: fields.quality || null,
          professionalism: fields.professionalism || null,
          price_fairness: fields.priceFairness || null,
          comment: fields.comment ?? "",
        },
      }),
    ),
  reply: async (id, body) =>
    n.review(await request(`/reviews/${id}/reply/`, { method: "POST", body: { body } })),
};
