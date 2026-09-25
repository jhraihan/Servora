import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "../store/auth";
import { ApiError, request, withQuery } from "./client";

function respond(status, body) {
  return Promise.resolve(new Response(body === undefined ? "" : JSON.stringify(body), { status }));
}

describe("api client", () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    useAuthStore.setState({ access: "old-access", refresh: "old-refresh", user: { id: 1 } });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the bearer token", async () => {
    fetchMock.mockReturnValueOnce(respond(200, { ok: true }));
    await request("/me/");
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe("Bearer old-access");
  });

  it("refreshes once on 401 and retries with the new token", async () => {
    fetchMock.mockImplementation((url, init) => {
      if (url.endsWith("/auth/refresh/")) return respond(200, { access: "new-access", refresh: "new-refresh" });
      if (init.headers.Authorization === "Bearer new-access") return respond(200, { ok: true });
      return respond(401, { error: { code: "token_not_valid", message: "expired" } });
    });

    const data = await request("/me/");

    expect(data).toEqual({ ok: true });
    expect(useAuthStore.getState()).toMatchObject({ access: "new-access", refresh: "new-refresh" });
  });

  it("shares a single refresh between concurrent 401s", async () => {
    let refreshCalls = 0;
    fetchMock.mockImplementation((url, init) => {
      if (url.endsWith("/auth/refresh/")) {
        refreshCalls += 1;
        return respond(200, { access: "new-access", refresh: "new-refresh" });
      }
      if (init.headers.Authorization === "Bearer new-access") return respond(200, { url });
      return respond(401, { error: { code: "token_not_valid", message: "expired" } });
    });

    const results = await Promise.all([request("/a/"), request("/b/"), request("/c/")]);

    expect(refreshCalls).toBe(1);
    expect(results.map((r) => r.url)).toEqual(["/api/v1/a/", "/api/v1/b/", "/api/v1/c/"]);
  });

  it("refreshes before the first call after a reload instead of taking a 401", async () => {
    useAuthStore.setState({ access: null });
    fetchMock.mockImplementation((url, init) => {
      if (url.endsWith("/auth/refresh/")) return respond(200, { access: "new-access", refresh: "new-refresh" });
      if (init.headers.Authorization === "Bearer new-access") return respond(200, { url });
      return respond(401, { error: { code: "not_authenticated", message: "no token" } });
    });

    const results = await Promise.all([request("/a/"), request("/b/")]);

    const statuses = await Promise.all(fetchMock.mock.results.map((r) => r.value.then((res) => res.status)));
    expect(statuses).not.toContain(401);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh/"))).toHaveLength(1);
    expect(results.map((r) => r.url)).toEqual(["/api/v1/a/", "/api/v1/b/"]);
  });

  it("clears the session when the refresh token is rejected", async () => {
    fetchMock.mockImplementation((url) =>
      url.endsWith("/auth/refresh/")
        ? respond(401, { error: { code: "token_not_valid", message: "blacklisted" } })
        : respond(401, { error: { code: "token_not_valid", message: "expired" } }),
    );

    await expect(request("/me/")).rejects.toBeInstanceOf(ApiError);
    expect(useAuthStore.getState()).toMatchObject({ access: null, refresh: null, user: null });
  });

  it("turns the error envelope into an ApiError with field messages", async () => {
    fetchMock.mockReturnValueOnce(respond(400, {
      error: { code: "validation_error", message: "Invalid input.", details: { fields: { phone: ["Enter a valid number."] } } },
    }));

    const error = await request("/auth/register/", { method: "POST", body: {}, auth: false }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(400);
    expect(error.code).toBe("validation_error");
    expect(error.fieldError("phone")).toBe("Enter a valid number.");
  });

  it("does not attempt a refresh for anonymous calls", async () => {
    fetchMock.mockReturnValueOnce(respond(401, { error: { code: "no", message: "no" } }));
    await expect(request("/auth/login/", { method: "POST", body: {}, auth: false })).rejects.toThrow();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("reports an unreachable server as a network error", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    const error = await request("/me/").catch((e) => e);
    expect(error.code).toBe("network_error");
  });

  it("returns null for 204 responses", async () => {
    fetchMock.mockReturnValueOnce(Promise.resolve(new Response(null, { status: 204 })));
    expect(await request("/auth/logout/", { method: "POST", body: {} })).toBeNull();
  });
});

describe("withQuery", () => {
  it("drops empty values and encodes the rest", () => {
    expect(withQuery("/providers/", { service: 3, tier: "", verified_only: false, location: null, q: "a b" }))
      .toBe("/providers/?service=3&q=a+b");
  });

  it("returns the bare path when nothing is set", () => {
    expect(withQuery("/providers/", {})).toBe("/providers/");
  });
});
