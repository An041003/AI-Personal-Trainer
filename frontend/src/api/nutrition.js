import { apiRequest } from "./client";


export function analyzeMetrics(data) {
  return apiRequest("/nutrition/metrics/", { method: "POST", body: data });
}

export function previewRulebase(data) {
  return apiRequest("/nutrition/rulebase/preview/", { method: "POST", body: data });
}

export function generateNutritionPlan(data) {
  return apiRequest("/nutrition/plan/generate/", { method: "POST", body: data });
}

export function replaceNutritionPlan(data) {
  return apiRequest("/nutrition/plan/replace/", { method: "POST", body: data });
}

export function getLatestNutritionPlan() {
  return apiRequest("/nutrition/plan/latest/");
}

export function searchAtoms(params = "") {
  return apiRequest(`/nutrition/atoms/search/${params}`);
}
