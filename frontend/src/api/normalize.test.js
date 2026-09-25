import { describe, expect, it } from "vitest";

import * as n from "./normalize";

describe("normalisers", () => {
  it("keeps money as strings so no float arithmetic creeps in", () => {
    const booking = n.booking({
      id: 3, state: "completed", agreed_price: "1800.00", final_price: "2000.00",
      customer_confirmed_price: "2000.00", events: [],
    });
    expect(booking.agreedPrice).toBe("1800.00");
    expect(booking.finalPrice).toBe("2000.00");
    expect(typeof booking.finalPrice).toBe("string");
  });

  it("maps booking events and contact details", () => {
    const booking = n.booking({
      id: 1, state: "scheduled", events: [
        { id: 9, from_state: "", to_state: "scheduled", actor: "provider", metadata: {}, created_at: "2026-09-01T00:00:00Z" },
      ],
      customer_name: "Rumana Akter", customer_phone: "+8801912345678",
      review_submitted: false, customer_rated: true,
    });
    expect(booking.events[0]).toMatchObject({ fromState: null, toState: "scheduled", actor: "provider" });
    expect(booking.customerPhone).toBe("+8801912345678");
    expect(booking.customerRated).toBe(true);
  });

  it("maps the trust breakdown into readable groups", () => {
    const trust = n.trustBreakdown({
      score: 84.19, tier: "rising", algo_version: "v1.0",
      verification: { phone_verified: true, identity_verified: true, skill_verified: false, address_verified: false },
      evidence: { jobs_completed: 4, jobs_accepted: 4, jobs_cancelled: 0, completion_rate: 100, cancellation_rate: 0, median_response_seconds: 480 },
      factors: [{ key: "f1_verification", label: "Verification depth", score: 70, weight: 0.2, contribution: 14 }],
      penalties: 0,
    });
    expect(trust.verification).toEqual({ phone: true, identity: true, skill: false, address: false });
    expect(trust.evidence.medianResponseSeconds).toBe(480);
    expect(trust.factors[0].label).toBe("Verification depth");
  });

  it("wraps a bare list in the same page shape as a paginated response", () => {
    const page = n.page([{ id: 1, name: "Dhaka", level: "city" }], n.location);
    expect(page).toMatchObject({ count: 1, next: null, previous: null });
    expect(page.results[0].name).toBe("Dhaka");
  });

  it("survives missing optional structures", () => {
    const provider = n.providerDetail({ id: 5, display_name: "Kamal" });
    expect(provider.offerings).toEqual([]);
    expect(provider.serviceAreas).toEqual([]);
    expect(provider.jobsCompleted).toBe(0);
  });

  it("carries provider id through the user so provider pages can find themselves", () => {
    const user = n.user({ id: 2, phone: "+8801712345678", active_role: "provider", roles: ["provider"], provider_profile: { id: 7 } });
    expect(user.providerId).toBe(7);
    expect(user.hasCustomerProfile).toBe(false);
  });

  it("omits the address when the inbox withholds it", () => {
    const request = n.serviceRequest({ id: 1, state: "open", description: "AC", location_detail: { id: 2, name: "Dhanmondi" } });
    expect(request.address).toBeNull();
    expect(request.location.name).toBe("Dhanmondi");
  });
});
