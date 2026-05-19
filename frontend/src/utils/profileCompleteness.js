export const REQUIRED_PROFILE_FIELDS = [
  ["sex", "Sex"],
  ["birth_year", "Birth year"],
  ["height_cm", "Height"],
  ["weight_kg", "Weight"],
  ["waist_cm", "Waist"],
  ["neck_cm", "Neck"],
  ["activity_level", "Activity level"],
  ["experience_level", "Experience level"],
  ["goal_type", "Goal type"],
];

function isBlank(value) {
  return value === null || value === undefined || (typeof value === "string" && value.trim() === "");
}

export function getMissingProfileFields(profile = {}) {
  const missing = REQUIRED_PROFILE_FIELDS
    .filter(([field]) => isBlank(profile[field]))
    .map(([field, label]) => ({ field, label }));

  if (profile.sex === "female" && isBlank(profile.hip_cm)) {
    missing.push({ field: "hip_cm", label: "Hip" });
  }

  return missing;
}

export function getProfileCompleteness(profile = {}) {
  const missingFields = getMissingProfileFields(profile);
  const total = REQUIRED_PROFILE_FIELDS.length + (profile.sex === "female" ? 1 : 0);
  const completed = Math.max(total - missingFields.length, 0);

  return {
    isComplete: missingFields.length === 0,
    missingFields,
    completionPercent: total ? Math.round((completed / total) * 100) : 100,
  };
}
