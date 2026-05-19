import { Activity, Flame, LoaderCircle, Percent, Save, Scale, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getProfile, profileAdvice, saveProfile } from "../api/profile";
import { FocusMuscles } from "../components/FocusMuscles";
import { ErrorBanner, Field, SelectInput, TextArea, TextInput } from "../components/FormControls";
import { ProfileCompletionNotice } from "../components/ProfileCompletionNotice";
import { getProfileCompleteness } from "../utils/profileCompleteness";


function listToText(value) {
  return Array.isArray(value) ? value.join(", ") : "";
}

function textToList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function hasDisplayValue(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.some(hasDisplayValue);
  if (typeof value === "object") return Object.values(value).some(hasDisplayValue);
  return true;
}

function displayText(value, fallback = "-") {
  if (!hasDisplayValue(value)) return fallback;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

const metricCards = [
  { key: "bmi", label: "BMI", unit: "", icon: Scale },
  { key: "bmr_kcal", label: "BMR", unit: "kcal", icon: Flame },
  { key: "tdee_kcal", label: "TDEE", unit: "kcal", icon: Activity },
  { key: "bodyfat_percent", label: "Body fat", unit: "%", icon: Percent },
];

function MetricCards({ metrics }) {
  if (!hasDisplayValue(metrics)) {
    return <p className="text-sm text-slate-500">No metrics analyzed yet.</p>;
  }

  const notes = Object.values(metrics.notes || {}).filter(hasDisplayValue);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        {metricCards.map((item) => {
          const Icon = item.icon;
          const value = metrics[item.key];
          const hasValue = hasDisplayValue(value);
          return (
            <article key={item.key} className="rounded-2xl border border-slate-200 bg-slate-50 p-2 lg:p-3 xl:p-4">
              <div className="mb-2 lg:mb-3 flex items-center justify-between gap-2 lg:gap-3">
                <p className="text-xs font-semibold uppercase text-slate-500">{item.label}</p>
                <Icon size={16} className="text-brand-600" />
              </div>
              <p className="text-lg lg:text-xl xl:text-2xl font-semibold text-slate-950">
                {displayText(value)}
                {hasValue && item.unit ? <span className="ml-1 text-xs lg:text-sm text-slate-500">{item.unit}</span> : null}
              </p>
            </article>
          );
        })}
      </div>
      {notes.length ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {notes.map((note, index) => (
            <div key={`metric-note-${index}`}>{renderAdviceValue(note, `metric-note-${index}`)}</div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function labelFromKey(key) {
  return String(key).replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function AnalyzingAdvice() {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-brand-100 bg-brand-50/70 px-4 py-3 text-brand-700">
      <LoaderCircle size={18} className="animate-spin" />
      <span className="text-sm font-semibold">
        Analyzing<span className="loading-dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
      </span>
    </div>
  );
}

function renderAdviceValue(value, keyPrefix = "advice") {
  if (!hasDisplayValue(value)) return null;
  if (Array.isArray(value)) {
    const items = value.filter(hasDisplayValue);
    return (
      <ul className="space-y-2 text-sm leading-6">
        {items.map((item, index) => (
          <li key={`${keyPrefix}-${index}`}>
            {typeof item === "object" ? renderAdviceValue(item, `${keyPrefix}-${index}`) : <span>- {String(item)}</span>}
          </li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object") {
    const entries = Object.entries(value).filter(([, item]) => hasDisplayValue(item));
    return (
      <div className="space-y-2 text-sm leading-6">
        {entries.map(([key, item]) => (
          <div key={`${keyPrefix}-${key}`}>
            <span className="font-semibold">{labelFromKey(key)}:</span>
            {typeof item === "object" ? (
              <div className="mt-1 pl-3">{renderAdviceValue(item, `${keyPrefix}-${key}`)}</div>
            ) : (
              <span> {String(item)}</span>
            )}
          </div>
        ))}
      </div>
    );
  }
  return <span className="text-sm leading-6">{String(value)}</span>;
}

function listValue(value) {
  if (!hasDisplayValue(value)) return [];
  return Array.isArray(value) ? value.filter(hasDisplayValue) : [value];
}

function AdviceList({ title, items, keyPrefix }) {
  if (!items.length) return null;
  return (
    <div>
      <p className="mb-2 text-sm font-semibold uppercase">{title}</p>
      <ul className="space-y-2 text-sm leading-6">
        {items.map((item, index) => (
          <li key={`${keyPrefix}-${index}`}>
            {typeof item === "object" ? renderAdviceValue(item, `${keyPrefix}-${index}`) : <span>- {String(item)}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function AdviceText({ advice }) {
  if (!hasDisplayValue(advice)) {
    return <p className="text-sm text-slate-500">No advice generated yet.</p>;
  }

  if (typeof advice !== "object") {
    return <div className="text-brand-700">{renderAdviceValue(advice)}</div>;
  }

  const shownKeys = new Set(["summary", "advice", "message", "recommendations", "risks", "suggested_goal", "safety_note"]);
  const summary = advice.summary ?? advice.advice ?? advice.message;
  const recommendations = listValue(advice.recommendations);
  const risks = listValue(advice.risks);
  const suggestedGoal = advice.suggested_goal;
  const safetyNote = advice.safety_note;
  const extraEntries = Object.entries(advice).filter(([key, value]) => !shownKeys.has(key) && hasDisplayValue(value));

  return (
    <div className="space-y-4 text-brand-700">
      {hasDisplayValue(summary) ? <div className="text-base font-semibold leading-7">{renderAdviceValue(summary, "summary")}</div> : null}
      <AdviceList title="Recommendations" items={recommendations} keyPrefix="recommendation" />
      <AdviceList title="Risks" items={risks} keyPrefix="risk" />
      {hasDisplayValue(suggestedGoal) ? (
        <div className="text-sm leading-6">
          <p className="mb-1 font-semibold">Suggested goal</p>
          {renderAdviceValue(suggestedGoal, "suggested-goal")}
        </div>
      ) : null}
      {hasDisplayValue(safetyNote) ? <div className="border-t border-brand-100 pt-3 text-sm leading-6">{renderAdviceValue(safetyNote, "safety-note")}</div> : null}
      {extraEntries.map(([key, value]) => (
        <div key={key} className="border-t border-brand-100 pt-3">
          <p className="mb-2 text-sm font-semibold uppercase">{labelFromKey(key)}</p>
          {renderAdviceValue(value, key)}
        </div>
      ))}
    </div>
  );
}

const emptyProfile = {
  full_name: "",
  sex: "",
  birth_year: "",
  height_cm: "",
  weight_kg: "",
  waist_cm: "",
  neck_cm: "",
  hip_cm: "",
  activity_level: "moderate",
  experience_level: "beginner",
  goal_type: "recomp",
  focus_muscles: [],
};

export default function ProfilePage() {
  const [profile, setProfile] = useState(emptyProfile);
  const [preferences, setPreferences] = useState({
    dietary_style: "none",
    allergies: "",
    favorite_foods: "",
    disliked_foods: "",
    avoid_ingredients: "",
    medical_conditions: "",
    notes: "",
  });
  const [metrics, setMetrics] = useState(null);
  const [advice, setAdvice] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [adviceLoading, setAdviceLoading] = useState(false);

  useEffect(() => {
    getProfile()
      .then((data) => {
        const { goal_text: _goalText, ...profileData } = data.profile || {};
        setProfile({ ...emptyProfile, ...profileData });
        setMetrics(data.metrics || null);
        setAdvice(data.advice || null);
        setPreferences({
          ...data.preferences,
          allergies: listToText(data.preferences.allergies),
          favorite_foods: listToText(data.preferences.favorite_foods),
          disliked_foods: listToText(data.preferences.disliked_foods),
          avoid_ingredients: listToText(data.preferences.avoid_ingredients),
          medical_conditions: listToText(data.preferences.medical_conditions),
        });
      })
      .catch((err) => setError(err.message));
  }, []);

  const preferencePayload = useMemo(
    () => ({
      ...preferences,
      allergies: textToList(preferences.allergies),
      favorite_foods: textToList(preferences.favorite_foods),
      disliked_foods: textToList(preferences.disliked_foods),
      avoid_ingredients: textToList(preferences.avoid_ingredients),
      medical_conditions: textToList(preferences.medical_conditions),
    }),
    [preferences]
  );
  const completeness = useMemo(() => getProfileCompleteness(profile), [profile]);

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const { goal_text: _goalText, ...profilePayload } = profile;
      const result = await saveProfile({ profile: profilePayload, preferences: preferencePayload });
      const { goal_text: _savedGoalText, ...savedProfile } = result.profile || {};
      setProfile({ ...emptyProfile, ...savedProfile });
      setMetrics(result.metrics || null);
      setAdvice(result.advice || null);
      window.dispatchEvent(new Event("aipt:profile-focus-updated"));
      setSaving(false);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  async function handleAdvice() {
    setError("");
    if (!completeness.isComplete) {
      setError("Complete your profile before requesting AI advice.");
      return;
    }
    setAdvice(null);
    setAdviceLoading(true);
    try {
      setAdvice(await profileAdvice({ profile, metrics, preferences: preferencePayload }));
    } catch (err) {
      setError(err.message);
    } finally {
      setAdviceLoading(false);
    }
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">Profile</h1>
        <p className="page-subtitle">Primary source for body metrics, goals, diet preferences, and constraints.</p>
      </header>
      <ErrorBanner message={error} />


      <div className="mt-4 grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <section className="section">
          <h2 className="mb-4 text-lg font-semibold">Body and goals</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Full name">
              <TextInput value={profile.full_name || ""} onChange={(event) => setProfile({ ...profile, full_name: event.target.value })} />
            </Field>
            <Field label="Sex">
              <SelectInput value={profile.sex || ""} onChange={(event) => setProfile({ ...profile, sex: event.target.value })}>
                <option value="">Select</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
              </SelectInput>
            </Field>
            {["birth_year", "height_cm", "weight_kg", "waist_cm", "neck_cm", "hip_cm"].map((key) => (
              <Field key={key} label={key.replace("_", " ")}>
                <TextInput value={profile[key] || ""} onChange={(event) => setProfile({ ...profile, [key]: event.target.value })} />
              </Field>
            ))}
            <Field label="Activity level">
              <SelectInput value={profile.activity_level || "moderate"} onChange={(event) => setProfile({ ...profile, activity_level: event.target.value })}>
                <option value="sedentary">Sedentary</option>
                <option value="light">Light</option>
                <option value="moderate">Moderate</option>
                <option value="very_active">Very active</option>
                <option value="athlete">Athlete</option>
              </SelectInput>
            </Field>
            <Field label="Experience level">
              <SelectInput value={profile.experience_level || "beginner"} onChange={(event) => setProfile({ ...profile, experience_level: event.target.value })}>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </SelectInput>
            </Field>
            <Field label="Goal type">
              <SelectInput value={profile.goal_type || "recomp"} onChange={(event) => setProfile({ ...profile, goal_type: event.target.value })}>
                <option value="cut">Cut</option>
                <option value="bulk">Bulk</option>
                <option value="recomp">Recomp</option>
                <option value="maintain">Maintain</option>
              </SelectInput>
            </Field>
            <div className="sm:col-span-2 rounded-2xl border border-brand-100 bg-brand-50/60 p-4">
              <p className="mb-3 text-sm font-semibold text-brand-800">Current workout focus</p>
              <FocusMuscles muscles={profile.focus_muscles} />
            </div>
          </div>
        </section>

        <section className="section">
          <h2 className="mb-4 text-lg font-semibold">Nutrition preferences</h2>
          <div className="space-y-4">
            <Field label="Dietary style">
              <SelectInput value={preferences.dietary_style || "none"} onChange={(event) => setPreferences({ ...preferences, dietary_style: event.target.value })}>
                <option value="none">None</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="vegan">Vegan</option>
                <option value="halal">Halal</option>
                <option value="low_carb">Low carb</option>
                <option value="keto">Keto</option>
                <option value="mediterranean">Mediterranean</option>
              </SelectInput>
            </Field>
            {["allergies", "favorite_foods", "disliked_foods", "avoid_ingredients", "medical_conditions"].map((key) => (
              <Field key={key} label={key.replace("_", " ")}>
                <TextInput value={preferences[key] || ""} onChange={(event) => setPreferences({ ...preferences, [key]: event.target.value })} />
              </Field>
            ))}
            <Field label="Notes">
              <TextArea value={preferences.notes || ""} onChange={(event) => setPreferences({ ...preferences, notes: event.target.value })} />
            </Field>
          </div>
        </section>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          <Save size={16} />
          Save profile
        </button>
        <button className="btn-secondary" onClick={handleAdvice} disabled={!completeness.isComplete || adviceLoading}>
          <Sparkles size={16} />
          AI advice
        </button>
      </div>

      <div className="mt-5 grid gap-5">
        <section className="section">
          <h2 className="mb-4 text-lg font-semibold">Metrics</h2>
          <MetricCards metrics={metrics} />
        </section>
        <section className="section">
          <h2 className="mb-4 text-lg font-semibold">Advice</h2>
          {adviceLoading ? <AnalyzingAdvice /> : <AdviceText advice={advice} />}
        </section>
      </div>
    </div>
  );
}
