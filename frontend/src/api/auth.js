import { apiRequest, setAuthToken } from "./client";


export async function register(data) {
  const result = await apiRequest("/auth/register/", { method: "POST", body: data, auth: false });
  setAuthToken(result.token);
  return result;
}

export async function login(data) {
  const result = await apiRequest("/auth/login/", { method: "POST", body: data, auth: false });
  setAuthToken(result.token);
  return result;
}

export async function logout() {
  await apiRequest("/auth/logout/", { method: "POST" }).catch(() => null);
  setAuthToken("");
}

export function me() {
  return apiRequest("/auth/me/");
}
