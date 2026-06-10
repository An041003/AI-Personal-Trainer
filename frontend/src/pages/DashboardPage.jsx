import {
  Bell,
  Camera,
  Check,
  ChevronRight,
  CloudSun,
  Dumbbell,
  Flame,
  Leaf,
  MapPin,
  Mic,
  Salad,
  Scale,
  Trophy,
  UserRound,
  RefreshCw,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { me } from "../api/auth";
import { completeNutritionToday, getMonthlyCalories, getLatestNutritionPlan, replaceNutritionPlan } from "../api/nutrition";
import { getDashboardGreeting, getProfile } from "../api/profile";
import { completeWorkoutToday, getLatestWorkoutPlan, getWorkoutCompletionSummary } from "../api/workout";
import { getProfileCompleteness } from "../utils/profileCompleteness";

function readNumber(source, keys = []) {
  for (const key of keys) {
    const value = source?.[key];
    if (value !== null && value !== undefined && value !== "") {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}

function clamp(value, min = 0, max = 100) {
  return Math.min(Math.max(value, min), max);
}

function formatNumber(value, fallback = "-") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return fallback;
  return Math.round(Number(value)).toLocaleString("en-US");
}

function formatWeight(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(1);
}

const DAY_LABELS = {
  mon: "Mon",
  tue: "Tue",
  wed: "Wed",
  thu: "Thu",
  fri: "Fri",
  sat: "Sat",
  sun: "Sun",
};

const JS_DAY_KEYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
const DASHBOARD_GREETING_FALLBACK = "Hãy có một ngày ăn uống và tập luyện năng suất nhé.";

function normalizeDayKey(value) {
  const key = String(value || "").trim().toLowerCase().slice(0, 3);
  return DAY_LABELS[key] ? key : "";
}

function formatDayLabel(value) {
  const key = normalizeDayKey(value);
  if (key) return DAY_LABELS[key];
  const text = String(value || "Day").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Day";
}

function todayDayKey() {
  return JS_DAY_KEYS[new Date().getDay()];
}

function findTodayWorkout(days = []) {
  const currentDay = todayDayKey();
  return days.find((day) => normalizeDayKey(day?.day) === currentDay) || null;
}

function weatherSummary(profile) {
  const weather = profile?.weather_snapshot || {};
  const current = weather.current || {};
  const location = weather.location || {};
  const city = profile?.city || location.city || location.name;
  const country = profile?.country || location.country;
  const temp = readNumber(current, ["temp_c"]);
  return {
    place: [city, country].filter(Boolean).join(", "),
    temp,
    condition: current.condition_text || "",
    humidity: readNumber(current, ["humidity"]),
  };
}

function getMealCalories(meal) {
  const direct =
    readNumber(meal, ["kcal", "calories", "total_kcal", "meal_kcal"]) ??
    readNumber(meal?.totals, ["kcal", "calories", "total_kcal"]);
  if (direct !== null) return direct;

  return (meal?.recipes || []).reduce((sum, recipe) => {
    const recipeKcal =
      readNumber(recipe, ["kcal", "calories", "total_kcal"]) ??
      readNumber(recipe?.totals, ["kcal", "calories", "total_kcal"]);
    return sum + (recipeKcal || 0);
  }, 0);
}

function getMealTitle(meal) {
  return meal?.title || meal?.recipes?.[0]?.recipe_name || "Planned meal";
}

function normalizeMealTitle(value) {
  const text = String(value || "Meal").replace(/_/g, " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Meal";
}

function blankImageLabel(text) {
  return String(text || "?").trim().slice(0, 1).toUpperCase();
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function chartPointsFromSeries(series = []) {
  const entries = series.filter((item) => Number(item.kcal) > 0);
  if (!entries.length) return [];
  const max = Math.max(...entries.map((item) => Number(item.kcal)), 1);
  return entries.map((item, index) => {
    const spread = Math.max(entries.length - 1, 1);
    return {
      x: 18 + (index / spread) * 286,
      y: 150 - (Number(item.kcal) / max) * 116,
    };
  });
}

export default function DashboardPage() {
  const [profileBundle, setProfileBundle] = useState(null);
  const [user, setUser] = useState(null);
  const [workout, setWorkout] = useState(null);
  const [nutrition, setNutrition] = useState(null);
  const [completion, setCompletion] = useState(null);
  const [monthlyCalories, setMonthlyCalories] = useState(null);
  const [dashboardGreeting, setDashboardGreeting] = useState("");
  const [completeLoading, setCompleteLoading] = useState(false);
  const [nutritionCompleteLoading, setNutritionCompleteLoading] = useState(false);
  const [mealReplaceLoading, setMealReplaceLoading] = useState(false);
  const [mealReplaceModal, setMealReplaceModal] = useState(null);
  const [mealReplaceText, setMealReplaceText] = useState("");
  const [mealReplaceImage, setMealReplaceImage] = useState(null);
  const [speechListening, setSpeechListening] = useState(false);
  const [completeError, setCompleteError] = useState("");

  useEffect(() => {
    let active = true;

    Promise.allSettled([
      getProfile(),
      me(),
      getLatestWorkoutPlan(),
      getLatestNutritionPlan(),
      getWorkoutCompletionSummary(),
      getMonthlyCalories(),
      getDashboardGreeting(),
    ]).then((results) => {
      if (!active) return;
      if (results[0].status === "fulfilled") setProfileBundle(results[0].value);
      if (results[1].status === "fulfilled") setUser(results[1].value);
      if (results[2].status === "fulfilled") setWorkout(results[2].value);
      if (results[3].status === "fulfilled") setNutrition(results[3].value);
      if (results[4].status === "fulfilled") setCompletion(results[4].value);
      if (results[5].status === "fulfilled") setMonthlyCalories(results[5].value);
      if (results[6].status === "fulfilled") setDashboardGreeting(results[6].value?.message || "");
      if (results[6].status === "rejected") setDashboardGreeting(DASHBOARD_GREETING_FALLBACK);
    });

    return () => {
      active = false;
    };
  }, []);

  async function handleCompleteToday() {
    setCompleteLoading(true);
    setCompleteError("");
    try {
      const updated = await completeWorkoutToday();
      setCompletion(updated);
    } catch (err) {
      setCompleteError(err.message || "Could not mark workout complete.");
    } finally {
      setCompleteLoading(false);
    }
  }

  async function handleCompleteMealsToday() {
    setNutritionCompleteLoading(true);
    setCompleteError("");
    try {
      const updated = await completeNutritionToday();
      setCompletion(updated);
    } catch (err) {
      setCompleteError(err.message || "Could not mark today's meals complete.");
    } finally {
      setNutritionCompleteLoading(false);
    }
  }

  function openMealReplaceModal(meal, mealIndex) {
    setMealReplaceModal({ meal, mealIndex });
    setMealReplaceText("");
    setMealReplaceImage(null);
  }

  async function handleMealReplaceSubmit() {
    if (!mealReplaceModal || !nutrition?.meal_plan) return;
    setMealReplaceLoading(true);
    setCompleteError("");
    try {
      if (mealReplaceImage && mealReplaceImage.size > 2 * 1024 * 1024) {
        throw new Error("Please attach an image smaller than 2 MB.");
      }
      const imageDataUrl = mealReplaceImage ? await fileToDataUrl(mealReplaceImage) : "";
      const meal = mealReplaceModal.meal || {};
      const updatedPlan = await replaceNutritionPlan({
        source_request_id: nutrition.request_id,
        scope: "meal",
        target: {
          day_index: 0,
          meal_index: mealReplaceModal.mealIndex,
          meal_slot: meal.slot,
        },
        derived_targets: nutrition.derived_targets || {},
        constraint_report: nutrition.constraint_report || {},
        preferences: profileBundle?.preferences || {},
        replacement_request: {
          scope: "meal",
          reason_type: "ate_different",
          reason_detail: mealReplaceText || "User ate a different meal.",
          free_text_reason: mealReplaceText,
          ignore_short_term_memory: true,
          persist_short_term_memory: false,
          skip_old_plan_as_avoid: true,
          eaten_different: {
            description: mealReplaceText,
            image_data_url: imageDataUrl,
            image_filename: mealReplaceImage?.name || "",
          },
        },
        options: {
          optimizer_iters: 200,
          max_llm_retries: 1,
        },
      });
      setNutrition(updatedPlan);
      setMealReplaceModal(null);
      setMealReplaceText("");
      setMealReplaceImage(null);
    } catch (err) {
      setCompleteError(err.message || "Could not update the meal you ate.");
    } finally {
      setMealReplaceLoading(false);
    }
  }

  function handleSpeakMealNote() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setCompleteError("Speech input is not supported in this browser.");
      return;
    }
    setCompleteError("");
    const recognition = new SpeechRecognition();
    recognition.lang = "vi-VN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setSpeechListening(true);
    recognition.onend = () => setSpeechListening(false);
    recognition.onerror = () => {
      setSpeechListening(false);
      setCompleteError("Could not capture your voice note.");
    };
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript || "";
      if (transcript) {
        setMealReplaceText((current) => [current, transcript].filter(Boolean).join(" "));
      }
    };
    recognition.start();
  }

  const profile = profileBundle?.profile || {};
  const completeness = useMemo(() => getProfileCompleteness(profile), [profile]);
  const displayName = profile.full_name || user?.username || "there";
  const weight = readNumber(profile, ["weight_kg", "weight"]);
  const weather = weatherSummary(profile);

  const workoutPlan = workout?.plan || null;
  const workoutDays = workoutPlan?.days || [];
  const currentDayKey = todayDayKey();
  const todayWorkout = findTodayWorkout(workoutDays);
  const hasWorkoutPlan = workoutDays.length > 0;
  const workoutExercises = (todayWorkout?.exercises || []).slice(0, 5);

  const meals = nutrition?.meal_plan?.days?.[0]?.meals || [];
  const totals = nutrition?.totals || {};
  const derivedTargets = nutrition?.derived_targets || {};
  const todayCalories = readNumber(totals, ["kcal", "calories", "total_kcal"]);
  const dailyTarget =
    readNumber(derivedTargets, ["calorie_target_kcal", "calories", "calorie_target"]) ||
    monthlyCalories?.daily_target_kcal ||
    null;
  const todayCaloriePercent = todayCalories && dailyTarget ? clamp((todayCalories / dailyTarget) * 100) : 0;
  const monthTotal = monthlyCalories?.total_kcal ?? null;
  const monthTarget = monthlyCalories?.month_target_kcal ?? null;
  const monthPercent = monthTotal && monthTarget ? clamp((monthTotal / monthTarget) * 100) : 0;
  const chartPoints = chartPointsFromSeries(monthlyCalories?.series || []);
  const polyline = chartPoints.map((point) => `${point.x},${point.y}`).join(" ");
  const areaPath = chartPoints.length
    ? `M ${chartPoints[0].x},160 L ${polyline} L ${chartPoints[chartPoints.length - 1].x},160 Z`
    : "";

  const statCards = [
    !completeness.isComplete
      ? {
          to: "/profile",
          icon: UserRound,
          tone: "green",
          title: "Profile",
          subtitle: "Completeness",
          value: `${completeness.completionPercent}%`,
          progress: completeness.completionPercent,
          foot: "Complete required fields to unlock all AI flows.",
        }
      : null,
    {
      to: "/profile",
      icon: weather.temp !== null ? CloudSun : MapPin,
      tone: "green",
      title: "Location",
      subtitle: weather.place || "Weather context",
      value: weather.temp !== null ? `${Math.round(weather.temp)}°C` : "-",
      progress: null,
      foot: weather.condition
        ? `${weather.condition}${weather.humidity !== null ? `, ${weather.humidity}% humidity` : ""}`
        : "Add city or use current location in Profile.",
    },
    {
      to: "/workout",
      icon: Trophy,
      tone: "green",
      title: "Streak",
      subtitle: "Consecutive days",
      value: `${completion?.streak_days || 0}`,
      progress: null,
      foot: completion?.today_completed
        ? "Daily streak secured."
        : completion?.today_requires_workout
        ? "Complete today's meals and workout to keep the streak alive."
        : "Complete today's meals to keep the streak alive.",
    },
    {
      to: "/nutrition",
      icon: Flame,
      tone: "orange",
      title: "Calories",
      subtitle: "Today Target",
      value: todayCalories && dailyTarget ? `${Math.round(todayCaloriePercent)}%` : "-",
      progress: todayCaloriePercent,
      foot: todayCalories && dailyTarget ? `${formatNumber(todayCalories)} / ${formatNumber(dailyTarget)} kcal` : "Generate today's menu first.",
    },
    {
      to: "/profile",
      icon: Scale,
      tone: "green",
      title: "Current Weight",
      subtitle: "From profile",
      value: weight ? `${formatWeight(weight)} kg` : "-",
      progress: null,
      foot: weight ? "Latest saved profile weight." : "Add weight in profile.",
    },
  ].filter(Boolean);

  return (
    <div className="space-y-7">
      <header className="flex items-center justify-between gap-4 border-b border-black/10 pb-6">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Dashboard</h1>
        <button className="relative grid h-11 w-11 place-items-center rounded-2xl border border-black/10 bg-white/80 text-slate-700 shadow-sm transition hover:bg-white" aria-label="Notifications">
          <Bell size={20} />
        </button>
      </header>

      <section>
        <h2 className="text-2xl font-semibold tracking-tight text-slate-950">Hi {displayName}</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          {dashboardGreeting || "Đang tạo gợi ý hôm nay dựa trên thời tiết và kế hoạch của bạn..."}
        </p>
      </section>

      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {statCards.map((card) => (
          <StatCard key={card.title} {...card} />
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_1.03fr_1.08fr]">
        <Panel className="p-5">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold text-slate-950">Today's Workout</h2>
            <Link to="/workout" className="text-sm font-semibold text-brand-800 hover:text-brand-900">
              View full plan
            </Link>
          </div>
          {todayWorkout ? (
            <span className="mt-4 inline-flex rounded-xl bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-800">
              {formatDayLabel(todayWorkout.day)} - {todayWorkout.title || "Training"}
            </span>
          ) : null}
          {hasWorkoutPlan && !todayWorkout ? (
            <RestDayCard dayLabel={formatDayLabel(currentDayKey)} />
          ) : (
            <div className="mt-4 space-y-3">
              {workoutExercises.length ? (
                workoutExercises.map((exercise, index) => (
                  <WorkoutRow key={`${exercise.exercise_id || exercise.title}-${index}`} exercise={exercise} />
                ))
              ) : (
                <EmptyState title="No workout plan yet" text="Generate a workout plan to show today's exercises." to="/workout" action="Build workout" />
              )}
            </div>
          )}
          {workoutExercises.length ? (
            <button
              type="button"
              className="mt-5 flex h-12 w-full items-center justify-center gap-3 rounded-2xl bg-brand-800 px-5 text-sm font-semibold text-white shadow-lg shadow-brand-900/15 transition hover:bg-brand-900 disabled:cursor-not-allowed disabled:opacity-65"
              onClick={handleCompleteToday}
              disabled={completeLoading || completion?.today_workout_completed}
            >
              <Check size={17} />
              {completion?.today_workout_completed ? "Workout completed" : completeLoading ? "Confirming..." : "Confirm workout completed"}
            </button>
          ) : null}
          {completeError ? <p className="mt-3 text-sm font-medium text-red-600">{completeError}</p> : null}
        </Panel>

        <Panel className="p-5">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold text-slate-950">Calories This Month</h2>
            <Link to="/nutrition" className="text-sm font-semibold text-brand-800 hover:text-brand-900">
              Details
            </Link>
          </div>
          {monthTotal !== null && monthlyCalories?.days_with_data ? (
            <>
              <div className="mt-7 flex items-end gap-2">
                <span className="text-3xl font-semibold tracking-tight text-brand-800">{formatNumber(monthTotal)}</span>
                {monthTarget ? <span className="pb-1 text-lg font-medium text-slate-900">/ {formatNumber(monthTarget)} kcal</span> : null}
              </div>
              <p className="mt-2 text-sm font-semibold text-brand-700">
                {monthTarget ? `${Math.round(monthPercent)}% of monthly target` : `${monthlyCalories.days_with_data} days with menu data`}
              </p>
              <div className="mt-5">
                <svg viewBox="0 0 320 180" className="h-48 w-full overflow-visible" role="img" aria-label="Calories progress chart">
                  <line x1="18" y1="34" x2="306" y2="34" stroke="#d8ded5" strokeDasharray="4 6" />
                  <line x1="18" y1="92" x2="306" y2="92" stroke="#e4e9e0" strokeDasharray="4 6" />
                  <line x1="18" y1="150" x2="306" y2="150" stroke="#e4e9e0" />
                  {areaPath ? <path d={areaPath} fill="url(#calorieGradient)" /> : null}
                  {polyline ? <polyline points={polyline} fill="none" stroke="#166534" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" /> : null}
                  <defs>
                    <linearGradient id="calorieGradient" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#3f8f49" stopOpacity="0.28" />
                      <stop offset="100%" stopColor="#3f8f49" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  <text x="0" y="38" className="fill-slate-500 text-[12px]">max</text>
                  <text x="0" y="96" className="fill-slate-500 text-[12px]">mid</text>
                  <text x="0" y="154" className="fill-slate-500 text-[12px]">0</text>
                </svg>
              </div>
              <div className="mt-4 flex items-center gap-3 rounded-2xl bg-brand-50/80 px-4 py-3 text-sm font-medium text-brand-900">
                <Leaf size={17} />
                This chart uses saved nutrition plan history.
              </div>
            </>
          ) : (
            <EmptyState title="No monthly calorie data" text="Generate nutrition plans to build the monthly chart." to="/nutrition" action="Generate menu" />
          )}
        </Panel>

        <Panel className="p-5">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold text-slate-950">Today's Meals</h2>
            <Link to="/nutrition" className="text-sm font-semibold text-brand-800 hover:text-brand-900">
              View full menu
            </Link>
          </div>
          <div className="mt-5 space-y-5">
            {meals.length ? (
              meals.map((meal, index) => (
                <MealRow
                  key={`${meal.slot || "meal"}-${index}`}
                  meal={meal}
                  onAteDifferent={() => openMealReplaceModal(meal, index)}
                />
              ))
            ) : (
              <EmptyState title="No menu for today" text="Generate today's nutrition plan to show meals here." to="/nutrition" action="Generate menu" />
            )}
          </div>
          {meals.length ? (
            <>
              <div className="mt-6 rounded-2xl bg-slate-50 p-4">
                <div className="flex items-center justify-between gap-4 text-sm">
                  <span className="font-semibold text-slate-900">Total</span>
                  <span className="font-semibold text-slate-900">
                    <span className="text-brand-800">{formatNumber(todayCalories)}</span>
                    {dailyTarget ? ` / ${formatNumber(dailyTarget)} kcal` : " kcal"}
                  </span>
                </div>
                <ProgressBar value={todayCaloriePercent} className="mt-4" />
              </div>
              <button
                type="button"
                className="mt-4 flex h-12 w-full items-center justify-center gap-3 rounded-2xl bg-brand-800 px-5 text-sm font-semibold text-white shadow-lg shadow-brand-900/15 transition hover:bg-brand-900 disabled:cursor-not-allowed disabled:opacity-65"
                onClick={handleCompleteMealsToday}
                disabled={nutritionCompleteLoading || completion?.today_nutrition_completed}
              >
                <Check size={17} />
                {completion?.today_nutrition_completed ? "Meals completed" : nutritionCompleteLoading ? "Confirming..." : "Complete today's meals"}
              </button>
            </>
          ) : null}
        </Panel>
      </section>

      {mealReplaceModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6">
          <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-950">I ate something else</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Describe what you ate, or attach a photo so the menu can be recalculated.
                </p>
              </div>
              <button
                type="button"
                className="flex h-9 w-9 items-center justify-center rounded border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
                onClick={() => setMealReplaceModal(null)}
                aria-label="Close eaten meal modal"
              >
                <X size={16} />
              </button>
            </div>

            <div className="mt-5 space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-sm font-semibold text-slate-900">
                  {normalizeMealTitle(mealReplaceModal.meal?.slot)} - {getMealTitle(mealReplaceModal.meal)}
                </p>
                <p className="mt-1 text-xs text-slate-500">This replaces only the selected meal.</p>
              </div>

              <label className="block">
                <span className="mb-1 block text-sm font-semibold text-slate-700">What did you eat?</span>
                <textarea
                  className="input min-h-28 py-3"
                  value={mealReplaceText}
                  onChange={(event) => setMealReplaceText(event.target.value)}
                  placeholder="Example: I ate chicken pho with extra beef and one iced tea."
                />
              </label>

              <button
                type="button"
                className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-600 transition hover:border-brand-200 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
                onClick={handleSpeakMealNote}
                disabled={speechListening}
              >
                <Mic size={16} />
                {speechListening ? "Listening..." : "Speak note"}
              </button>

              <label className="flex cursor-pointer items-center justify-between gap-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600 transition hover:border-brand-200 hover:bg-brand-50/50">
                <span className="flex items-center gap-3">
                  <Camera size={18} className="text-brand-700" />
                  {mealReplaceImage ? mealReplaceImage.name : "Attach meal photo"}
                </span>
                <input
                  type="file"
                  accept="image/*"
                  className="sr-only"
                  onChange={(event) => setMealReplaceImage(event.target.files?.[0] || null)}
                />
              </label>
            </div>

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                className="btn-secondary justify-center rounded-xl"
                onClick={() => setMealReplaceModal(null)}
                disabled={mealReplaceLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary justify-center rounded-xl"
                onClick={handleMealReplaceSubmit}
                disabled={mealReplaceLoading || (!mealReplaceText.trim() && !mealReplaceImage)}
              >
                {mealReplaceLoading ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    Updating...
                  </>
                ) : (
                  <>
                    <RefreshCw size={16} />
                    Update meal
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <p className="flex items-center justify-center gap-2 pb-2 text-sm text-slate-600">
        <Leaf size={16} className="text-slate-500" />
        Tip: Consistency today, results tomorrow.
      </p>
    </div>
  );
}

function Panel({ children, className = "" }) {
  return (
    <section className={`rounded-[1.5rem] border border-black/10 bg-white/85 shadow-[0_18px_60px_rgba(35,48,30,0.08)] backdrop-blur ${className}`}>
      {children}
    </section>
  );
}

function StatCard({ to, icon: Icon, tone, title, subtitle, value, progress, foot }) {
  const toneMap = {
    green: "bg-brand-100 text-brand-800",
    blue: "bg-blue-100 text-blue-700",
    orange: "bg-orange-100 text-orange-600",
  };

  return (
    <Link to={to} className="group rounded-[1.5rem] border border-black/10 bg-white/85 p-5 shadow-[0_18px_60px_rgba(35,48,30,0.08)] backdrop-blur transition hover:-translate-y-1 hover:shadow-[0_24px_70px_rgba(35,48,30,0.12)]">
      <div className="flex items-start justify-between gap-4">
        <div className={`grid h-14 w-14 place-items-center rounded-full ${toneMap[tone] || toneMap.green}`}>
          <Icon size={27} />
        </div>
        <ChevronRight className="mt-3 text-slate-700 transition group-hover:translate-x-1" size={20} />
      </div>
      <div className="mt-4">
        <h3 className="font-semibold text-slate-950">{title}</h3>
        <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
      </div>
      <p className={`mt-5 text-3xl font-semibold tracking-tight ${tone === "orange" ? "text-orange-500" : tone === "blue" ? "text-blue-800" : "text-brand-800"}`}>
        {value}
      </p>
      {progress !== null && progress !== undefined ? <ProgressBar value={progress} accent={tone} className="mt-5" /> : null}
      <p className="mt-4 text-sm leading-6 text-slate-600">{foot}</p>
    </Link>
  );
}

function ProgressBar({ value, accent = "green", className = "" }) {
  const fill = accent === "orange" ? "bg-orange-400" : accent === "blue" ? "bg-blue-700" : "bg-brand-700";
  return (
    <div className={`h-2 overflow-hidden rounded-full bg-slate-100 ${className}`}>
      <div className={`h-full rounded-full ${fill}`} style={{ width: `${clamp(value)}%` }} />
    </div>
  );
}

function BlankImage({ label }) {
  return (
    <div className="grid h-14 w-14 shrink-0 place-items-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-sm font-semibold text-slate-400">
      {blankImageLabel(label)}
    </div>
  );
}

function ExerciseImage({ src, label }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return <BlankImage label={label} />;
  }
  return (
    <img
      src={src}
      alt=""
      className="h-14 w-14 shrink-0 rounded-xl border border-slate-200 bg-slate-50 object-contain"
      onError={() => setFailed(true)}
    />
  );
}

function WorkoutRow({ exercise }) {
  return (
    <div className="flex items-center gap-4">
      <ExerciseImage src={exercise.image_url} label={exercise.title || exercise.exercise_id} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-slate-950">{exercise.title || `Exercise ${exercise.exercise_id || ""}`}</p>
        <p className="mt-1 text-sm text-slate-600">
          {exercise.sets || 3} sets x {exercise.reps || "8-12"} reps
        </p>
      </div>
    </div>
  );
}

function RestDayCard({ dayLabel }) {
  return (
    <div className="relative mt-4 min-h-[260px] overflow-hidden rounded-[1.25rem] border border-brand-900/10 bg-slate-900">
      <img
        src="https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=1200&q=80"
        alt=""
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/85 via-slate-950/35 to-slate-950/5" />
      <div className="relative flex min-h-[260px] flex-col justify-end p-5 text-white">
        <span className="mb-3 inline-flex w-fit rounded-xl bg-white/15 px-3 py-1 text-xs font-semibold backdrop-blur">
          {dayLabel}
        </span>
        <h3 className="max-w-sm text-2xl font-semibold leading-tight">Today is a rest day</h3>
        <p className="mt-2 max-w-sm text-sm leading-6 text-white/85">
          Rest and sleep well so your muscles can recover.
        </p>
      </div>
    </div>
  );
}

function MealRow({ meal, onAteDifferent }) {
  const kcal = getMealCalories(meal);
  return (
    <div className="grid grid-cols-[56px_1fr_auto] items-center gap-3">
      <BlankImage label={getMealTitle(meal)} />
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-700">{normalizeMealTitle(meal.slot)}</p>
        <p className="mt-1 line-clamp-2 text-sm leading-5 text-slate-950">{getMealTitle(meal)}</p>
      </div>
      <div className="flex flex-col items-end gap-2">
        <p className="whitespace-nowrap text-base font-semibold text-brand-800">{formatNumber(kcal)} kcal</p>
        <button
          type="button"
          className="inline-flex h-7 items-center rounded border border-slate-200 bg-white px-2 text-[11px] font-semibold text-slate-600 transition hover:border-brand-200 hover:text-brand-700"
          onClick={onAteDifferent}
        >
          Ate different
        </button>
      </div>
    </div>
  );
}

function EmptyState({ title, text, to, action }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center">
      <p className="font-semibold text-slate-900">{title}</p>
      <p className="mx-auto mt-2 max-w-xs text-sm leading-6 text-slate-600">{text}</p>
      <Link to={to} className="mt-4 inline-flex h-10 items-center justify-center gap-2 rounded-2xl bg-white px-4 text-sm font-semibold text-brand-800 ring-1 ring-brand-100 transition hover:bg-brand-50">
        <Salad size={15} />
        {action}
      </Link>
    </div>
  );
}
