import { Check, Database, Dumbbell, Plus, RefreshCw, Search, Target, Wand2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getProfile } from "../api/profile";
import {
  addWorkoutExercise,
  analyzeIntent,
  generateWorkoutPlan,
  getLatestWorkoutPlan,
  replaceWorkoutExercise,
  searchExercises,
} from "../api/workout";
import { FocusMuscles } from "../components/FocusMuscles";
import { ErrorBanner, Field, TextArea, TextInput } from "../components/FormControls";
import { getProfileCompleteness } from "../utils/profileCompleteness";


const trainingDayOptions = [
  { value: "mon", label: "Mon" },
  { value: "tue", label: "Tue" },
  { value: "wed", label: "Wed" },
  { value: "thu", label: "Thu" },
  { value: "fri", label: "Fri" },
  { value: "sat", label: "Sat" },
  { value: "sun", label: "Sun" },
];

const DAY_LABELS = trainingDayOptions.reduce((labels, day) => {
  labels[day.value] = day.label;
  return labels;
}, {});

const FULL_DAY_LABELS = {
  mon: "Monday",
  tue: "Tuesday",
  wed: "Wednesday",
  thu: "Thursday",
  fri: "Friday",
  sat: "Saturday",
  sun: "Sunday",
};

function normalizeDayKey(value) {
  const key = String(value || "").trim().toLowerCase().slice(0, 3);
  return DAY_LABELS[key] ? key : "";
}

function formatDayLabel(value, variant = "short") {
  const key = normalizeDayKey(value);
  if (key) return variant === "long" ? FULL_DAY_LABELS[key] : DAY_LABELS[key];
  const text = String(value || "Day").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Day";
}

