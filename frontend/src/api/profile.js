import { apiRequest } from "./client";


export function getProfile() {
  return apiRequest("/profile/");
}

export function saveProfile(data) {
  return apiRequest("/profile/", { method: "PATCH", body: data });
}

export function profileAdvice(data) {
  return apiRequest("/profile/advice/", { method: "POST", body: data });
}

