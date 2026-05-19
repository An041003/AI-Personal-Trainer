import { apiRequest } from "./client";


export function analyzeIntent(data) {
  return apiRequest("/workout/intent/analyze/", { method: "POST", body: data });
}

export function generateWorkoutPlan(data) {
  return apiRequest("/workout/plan/generate/", { method: "POST", body: data });
}

export function replaceWorkoutExercise(data) {
  return apiRequest("/workout/plan/replace-exercise/", { method: "POST", body: data });
}

export function addWorkoutExercise(data) {
  return apiRequest("/workout/plan/add-exercise/", { method: "POST", body: data });
}

export function getLatestWorkoutPlan() {
  return apiRequest("/workout/plan/latest/");
}

export function searchExercises(params = "") {
  return apiRequest(`/workout/exercises/search/${params}`);
}