function normalizeTrainingDays(value) {
  if (Array.isArray(value)) return value;
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function uniqueValues(values) {
  const seen = new Set();
  const result = [];

  (values || []).forEach((value) => {
    if (value === undefined || value === null || value === "") return;
    const key = String(value).trim().toLowerCase();
    if (!key || seen.has(key)) return;
    seen.add(key);
    result.push(value);
  });

  return result;
}

function formatList(values, fallback = "-") {
  const list = uniqueValues(values).map((item) => String(item));
  return list.length ? list.join(", ") : fallback;
}

function getWorkoutExerciseIds(workoutPlan) {
  return uniqueValues(
    (workoutPlan?.days || []).flatMap((day) =>
      (day?.exercises || []).map((exercise) => exercise?.exercise_id)
    )
  );
}

function getWorkoutExerciseTitles(workoutPlan) {
  return uniqueValues(
    (workoutPlan?.days || []).flatMap((day) =>
      (day?.exercises || []).map((exercise) => exercise?.title)
    )
  );
}

function exerciseReplacementKey(target = {}) {
  return `replace-exercise-${target.day_index ?? 0}-${target.exercise_index ?? 0}`;
}

function libraryActionKey(action, dayIndex, exerciseId) {
  return `library-${action}-${dayIndex}-${exerciseId}`;
}

function sharesMuscle(candidate, currentExercise) {
  const currentMuscles = new Set((currentExercise?.muscle_groups || []).map((item) => String(item).toLowerCase()));
  return (candidate?.muscle_groups || []).some((item) => currentMuscles.has(String(item).toLowerCase()));
}

function matchesExerciseSearch(exercise, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;

  const haystack = [
    exercise.title,
    exercise.body_part_raw,
    exercise.equipment,
    exercise.level,
    ...(exercise.muscle_groups || []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return haystack.includes(normalized);
}

function hasFocusMuscles(intent) {
  return Array.isArray(intent?.focus_muscles) && intent.focus_muscles.filter(Boolean).length > 0;
}

function ExerciseThumb({ exercise, size = "md" }) {
  const [failed, setFailed] = useState(false);
  const title = exercise?.title || `Exercise ${exercise?.exercise_id || exercise?.id || ""}`;
  const sizeClass = size === "sm" ? "h-11 w-11 rounded-xl" : "h-14 w-14 rounded-2xl";
  if (!exercise?.image_url || failed) {
    return (
      <div className={`grid shrink-0 place-items-center border border-dashed border-slate-300 bg-slate-50 text-xs font-semibold text-slate-400 ${sizeClass}`}>
        {String(title).trim().slice(0, 1).toUpperCase() || "?"}
      </div>
    );
  }

  return (
    <img
      src={exercise.image_url}
      alt=""
      className={`shrink-0 border border-slate-200 bg-white object-contain ${sizeClass}`}
      onError={() => setFailed(true)}
    />
  );
}

export default function WorkoutPage() {
  const [form, setForm] = useState({
    goal_text: "",
    days_per_week: 4,
    session_minutes: 60,
    training_days: ["mon", "wed", "fri", "sat"],
  });
  const [intent, setIntent] = useState(null);
  const [plan, setPlan] = useState(null);
  const [profileCompleteness, setProfileCompleteness] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState("");
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [libraryAction, setLibraryAction] = useState("add");
  const [libraryDayIndex, setLibraryDayIndex] = useState(0);
  const [libraryExerciseIndex, setLibraryExerciseIndex] = useState(0);
  const [exerciseDatabase, setExerciseDatabase] = useState([]);
  const [exerciseDatabaseLoaded, setExerciseDatabaseLoaded] = useState(false);
  const [exerciseDatabaseLoading, setExerciseDatabaseLoading] = useState(false);
  const [exerciseSearch, setExerciseSearch] = useState("");
  const [sessionMemory, setSessionMemory] = useState({
    avoid_exercise_ids: [],
    avoid_exercise_titles: [],
    last_replace_reason: "",
  });

  useEffect(() => {
    getProfile()
      .then((data) => {
        const profile = data.profile || {};
        setProfileCompleteness(getProfileCompleteness(profile));
        const focusMuscles = profile.focus_muscles || [];
        if (focusMuscles.length) {
          setIntent({ focus_muscles: focusMuscles });
        }
      })
      .catch((err) => setError(err.message));

    getLatestWorkoutPlan()
      .then((data) => setPlan(data || null))
      .catch((err) => setError(err.message));
  }, []);

  const profileReady = profileCompleteness?.isComplete === true;
  const workoutPlan = plan?.plan || null;
  const oldExerciseIds = useMemo(() => getWorkoutExerciseIds(workoutPlan), [workoutPlan]);
  const oldExerciseTitles = useMemo(() => getWorkoutExerciseTitles(workoutPlan), [workoutPlan]);
  const isBusy = Boolean(loading);
  const selectedLibraryDay = workoutPlan?.days?.[libraryDayIndex] || null;
  const selectedLibraryExercise = selectedLibraryDay?.exercises?.[libraryExerciseIndex] || null;
  const filteredExercises = useMemo(() => {
    return exerciseDatabase
      .filter((exercise) => matchesExerciseSearch(exercise, exerciseSearch))
      .sort((a, b) => {
        if (libraryAction !== "replace") {
          return String(a.title || "").localeCompare(String(b.title || ""));
        }
        const aSame = sharesMuscle(a, selectedLibraryExercise);
        const bSame = sharesMuscle(b, selectedLibraryExercise);
        if (aSame !== bSame) return aSame ? -1 : 1;
        return String(a.title || "").localeCompare(String(b.title || ""));
      });
  }, [exerciseDatabase, exerciseSearch, libraryAction, selectedLibraryExercise]);

  function intentPayload() {
    return {
      goal_text: form.goal_text,
    };
  }

  function planSettingsPayload() {
    const trainingDays = normalizeTrainingDays(form.training_days);
    return {
      days_per_week: trainingDays.length || Number(form.days_per_week || 3),
      session_minutes: Number(form.session_minutes || 60),
      training_days: trainingDays,
    };
  }

  function resetSessionMemory() {
    setSessionMemory({
      avoid_exercise_ids: [],
      avoid_exercise_titles: [],
      last_replace_reason: "",
    });
  }

  function toggleTrainingDay(day) {
    const currentDays = normalizeTrainingDays(form.training_days);
    const nextDays = currentDays.includes(day)
      ? currentDays.filter((item) => item !== day)
      : trainingDayOptions.map((item) => item.value).filter((item) => [...currentDays, day].includes(item));
    setForm({ ...form, training_days: nextDays, days_per_week: nextDays.length || "" });
  }

  async function handleAnalyze() {
    setLoading("intent");
    setError("");
    if (!form.goal_text.trim()) {
      setError("Enter your workout goal before analyzing intent.");
      setLoading("");
      return;
    }
    if (!profileReady) {
      setError("Complete your profile before analyzing workout intent.");
      setLoading("");
      return;
    }
    try {
      const result = await analyzeIntent(intentPayload());
      setIntent(result);
      setPlan(null);
      resetSessionMemory();
      window.dispatchEvent(new Event("aipt:profile-focus-updated"));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  async function handleGenerate() {
    setLoading("plan");
    setError("");
    if (!profileReady) {
      setError("Complete your profile before generating a workout plan.");
      setLoading("");
      return;
    }
    try {
      let internalGoal = intent;
      if (!hasFocusMuscles(internalGoal)) {
        if (!form.goal_text.trim()) {
          setError("Analyze a workout goal first or set focus muscles in Profile before generating a plan.");
          setLoading("");
          return;
        }
        internalGoal = await analyzeIntent(intentPayload());
      }
      setIntent(internalGoal);
      const generatedPlan = await generateWorkoutPlan({
        internal_goal: internalGoal,
        ...planSettingsPayload(),
        constraints: { max_exercises_per_day: 6, max_repair_iterations: 2 },
      });
      setPlan(generatedPlan);
      resetSessionMemory();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  async function ensureExerciseDatabase() {
    if (exerciseDatabaseLoaded || exerciseDatabaseLoading) return;

    setExerciseDatabaseLoading(true);
    setError("");
    try {
      const exercises = await searchExercises("?all=1");
      setExerciseDatabase(exercises || []);
      setExerciseDatabaseLoaded(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setExerciseDatabaseLoading(false);
    }
  }

  function openLibrary() {
    setLibraryOpen(true);
    setLibraryAction("add");
    setLibraryDayIndex(0);
    setLibraryExerciseIndex(0);
    setExerciseSearch("");
    ensureExerciseDatabase();
  }

  function updateReplacementMemory(updatedPlan, oldExercise, reasonCode) {
    const applied = updatedPlan.short_term_memory_applied || {};
    setSessionMemory((current) => ({
      avoid_exercise_ids: uniqueValues([
        ...(current.avoid_exercise_ids || []),
        oldExercise?.exercise_id,
        ...(applied.avoid_exercise_ids || []),
      ]).slice(-30),
      avoid_exercise_titles: uniqueValues([
        ...(current.avoid_exercise_titles || []),
        oldExercise?.title,
        ...(applied.avoid_exercise_titles || []),
      ]).slice(-30),
      last_replace_reason: reasonCode,
    }));
  }

  function buildReplacePayload(target, selectedExerciseId = null, reasonCode = "quick_change") {
    return {
      source_request_id: plan?.request_id,
      current_plan: workoutPlan,
      target,
      replace_request: {
        reason_code: reasonCode,
        old_exercise_ids: oldExerciseIds,
        old_exercise_titles: oldExerciseTitles,
        selected_exercise_id: selectedExerciseId,
        session_short_term_memory: sessionMemory,
      },
    };
  }

  async function handleQuickReplaceExercise(day, dayIndex, exercise, exerciseIndex) {
    if (!profileReady) {
      setError("Complete your profile before changing a workout plan.");
      return;
    }
    if (!workoutPlan) {
      setError("Generate a workout plan before changing an exercise.");
      return;
    }

    const target = {
      day_index: dayIndex,
      day: day.day,
      exercise_index: exerciseIndex,
      exercise_id: exercise.exercise_id,
      exercise_title: exercise.title,
    };
    const reasonCode = "quick_change";
    setLoading(exerciseReplacementKey(target));
    setError("");

    try {
      const updatedPlan = await replaceWorkoutExercise(buildReplacePayload(target, null, reasonCode));
      setPlan(updatedPlan);
      updateReplacementMemory(updatedPlan, exercise, reasonCode);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  async function handleLibrarySelect(exercise) {
    if (!profileReady) {
      setError("Complete your profile before editing a workout plan.");
      return;
    }
    if (!workoutPlan || !selectedLibraryDay) {
      setError("Generate a workout plan before using the exercise library.");
      return;
    }

    const action = libraryAction;
    const target = {
      day_index: libraryDayIndex,
      day: selectedLibraryDay.day,
    };
    const key = libraryActionKey(action, libraryDayIndex, exercise.id);
    setLoading(key);
    setError("");

    try {
      if (action === "add") {
        const updatedPlan = await addWorkoutExercise({
          source_request_id: plan?.request_id,
          current_plan: workoutPlan,
          target,
          exercise_id: exercise.id,
          add_request: {
            sets: 3,
            reps: "8-12",
            rest_sec: 90,
            notes: "Keep controlled form.",
          },
        });
        setPlan(updatedPlan);
      } else {
        if (!selectedLibraryExercise) {
          setError("Choose an exercise in the workout day to replace.");
          return;
        }
        const replaceTarget = {
          ...target,
          exercise_index: libraryExerciseIndex,
          exercise_id: selectedLibraryExercise.exercise_id,
          exercise_title: selectedLibraryExercise.title,
        };
        const reasonCode = "library_replace";
        const updatedPlan = await replaceWorkoutExercise(
          buildReplacePayload(replaceTarget, exercise.id, reasonCode)
        );
        setPlan(updatedPlan);
        updateReplacementMemory(updatedPlan, selectedLibraryExercise, reasonCode);
        setLibraryOpen(false);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">Workout</h1>
        <p className="page-subtitle">Intent analysis is separated from plan generation.</p>
      </header>
      <ErrorBanner message={error} />


      <div className="mt-4 flex flex-col gap-5">
        <section className="section">
          <div className="mb-4 flex items-center gap-3">
            <Target className="text-brand-600" size={22} />
            <h2 className="text-lg font-semibold">Focus muscles</h2>
          </div>
          {!intent ? (
            <FocusMuscles muscles={[]} />
          ) : (
            <FocusMuscles muscles={intent.focus_muscles} />
          )}
        </section>
        <section className="section">
          <div className="mb-4 flex items-center gap-3">
            <Dumbbell className="text-brand-600" size={22} />
            <h2 className="text-lg font-semibold">Step 1 - Intent analysis</h2>
          </div>
          <div className="space-y-4">
            <Field label="Goal text for focus muscle analysis">
              <TextArea
                placeholder="Example: giảm mỡ, vai rộng, rõ cơ bụng"
                value={form.goal_text}
                onChange={(event) => {
                  setForm({ ...form, goal_text: event.target.value });
                  setPlan(null);
                  resetSessionMemory();
                }}
              />
            </Field>
            <button className="btn-primary" onClick={handleAnalyze} disabled={!profileReady || loading === "intent"}>
              <Search size={16} />
              Analyze intent
            </button>
          </div>

          <div className="mt-8 border-t border-slate-200 pt-5">
            <div className="mb-4 flex items-center gap-3">
              <Wand2 className="text-brand-600" size={22} />
              <h2 className="text-lg font-semibold">Step 2 - Plan settings</h2>
            </div>
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Days per week">
                  <TextInput value={form.days_per_week} onChange={(event) => setForm({ ...form, days_per_week: event.target.value })} />
                </Field>
                <Field label="Session minutes">
                  <TextInput value={form.session_minutes} onChange={(event) => setForm({ ...form, session_minutes: event.target.value })} />
                </Field>
              </div>
              <Field label="Training days">
                <div className="grid grid-cols-4 gap-2 sm:grid-cols-7" role="group" aria-label="Training days">
                  {trainingDayOptions.map((day) => {
                    const selected = normalizeTrainingDays(form.training_days).includes(day.value);
                    return (
                      <button
                        key={day.value}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => toggleTrainingDay(day.value)}
                        className={`h-10 rounded border text-sm font-semibold transition ${
                          selected
                            ? "border-brand-600 bg-brand-600 text-white shadow-sm hover:bg-brand-700"
                            : "border-slate-200 bg-slate-100 text-slate-600 hover:border-slate-300 hover:bg-slate-200"
                        }`}
                      >
                        {day.label}
                      </button>
                    );
                  })}
                </div>
              </Field>
            </div>
            <div className="mt-5">
              <button className="btn-primary" onClick={handleGenerate} disabled={!profileReady || loading === "plan"}>
                <Wand2 size={16} />
                Generate plan
              </button>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Generate uses the current focus muscles. Goal text is only needed when you want AI to analyze a new focus.
              </p>
            </div>
          </div>
        </section>
      </div>

      <section className="section mt-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-semibold">Weekly plan</h2>
          {plan ? (
            <button
              type="button"
              className="btn-secondary justify-center rounded-xl"
              onClick={openLibrary}
              disabled={isBusy}
            >
              <Database size={16} />
              Open Library
            </button>
          ) : null}
        </div>
        {!plan ? (
          <p className="text-sm text-slate-500">No plan generated yet.</p>
        ) : (
          <div className="space-y-5">
            {(workoutPlan?.days || []).map((day, dayIndex) => (
              <div key={`${day.day}-${dayIndex}`} className="border-t border-slate-200 pt-4 first:border-t-0 first:pt-0">
                <h3 className="font-semibold">{formatDayLabel(day.day, "long")} - {day.title}</h3>
                <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {(day.exercises || []).map((exercise, exerciseIndex) => {
                    const target = {
                      day_index: dayIndex,
                      exercise_index: exerciseIndex,
                    };
                    const exerciseLoading = loading === exerciseReplacementKey(target);

                    return (
                      <article
                        key={`${day.day}-${exercise.exercise_id}-${exerciseIndex}`}
                        className="rounded-2xl border border-slate-200 bg-slate-50 p-3"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex min-w-0 items-start gap-3">
                            <ExerciseThumb exercise={exercise} />
                            <div className="min-w-0">
                              <p className="font-medium">{exercise.title || `Exercise ${exercise.exercise_id}`}</p>
                              <p className="mt-1 text-sm text-slate-600">
                                {exercise.sets} sets - {exercise.reps} reps - {exercise.rest_sec}s rest
                              </p>
                              <p className="mt-2 text-xs text-slate-500">{formatList(exercise.muscle_groups)}</p>
                            </div>
                          </div>
                          <button
                            type="button"
                            className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-600 transition hover:border-brand-200 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
                            onClick={() => handleQuickReplaceExercise(day, dayIndex, exercise, exerciseIndex)}
                            disabled={isBusy}
                          >
                            <RefreshCw size={13} className={exerciseLoading ? "animate-spin" : ""} />
                            {exerciseLoading ? "Changing..." : "Change"}
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {libraryOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6">
          <div className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-5">
              <div>
                <h2 className="text-lg font-bold text-slate-950">Exercise Library</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Pick an exercise to add to a day or replace one exercise in that day.
                </p>
              </div>

              <button
                type="button"
                className="flex h-9 w-9 items-center justify-center rounded border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
                onClick={() => setLibraryOpen(false)}
                aria-label="Close exercise library"
              >
                <X size={16} />
              </button>
            </div>

            <div className="grid min-h-0 flex-1 gap-0 overflow-hidden lg:grid-cols-[320px,1fr]">
              <div className="space-y-4 overflow-auto border-b border-slate-100 p-5 lg:border-b-0 lg:border-r">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    className={`h-10 rounded border text-sm font-semibold transition ${
                      libraryAction === "add"
                        ? "border-brand-600 bg-brand-600 text-white"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                    onClick={() => setLibraryAction("add")}
                  >
                    Add
                  </button>
                  <button
                    type="button"
                    className={`h-10 rounded border text-sm font-semibold transition ${
                      libraryAction === "replace"
                        ? "border-brand-600 bg-brand-600 text-white"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                    onClick={() => setLibraryAction("replace")}
                  >
                    Replace
                  </button>
                </div>

                <label className="block">
                  <span className="mb-1 block text-sm font-semibold text-slate-700">Workout day</span>
                  <select
                    className="input"
                    value={libraryDayIndex}
                    onChange={(event) => {
                      setLibraryDayIndex(Number(event.target.value));
                      setLibraryExerciseIndex(0);
                    }}
                  >
                    {(workoutPlan?.days || []).map((day, index) => (
                      <option key={`${day.day}-${index}`} value={index}>
                        {formatDayLabel(day.day, "long")} - {day.title}
                      </option>
                    ))}
                  </select>
                </label>

                {libraryAction === "replace" && (
                  <label className="block">
                    <span className="mb-1 block text-sm font-semibold text-slate-700">Exercise to replace</span>
                    <select
                      className="input"
                      value={libraryExerciseIndex}
                      onChange={(event) => setLibraryExerciseIndex(Number(event.target.value))}
                    >
                      {(selectedLibraryDay?.exercises || []).map((exercise, index) => (
                        <option key={`${exercise.exercise_id}-${index}`} value={index}>
                          {exercise.title || `Exercise ${exercise.exercise_id}`}
                        </option>
                      ))}
                    </select>
                  </label>
                )}

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-sm font-semibold text-slate-900">
                    {libraryAction === "add" ? "Adding to" : "Replacing in"} {formatDayLabel(selectedLibraryDay?.day, "long")}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {libraryAction === "replace"
                      ? formatList(selectedLibraryExercise?.muscle_groups)
                      : `${selectedLibraryDay?.exercises?.length || 0} exercises currently`}
                  </p>
                </div>
              </div>

              <div className="flex min-h-0 flex-col p-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="text-brand-600" size={18} />
                    <h3 className="font-semibold text-slate-950">All exercises</h3>
                  </div>
                  <div className="relative sm:w-72">
                    <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={15} />
                    <input
                      className="input pl-9"
                      value={exerciseSearch}
                      onChange={(event) => setExerciseSearch(event.target.value)}
                      placeholder="Search"
                    />
                  </div>
                </div>

                <div className="mt-4 min-h-0 flex-1 overflow-auto rounded-2xl border border-slate-200">
                  {exerciseDatabaseLoading ? (
                    <div className="flex h-40 items-center justify-center text-sm text-slate-500">
                      Loading exercises...
                    </div>
                  ) : filteredExercises.length ? (
                    <div className="divide-y divide-slate-100">
                      {filteredExercises.map((exercise) => {
                        const sameMuscle = libraryAction === "replace" && sharesMuscle(exercise, selectedLibraryExercise);
                        const actionKey = libraryActionKey(libraryAction, libraryDayIndex, exercise.id);
                        const actionLoading = loading === actionKey;

                        return (
                          <div key={exercise.id} className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
                            <div className="flex min-w-0 items-start gap-3">
                              <ExerciseThumb exercise={exercise} size="sm" />
                              <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                  <p className="font-semibold text-slate-900">{exercise.title}</p>
                                  {sameMuscle && (
                                    <span className="inline-flex h-6 items-center gap-1 rounded-full bg-brand-50 px-2 text-xs font-semibold text-brand-700">
                                      <Check size={12} />
                                      Same muscle
                                    </span>
                                  )}
                                </div>
                                <p className="mt-1 text-xs text-slate-500">
                                  {formatList(exercise.muscle_groups)} - {exercise.equipment || "No equipment data"}
                                </p>
                              </div>
                            </div>
                            <button
                              type="button"
                              className="btn-secondary h-9 justify-center rounded-xl px-3"
                              onClick={() => handleLibrarySelect(exercise)}
                              disabled={isBusy}
                            >
                              {actionLoading ? (
                                <>
                                  <RefreshCw size={14} className="animate-spin" />
                                  Working...
                                </>
                              ) : libraryAction === "add" ? (
                                <>
                                  <Plus size={14} />
                                  Add
                                </>
                              ) : (
                                <>
                                  <RefreshCw size={14} />
                                  Replace
                                </>
                              )}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex h-40 items-center justify-center text-sm text-slate-500">
                      No exercises found.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
