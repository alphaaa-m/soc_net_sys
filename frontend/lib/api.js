/**
 * Tiny fetch wrapper for the Chirp API.
 *
 * The JWT lives in localStorage (fine for this teaching project; a production
 * app would prefer httpOnly cookies) and is attached to every authenticated
 * request. Errors are normalised into ApiError with the backend's `detail`.
 */

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"
).replace(/\/$/, "");

const TOKEN_KEY = "chirp_token";

export function getToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function extractDetail(data) {
  if (!data) return null;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((error) => {
        const field = Array.isArray(error.loc)
          ? error.loc.filter((part) => part !== "body").join(".")
          : "";
        return field ? `${field}: ${error.msg}` : error.msg;
      })
      .join(" · ");
  }
  return null;
}

export async function api(
  path,
  { method = "GET", body, token, auth = true } = {},
) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const bearer = token ?? (auth ? getToken() : null);
  if (bearer) headers.Authorization = `Bearer ${bearer}`;

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Cannot reach the backend. Is it running on port 8000?",
      0,
      null,
    );
  }

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      extractDetail(data) || `Request failed (${response.status})`,
      response.status,
      data,
    );
  }
  return data;
}
