const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

let authToken = localStorage.getItem("aipt_token") || "";

export function setAuthToken(token) {
  authToken = token || "";
  if (authToken) {
    localStorage.setItem("aipt_token", authToken);
  } else {
    localStorage.removeItem("aipt_token");
  }
}

export function getAuthToken() {
  return authToken;
}

export async function apiRequest(path, options = {}) {
  const { auth = true, ...fetchOptions } = options;
  const headers = new Headers(fetchOptions.headers || {});
  const isFormData = fetchOptions.body instanceof FormData;
  if (!isFormData && fetchOptions.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (auth && authToken) {
    headers.set("Authorization", `Token ${authToken}`);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...fetchOptions,
      headers,
      body: isFormData || typeof fetchOptions.body === "string" ? fetchOptions.body : JSON.stringify(fetchOptions.body),
    });
  } catch (cause) {
    const error = new Error(`Không kết nối được backend tại ${API_BASE_URL}. Hãy kiểm tra Django server đang chạy.`);
    error.cause = cause;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(getErrorMessage(payload) || "Request failed.");
    error.status = response.status;
    error.data = payload;
    throw error;
  }
  return payload;
}

function getErrorMessage(payload) {
  if (!payload || typeof payload !== "object") return "";
  if (payload.detail) return String(payload.detail);
  if (Array.isArray(payload.non_field_errors)) return payload.non_field_errors.join(" ");

  const fieldErrors = Object.entries(payload)
    .map(([field, value]) => {
      if (Array.isArray(value)) return `${field}: ${value.join(" ")}`;
      if (typeof value === "string") return `${field}: ${value}`;
      return "";
    })
    .filter(Boolean);

  return fieldErrors.join(" ");
}
