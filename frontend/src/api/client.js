import { useAuthStore } from "../store/auth";

const API_ROOT = "/api/v1";

export class ApiError extends Error {
  constructor({ status, code, message, details }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details ?? {};
  }

  get fields() {
    return this.details.fields ?? {};
  }

  fieldError(name) {
    const value = this.fields[name];
    return Array.isArray(value) ? value[0] : value ?? null;
  }
}

let refreshInFlight = null;

async function parse(response) {
  if (response.status === 204) return null;
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { error: { code: "bad_response", message: text.slice(0, 200) } };
  }
}

function toApiError(status, payload) {
  const error = payload?.error ?? {};
  return new ApiError({
    status,
    code: error.code ?? "http_error",
    message: error.message ?? `Request failed with status ${status}.`,
    details: error.details,
  });
}

async function send(path, { method, body, form, token }) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_ROOT}${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError({
      status: 0,
      code: "network_error",
      message: "Could not reach the server. Check your connection.",
    });
  }
  return { response, data: await parse(response) };
}

export function refreshSession() {
  if (refreshInFlight) return refreshInFlight;

  const { refresh, setTokens, clear } = useAuthStore.getState();
  if (!refresh) return Promise.resolve(null);

  refreshInFlight = send("/auth/refresh/", { method: "POST", body: { refresh } })
    .then(({ response, data }) => {
      if (!response.ok) {
        clear();
        return null;
      }
      setTokens({ access: data.access, refresh: data.refresh });
      return data.access;
    })
    .finally(() => {
      refreshInFlight = null;
    });

  return refreshInFlight;
}

export async function request(path, { method = "GET", body, form, auth = true } = {}) {
  const { access, refresh } = useAuthStore.getState();
  let token = auth ? access : null;
  if (auth && !token && refresh) token = await refreshSession();
  let { response, data } = await send(path, { method, body, form, token });

  if (response.status === 401 && auth && useAuthStore.getState().refresh) {
    const fresh = await refreshSession();
    if (fresh) {
      ({ response, data } = await send(path, { method, body, form, token: fresh }));
    }
  }

  if (!response.ok) throw toApiError(response.status, data);
  return data;
}

export function withQuery(path, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "" && value !== false) {
      query.set(key, String(value));
    }
  });
  const text = query.toString();
  return text ? `${path}?${text}` : path;
}
