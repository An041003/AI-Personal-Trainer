import {
  Coffee,
  Droplet,
  Flame,
  Leaf,
  Moon,
  Sparkles,
  Sun,
  Utensils,
  Wand2,
  Wheat,
  Dumbbell,
  RefreshCw,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getProfile } from "../api/profile";
import {
  analyzeMetrics,
  generateNutritionPlan,
  getLatestNutritionPlan,
  previewRulebase,
  replaceNutritionPlan,
} from "../api/nutrition";
import { ErrorBanner } from "../components/FormControls";
import { getProfileCompleteness } from "../utils/profileCompleteness";

function toNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatNumber(value, digits = 1) {
  const n = toNumber(value);
  if (n === null) return "-";

  return Number.isInteger(n) ? String(n) : n.toFixed(digits);
}

function readNumber(source, keys) {
  if (!source) return null;

  for (const key of keys) {
    const value = source?.[key];
    const n = toNumber(value);
    if (n !== null) return n;
  }

  return null;
}

function getRecipeCalories(recipe) {
  const direct =
    readNumber(recipe, [
      "kcal",
      "calories",
      "total_kcal",
      "energy_kcal",
      "calorie",
    ]) ??
    readNumber(recipe?.totals, ["kcal", "calories", "total_kcal"]) ??
    readNumber(recipe?.nutrition, ["kcal", "calories", "total_kcal"]);

  if (direct !== null) return direct;

  return (recipe?.ingredients || []).reduce((sum, ingredient) => {
    return sum + (readNumber(ingredient?.nutrients, ["kcal", "calories", "total_kcal"]) || 0);
  }, 0);
}

function getMealTotalKcal(meal) {
  const direct =
    readNumber(meal, ["kcal", "calories", "total_kcal", "meal_kcal"]) ??
    readNumber(meal?.totals, ["kcal", "calories", "total_kcal"]);

  if (direct !== null) return direct;

  return (meal?.recipes || []).reduce((sum, recipe) => {
    return sum + (getRecipeCalories(recipe) || 0);
  }, 0);
}

function formatIngredientName(value) {
  const name = String(value || "Ingredient")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  return name.replace(/\b\w/g, (char) => char.toUpperCase());
}

function getIngredientRows(recipe) {
  const ingredients = recipe?.ingredients || [];

  if (!ingredients.length) {
    const fallback = recipe?.description || recipe?.note;
    return fallback ? [fallback] : [];
  }

  return ingredients.map((ingredient) => {
      const name = formatIngredientName(ingredient.canonical_name || ingredient.ingredient_name || ingredient.name);
      const grams = toNumber(ingredient.grams);

      return grams ? `${name} ${formatNumber(grams, 0)}g` : name;
    });
}

function getRecipeImageUrl(recipe) {
  return recipe?.image_url || recipe?.image?.url || "";
}

function getRecipeImageMeta(recipe) {
  return recipe?.image || {};
}

function getRecipeInstructions(recipe) {
  return (recipe?.instructions || [])
    .map((item) => String(item || "").trim())
    .filter(Boolean);
}

function getIngredientDetailRows(recipe) {
  return (recipe?.ingredients || []).map((ingredient) => {
    const nutrients = ingredient?.nutrients || {};
    return {
      name: formatIngredientName(ingredient.canonical_name || ingredient.ingredient_name || ingredient.name),
      grams: toNumber(ingredient.grams),
      kcal: readNumber(nutrients, ["kcal", "calories", "total_kcal"]),
      protein: readNumber(nutrients, ["protein_g", "protein"]),
      carbs: readNumber(nutrients, ["carbs_g", "carbs", "carbohydrate_g"]),
      fat: readNumber(nutrients, ["fat_g", "fat"]),
    };
  });
}

function uniqueStrings(values) {
  const seen = new Set();
  const result = [];

  (values || []).forEach((value) => {
    const text = String(value || "").trim();
    const key = text.toLowerCase();

    if (text && !seen.has(key)) {
      seen.add(key);
      result.push(text);
    }
  });

  return result;
}

function getPlanRecipeNames(mealPlan) {
  return uniqueStrings(
    (mealPlan?.days || []).flatMap((day) =>
      (day?.meals || []).flatMap((meal) =>
        (meal?.recipes || []).map((recipe) => recipe?.recipe_name)
      )
    )
  );
}

function getPlanMealTitles(mealPlan) {
  return uniqueStrings(
    (mealPlan?.days || []).flatMap((day) =>
      (day?.meals || []).flatMap((meal) => [meal?.title, meal?.slot])
    )
  );
}

function getPlanIngredientOptions(mealPlan) {
  const seen = new Set();
  const options = [];

  (mealPlan?.days || []).forEach((day) => {
    (day?.meals || []).forEach((meal) => {
      (meal?.recipes || []).forEach((recipe) => {
        (recipe?.ingredients || []).forEach((ingredient) => {
          const value =
            ingredient?.canonical_name ||
            ingredient?.name ||
            ingredient?.ingredient_name;
          const key = String(value || "").trim().toLowerCase();

          if (key && !seen.has(key)) {
            seen.add(key);
            options.push({
              value,
              label: formatIngredientName(value),
            });
          }
        });
      });
    });
  });

  return options;
}

function getRecipeIngredientOptions(recipe) {
  const seen = new Set();
  const options = [];

  (recipe?.ingredients || []).forEach((ingredient) => {
    const value =
      ingredient?.canonical_name ||
      ingredient?.name ||
      ingredient?.ingredient_name;
    const key = String(value || "").trim().toLowerCase();

    if (key && !seen.has(key)) {
      seen.add(key);
      options.push({
        value,
        atomId: ingredient?.atom_id,
        label: formatIngredientName(value),
      });
    }
  });

  return options;
}

function replacementKey(scope, target = {}) {
  if (scope === "plan") return "replace-plan";

  return [
    "replace",
    scope,
    target.day_index ?? 0,
    target.meal_index ?? "",
    target.recipe_index ?? "",
  ]
    .filter((part) => part !== "")
    .join("-");
}

const RECIPE_REPLACEMENT_REASONS = [
  { value: "dislike_recipe", label: "I do not like this dish" },
  { value: "dislike_ingredient", label: "I do not like an ingredient" },
  { value: "repeated_or_bored", label: "Repeated or want a new flavor" },
  { value: "too_hard_to_cook", label: "Too hard to cook" },
  { value: "cost_or_availability", label: "Expensive or hard to buy" },
  { value: "health_mismatch", label: "Does not fit my health" },
  { value: "lighter", label: "I want something lighter" },
  { value: "more_filling", label: "I want something more filling" },
  { value: "other", label: "Other" },
];

function mealIcon(slot) {
  const s = String(slot || "").toLowerCase();

  if (s.includes("breakfast")) return <Sun size={18} />;
  if (s.includes("lunch")) return <Sun size={18} />;
  if (s.includes("dinner")) return <Moon size={18} />;
  if (s.includes("snack")) return <Coffee size={18} />;

  return <Utensils size={18} />;
}

function normalizeMealTitle(slot) {
  const s = String(slot || "").trim();

  if (!s) return "Meal";

  return s.charAt(0).toUpperCase() + s.slice(1);
}

function ProgressCard({ icon, label, value, target, unit, accent = "green" }) {
  const current = toNumber(value);
  const dailyTarget = toNumber(target);

  const percent =
    current !== null && dailyTarget && dailyTarget > 0
      ? (current / dailyTarget) * 100
      : 0;

  const isOver = percent > 100;
  const width = Math.min(percent, 100);

  const barColor =
    accent === "orange" || isOver ? "bg-orange-500" : "bg-emerald-600";

  const iconColor =
    accent === "orange" || isOver
      ? "text-orange-500"
      : accent === "purple"
      ? "text-violet-600"
      : accent === "teal"
      ? "text-teal-600"
      : "text-emerald-600";

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div
            className={`flex h-9 w-9 items-center justify-center rounded-xl bg-slate-50 ${iconColor}`}
          >
            {icon}
          </div>

          <div>
            <p className="text-sm font-semibold text-slate-800">{label}</p>
            <div className="flex items-end gap-1 mt-1">
              <span className="text-xl font-bold text-slate-950">
                {formatNumber(current)}
              </span>
              <span className="pb-0.5 text-sm text-slate-500">{unit}</span>
            </div>
          </div>
        </div>

        <div className="text-sm text-right text-slate-500">
          <span>/ {formatNumber(dailyTarget)} {unit}</span>
        </div>
      </div>

      <div className="mt-4">
        <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full ${barColor}`}
            style={{ width: `${width}%` }}
          />
        </div>

        <div className="flex justify-end mt-2 text-xs font-semibold text-slate-700">
          {dailyTarget ? `${formatNumber(percent, 1)}%` : "-"}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, unit, accent = "green" }) {
  const iconColor =
    accent === "orange"
      ? "text-orange-500"
      : accent === "purple"
      ? "text-violet-600"
      : "text-emerald-600";

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-center gap-3">
        <div className={`flex h-9 w-9 items-center justify-center rounded-xl bg-slate-50 ${iconColor}`}>
          {icon}
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-800">{label}</p>
          <div className="mt-1 flex items-end gap-1">
            <span className="text-xl font-bold text-slate-950">{formatNumber(value)}</span>
            <span className="pb-0.5 text-sm text-slate-500">{unit}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function RecipeThumb({ recipe, className = "" }) {
  const [failed, setFailed] = useState(false);
  const imageUrl = getRecipeImageUrl(recipe);
  const classes = `h-16 w-20 shrink-0 rounded-xl border border-slate-200 bg-slate-50 object-cover ${className}`;

  if (!imageUrl || failed) {
    return <div className={`${classes} border-dashed`} aria-hidden="true" />;
  }

  return (
    <img
      src={imageUrl}
      alt=""
      className={classes}
      onError={() => setFailed(true)}
    />
  );
}

function RecipeDetailModal({ detail, onClose }) {
  if (!detail) return null;

  const { meal, recipe } = detail;
  const recipeCalories = getRecipeCalories(recipe);
  const imageUrl = getRecipeImageUrl(recipe);
  const imageMeta = getRecipeImageMeta(recipe);
  const ingredients = getIngredientDetailRows(recipe);
  const instructions = getRecipeInstructions(recipe);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6">
      <div className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-5">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
              {normalizeMealTitle(meal?.slot)}
            </p>
            <h2 className="mt-1 text-xl font-bold text-slate-950">
              {recipe?.recipe_name || "Dish detail"}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {formatNumber(recipeCalories, 0)} kcal
            </p>
          </div>

          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
            onClick={onClose}
            aria-label="Close dish detail"
          >
            <X size={16} />
          </button>
        </div>

        <div className="overflow-auto p-5">
          {imageUrl ? (
            <div>
              <img
                src={imageUrl}
                alt=""
                className="h-56 w-full rounded-2xl border border-slate-200 bg-slate-50 object-cover"
              />
              {imageMeta?.source_url ? (
                <a
                  href={imageMeta.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block text-xs font-semibold text-slate-500 transition hover:text-emerald-700"
                >
                  {imageMeta.source || "Image source"}
                  {imageMeta.license ? ` · ${imageMeta.license}` : ""}
                </a>
              ) : null}
            </div>
          ) : (
            <div className="h-40 rounded-2xl border border-dashed border-slate-300 bg-slate-50" aria-hidden="true" />
          )}

          <div className="mt-6">
            <h3 className="text-sm font-bold text-slate-950">Ingredients</h3>
            <div className="mt-3 overflow-x-auto rounded-2xl border border-slate-200">
              <table className="min-w-full divide-y divide-slate-100 text-sm">
                <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Ingredient</th>
                    <th className="px-4 py-3 text-right">Gram</th>
                    <th className="px-4 py-3 text-right">Kcal</th>
                    <th className="px-4 py-3 text-right">Protein</th>
                    <th className="px-4 py-3 text-right">Carbs</th>
                    <th className="px-4 py-3 text-right">Fat</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {ingredients.length ? (
                    ingredients.map((ingredient, index) => (
                      <tr key={`${ingredient.name}-${index}`}>
                        <td className="px-4 py-3 font-semibold text-slate-800">{ingredient.name}</td>
                        <td className="px-4 py-3 text-right text-slate-600">{formatNumber(ingredient.grams, 0)}g</td>
                        <td className="px-4 py-3 text-right text-slate-600">{formatNumber(ingredient.kcal, 0)}</td>
                        <td className="px-4 py-3 text-right text-slate-600">{formatNumber(ingredient.protein, 1)}g</td>
                        <td className="px-4 py-3 text-right text-slate-600">{formatNumber(ingredient.carbs, 1)}g</td>
                        <td className="px-4 py-3 text-right text-slate-600">{formatNumber(ingredient.fat, 1)}g</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="px-4 py-6 text-center text-slate-500" colSpan={6}>
                        No ingredient details found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-6">
            <h3 className="text-sm font-bold text-slate-950">How to cook</h3>
            {instructions.length ? (
              <ol className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
                {instructions.map((instruction, index) => (
                  <li key={`${instruction}-${index}`} className="rounded-2xl bg-slate-50 px-4 py-3">
                    {index + 1}. {instruction}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-3 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-500">
                No cooking instructions found.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NutritionPage() {
  const [bundle, setBundle] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [rulebase, setRulebase] = useState(null);
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState("");
  const [replacementModal, setReplacementModal] = useState(null);
  const [replacementReason, setReplacementReason] = useState("simple_dislike");
  const [replacementDetail, setReplacementDetail] = useState("");
  const [replacementFreeText, setReplacementFreeText] = useState("");
  const [selectedRecipeDetail, setSelectedRecipeDetail] = useState(null);
  const [selectedAvoidIngredients, setSelectedAvoidIngredients] = useState([]);
  const [sessionMemory, setSessionMemory] = useState({
    avoid_recipe_names: [],
    avoid_ingredient_names: [],
    avoid_atom_ids: [],
    last_replace_reason: "",
  });

  useEffect(() => {
    getProfile()
      .then((data) => {
        setBundle(data);
        setMetrics(data.metrics || null);
      })
      .catch((err) => setError(err.message));

    getLatestNutritionPlan()
      .then((data) => setPlan(data || null))
      .catch((err) => setError(err.message));
  }, []);

  const profile = bundle?.profile || {};
  const preferences = bundle?.preferences || {};

  const profileCompleteness = useMemo(
    () => (bundle ? getProfileCompleteness(profile) : null),
    [bundle, profile]
  );

  const profileReady = profileCompleteness?.isComplete === true;

  const goalPayload = useMemo(
    () => ({
      metrics,
      profile,
      goal: {
        goal_type: profile.goal_type || "recomp",
        goal_mode: "standard",
      },
      preferences,
      medical: {
        conditions: preferences.medical_conditions || [],
      },
      restriction_levels: {
        protein_level: 0,
        carbs_level: 0,
        fat_level: 0,
      },
    }),
    [metrics, profile, preferences]
  );

  async function handlePlan() {
    setLoading("plan");
    setError("");

    if (!profileReady) {
      setError("Complete your profile before generating a meal plan.");
      setLoading("");
      return;
    }

    try {
      let currentRulebase = rulebase;

      if (!currentRulebase) {
        const currentMetrics = metrics || (await analyzeMetrics(profile));
        setMetrics(currentMetrics);

        currentRulebase = await previewRulebase({
          ...goalPayload,
          metrics: currentMetrics,
        });

        setRulebase(currentRulebase);
      }

      const generatedPlan = await generateNutritionPlan({
        ...currentRulebase,
        preferences,
        options: {
          optimizer_iters: 200,
          max_llm_retries: 1,
        },
      });

      setPlan(generatedPlan);
      setSessionMemory({
        avoid_recipe_names: [],
        avoid_ingredient_names: [],
        avoid_atom_ids: [],
        last_replace_reason: "",
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  function openPlanReplacementModal() {
    setReplacementReason("simple_dislike");
    setReplacementDetail("");
    setReplacementFreeText("");
    setSelectedAvoidIngredients([]);
    setReplacementModal({ scope: "plan" });
  }

  function openRecipeReplacementModal(target, meal, recipe) {
    setReplacementReason("dislike_recipe");
    setReplacementDetail(recipe?.recipe_name || "");
    setReplacementFreeText("");
    setSelectedAvoidIngredients([]);
    setReplacementModal({
      scope: "recipe",
      target,
      meal,
      recipe,
      ingredientOptions: getRecipeIngredientOptions(recipe),
    });
  }

  function handleReplacementReasonChange(event) {
    const nextReason = event.target.value;
    const isRecipeModal = replacementModal?.scope === "recipe";
    const nextOptions = isRecipeModal
      ? replacementModal?.ingredientOptions || []
      : nextReason === "disliked_ingredient"
      ? ingredientOptions
      : nextReason === "simple_dislike"
      ? []
      : oldRecipeNames.map((name) => ({ value: name, label: name }));

    setReplacementReason(nextReason);
    setReplacementDetail(isRecipeModal ? replacementModal?.recipe?.recipe_name || "" : nextOptions[0]?.value || "");
    setSelectedAvoidIngredients([]);
  }

  function buildReplacementPayload(scope, target, replacementRequest) {
    const activeRulebase = rulebase || {};
    const scopedOldRecipeNames =
      scope === "plan"
        ? oldRecipeNames
        : uniqueStrings([
            ...(sessionMemory.avoid_recipe_names || []),
            ...(replacementRequest.avoid_recipes || []),
            target?.recipe_name,
          ]);
    const scopedOldIngredientNames = uniqueStrings([
      ...(sessionMemory.avoid_ingredient_names || []),
      ...(replacementRequest.avoid_ingredients || []),
    ]);

    return {
      scope,
      source_request_id: plan?.request_id,
      current_plan: plan?.meal_plan,
      derived_targets: activeRulebase.derived_targets || plan?.derived_targets || {},
      constraints: activeRulebase.constraints || plan?.constraint_report || {},
      preferences,
      medical_flags: activeRulebase.medical_flags || {},
      replacement_request: {
        scope,
        old_recipe_names: scopedOldRecipeNames,
        old_meal_titles: oldMealTitles,
        old_ingredient_names: scopedOldIngredientNames,
        session_short_term_memory: sessionMemory,
        ...replacementRequest,
      },
      target,
      options: {
        optimizer_iters: 200,
        max_llm_retries: 1,
      },
    };
  }

  async function handleReplace(scope, target = {}, replacementRequest = {}) {
    if (!profileReady) {
      setError("Complete your profile before changing a meal plan.");
      return;
    }

    if (!plan?.meal_plan) {
      setError("Generate a meal plan before changing it.");
      return;
    }

    const key = replacementKey(scope, target);
    setLoading(key);
    setError("");

    try {
      const updatedPlan = await replaceNutritionPlan(
        buildReplacementPayload(scope, target, replacementRequest)
      );

      setPlan(updatedPlan);
      setRulebase((current) =>
        current || {
          derived_targets: updatedPlan.derived_targets,
          constraints: updatedPlan.constraint_report,
          medical_flags: {},
        }
      );
      if (scope === "plan") setReplacementModal(null);
      if (scope === "recipe") setReplacementModal(null);
      return updatedPlan;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading("");
    }
  }

  async function handlePlanReplacementSubmit() {
    if (replacementReason === "simple_dislike") {
      await handleReplace("plan", {}, {
        reason_type: "simple_dislike",
        reason_detail: "User simply does not like this menu.",
        old_recipe_names: [],
        old_meal_titles: [],
        old_ingredient_names: [],
        ignore_short_term_memory: true,
        persist_short_term_memory: false,
        skip_old_plan_as_avoid: true,
      });
      return;
    }

    const detailOptions =
      replacementReason === "disliked_ingredient"
        ? ingredientOptions
        : oldRecipeNames.map((name) => ({ value: name, label: name }));
    const reasonDetail = replacementDetail || detailOptions[0]?.value || "";

    await handleReplace("plan", {}, {
      reason_type: replacementReason,
      reason_detail: reasonDetail,
    });
  }

  function toggleAvoidIngredient(option) {
    setSelectedAvoidIngredients((current) => {
      const exists = current.some((item) => item.value === option.value);
      if (exists) {
        return current.filter((item) => item.value !== option.value);
      }
      return [...current, option];
    });
  }

  async function handleRecipeReplacementSubmit() {
    const recipe = replacementModal?.recipe || {};
    const target = replacementModal?.target || {};
    const selectedNames = selectedAvoidIngredients.map((item) => item.value);
    const selectedAtomIds = selectedAvoidIngredients.map((item) => item.atomId).filter(Boolean);
    const avoidRecipes = uniqueStrings([recipe.recipe_name]);
    const constraintsDelta =
      replacementReason === "too_hard_to_cook"
        ? { max_cook_time_min: 20, cooking_level: "low" }
        : replacementReason === "cost_or_availability"
        ? { budget_level: "low" }
        : {};

    const updatedPlan = await handleReplace("recipe", target, {
      reason_code: replacementReason,
      reason_type: replacementReason,
      reason_detail:
        replacementReason === "dislike_ingredient"
          ? selectedNames.join(", ")
          : recipe.recipe_name || replacementDetail,
      avoid_recipes: avoidRecipes,
      avoid_ingredients: selectedNames,
      avoid_atom_ids: selectedAtomIds,
      free_text_reason: replacementFreeText,
      keep_same_meal_role: true,
      keep_similar_calories: true,
      allow_same_main_ingredient: replacementReason === "repeated_or_bored",
      constraints_delta: constraintsDelta,
    });

    if (!updatedPlan) return;

    setSessionMemory((current) => ({
      avoid_recipe_names: uniqueStrings([
        ...(current.avoid_recipe_names || []),
        ...avoidRecipes,
        ...(updatedPlan.short_term_memory_applied?.avoid_recipes || []),
      ]).slice(-12),
      avoid_ingredient_names: uniqueStrings([
        ...(current.avoid_ingredient_names || []),
        ...selectedNames,
        ...(updatedPlan.short_term_memory_applied?.avoid_ingredients || []),
      ]).slice(-12),
      avoid_atom_ids: Array.from(new Set([
        ...(current.avoid_atom_ids || []),
        ...selectedAtomIds,
      ])).slice(-12),
      last_replace_reason: replacementReason,
    }));
  }

  const totals = plan?.totals || {};
  const derivedTargets = rulebase?.derived_targets || plan?.derived_targets || {};
  const legacyTargets =
    rulebase?.targets ||
    rulebase?.daily_targets ||
    rulebase?.nutrition_targets ||
    plan?.targets ||
    plan?.daily_targets ||
    {};

  const calorieOverview = {
    key: "kcal",
    label: "Calories",
    unit: "kcal",
    icon: <Flame size={18} />,
    value: readNumber(totals, ["kcal", "calories", "total_kcal"]),
    target:
      readNumber(derivedTargets, [
        "calorie_target_kcal",
        "kcal",
        "calories",
        "target_kcal",
        "calorie_target",
      ]) ||
      readNumber(legacyTargets, [
        "kcal",
        "calories",
        "target_kcal",
        "calorie_target",
      ]) ||
      readNumber(metrics, ["tdee", "tdee_kcal", "target_kcal"]),
    accent: "green",
  };

  const nutrientOverview = [
    {
      key: "protein_g",
      label: "Protein",
      unit: "g",
      icon: <Dumbbell size={18} />,
      value: readNumber(totals, ["protein_g", "protein"]),
      accent: "purple",
    },
    {
      key: "carbs_g",
      label: "Carbs",
      unit: "g",
      icon: <Wheat size={18} />,
      value: readNumber(totals, ["carbs_g", "carbs", "carbohydrate_g"]),
      accent: "green",
    },
    {
      key: "fat_g",
      label: "Fat",
      unit: "g",
      icon: <Droplet size={18} />,
      value: readNumber(totals, ["fat_g", "fat"]),
      accent: "orange",
    },
    {
      key: "fiber_g",
      label: "Fiber",
      unit: "g",
      icon: <Leaf size={18} />,
      value: readNumber(totals, ["fiber_g", "fiber"]),
      accent: "green",
    },
  ];

  const meals = plan?.meal_plan?.days?.[0]?.meals || [];
  const oldRecipeNames = useMemo(
    () => getPlanRecipeNames(plan?.meal_plan),
    [plan]
  );
  const oldMealTitles = useMemo(
    () => getPlanMealTitles(plan?.meal_plan),
    [plan]
  );
  const ingredientOptions = useMemo(
    () => getPlanIngredientOptions(plan?.meal_plan),
    [plan]
  );
  const modalDetailOptions =
    replacementReason === "disliked_ingredient"
      ? ingredientOptions
      : replacementReason === "simple_dislike"
      ? []
      : oldRecipeNames.map((name) => ({ value: name, label: name }));
  const isBusy = Boolean(loading);

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-2xl bg-emerald-50 text-emerald-700">
              <Leaf size={22} />
            </div>

            <h1 className="page-title">Nutrition</h1>
          </div>

          <p className="mt-2 page-subtitle">
            Your profile metrics help us generate a personalized meal plan tailored to your goals.
          </p>
        </div>

        <button
          className="h-12 px-6 shadow-lg btn-primary rounded-xl shadow-emerald-200"
          onClick={plan ? openPlanReplacementModal : handlePlan}
          disabled={!profileReady || isBusy}
        >
          {loading === "plan" ? (
            <>
              <Sparkles size={16} className="animate-pulse" />
              Generating...
            </>
          ) : loading === "replace-plan" ? (
            <>
              <RefreshCw size={16} className="animate-spin" />
              Changing...
            </>
          ) : plan ? (
            <>
              <RefreshCw size={16} />
              Change menu
            </>
          ) : (
            <>
              <Wand2 size={16} />
              Generate menu
            </>
          )}
        </button>
      </header>

      <ErrorBanner message={error} />

      <section className="p-5 bg-white border shadow-sm rounded-3xl border-slate-200">
        <div className="mb-5">
          <h2 className="text-xl font-bold text-slate-950">
            Meal Plan Overview
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Compare your meal plan to your daily targets.
          </p>
        </div>

        {!plan ? (
          <div className="p-8 text-center border border-dashed rounded-2xl border-slate-300 bg-slate-50">
            <div className="flex items-center justify-center w-12 h-12 mx-auto rounded-2xl bg-emerald-50 text-emerald-700">
              <Utensils size={22} />
            </div>

            <p className="mt-3 font-semibold text-slate-800">
              No meal plan generated yet.
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Generate a menu to see nutrition progress and meal details.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <ProgressCard
              icon={calorieOverview.icon}
              label={calorieOverview.label}
              value={calorieOverview.value}
              target={calorieOverview.target}
              unit={calorieOverview.unit}
              accent={calorieOverview.accent}
            />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {nutrientOverview.map((item) => (
                <MetricCard
                  key={item.key}
                  icon={item.icon}
                  label={item.label}
                  value={item.value}
                  unit={item.unit}
                  accent={item.accent}
                />
              ))}
            </div>
          </div>
        )}
      </section>

      {plan && (
        <section className="grid gap-4 lg:grid-cols-2">
          {meals.map((meal, mealIndex) => {
            const mealTotalKcal = getMealTotalKcal(meal);
            const mealTarget = {
              day_index: 0,
              meal_index: mealIndex,
              meal_slot: meal.slot,
            };
            const mealLoading = loading === replacementKey("meal", mealTarget);

            return (
              <article
                key={`${meal.slot}-${meal.title}`}
                className="flex min-h-[320px] flex-col rounded-3xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex items-center justify-between gap-3 p-5 border-b border-slate-100">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center h-9 w-9 rounded-xl bg-emerald-50 text-emerald-700">
                      {mealIcon(meal.slot)}
                    </div>

                    <div>
                      <h3 className="font-bold text-slate-950">
                        {normalizeMealTitle(meal.slot)}
                      </h3>
                      {meal.title && (
                        <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">
                          {meal.title}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-col items-end gap-2">
                    <span className="px-3 py-1 text-sm font-bold rounded-full bg-emerald-50 text-emerald-700">
                      {formatNumber(mealTotalKcal, 0)} kcal
                    </span>
                    <button
                      type="button"
                      className="inline-flex h-8 items-center gap-1.5 rounded border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-600 transition hover:border-emerald-200 hover:text-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                      onClick={() =>
                        handleReplace("meal", mealTarget, {
                          reason_type: "refresh_meal",
                          reason_detail: meal.title || meal.slot,
                        })
                      }
                      disabled={isBusy}
                    >
                      <RefreshCw size={13} className={mealLoading ? "animate-spin" : ""} />
                      {mealLoading ? "Changing..." : "Change meal"}
                    </button>
                  </div>
                </div>

                <div className="flex-1 p-4">
                  <div className="overflow-hidden rounded-2xl border border-slate-200">
                  {(meal.recipes || []).map((recipe, recipeIndex) => {
                    const recipeCalories = getRecipeCalories(recipe);
                    const recipeTarget = {
                      day_index: 0,
                      meal_index: mealIndex,
                      meal_slot: meal.slot,
                      recipe_index: recipeIndex,
                      recipe_name: recipe.recipe_name,
                    };
                    const recipeLoading = loading === replacementKey("recipe", recipeTarget);

                    return (
                      <div
                        key={`${meal.slot}-${recipe.recipe_name}-${recipeIndex}`}
                        role="button"
                        tabIndex={0}
                        className="group flex cursor-pointer items-center justify-between gap-3 border-b border-slate-100 bg-white p-3 transition last:border-b-0 hover:bg-emerald-50/40 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-emerald-500"
                        onClick={() => setSelectedRecipeDetail({ meal, recipe })}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            setSelectedRecipeDetail({ meal, recipe });
                          }
                        }}
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <RecipeThumb recipe={recipe} />
                          <div className="min-w-0">
                            <p className="truncate font-semibold text-slate-900 transition group-hover:text-emerald-800">
                              {recipe.recipe_name}
                            </p>
                            <p className="mt-1 text-sm text-slate-500">
                              {recipeCalories !== null
                                ? `${formatNumber(recipeCalories, 0)} kcal`
                                : "-"}
                            </p>
                          </div>
                        </div>

                        <button
                          type="button"
                          className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-600 transition hover:border-emerald-200 hover:text-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                          onClick={(event) => {
                            event.stopPropagation();
                            openRecipeReplacementModal(recipeTarget, meal, recipe);
                          }}
                          disabled={isBusy}
                        >
                          <RefreshCw size={13} className={recipeLoading ? "animate-spin" : ""} />
                          {recipeLoading ? "Changing..." : "Change dish"}
                        </button>
                      </div>
                    );
                  })}
                  </div>
                </div>

                <div className="flex items-center justify-between p-5 mt-auto border-t border-slate-100">
                  <span className="font-semibold text-slate-600">Total</span>
                  <span className="font-bold text-emerald-700">
                    {formatNumber(mealTotalKcal, 0)} kcal
                  </span>
                </div>
              </article>
            );
          })}
        </section>
      )}

      {plan && (
        <div className="flex items-center justify-center px-5 py-4 text-sm border rounded-2xl border-emerald-100 bg-emerald-50/70 text-slate-600">
          <Leaf size={16} className="mr-2 text-emerald-700" />
          Stay consistent, stay hydrated, and listen to your body. Small choices, big results.
        </div>
      )}

      <RecipeDetailModal
        detail={selectedRecipeDetail}
        onClose={() => setSelectedRecipeDetail(null)}
      />

      {replacementModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6">
          <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-950">
                  {replacementModal.scope === "recipe" ? "Change dish" : "Change menu"}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  {replacementModal.scope === "recipe"
                    ? "Choose why this dish should change. The app will avoid repeating it in this session."
                    : "Select what should be avoided in the new menu."}
                </p>
              </div>

              <button
                type="button"
                className="flex h-9 w-9 items-center justify-center rounded border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
                onClick={() => setReplacementModal(null)}
                aria-label="Close replacement modal"
              >
                <X size={16} />
              </button>
            </div>

            <div className="mt-5 space-y-4">
              {replacementModal.scope === "recipe" ? (
                <>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-sm font-semibold text-slate-900">
                      {replacementModal.recipe?.recipe_name || "Selected dish"}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {replacementModal.meal?.slot
                        ? `${normalizeMealTitle(replacementModal.meal.slot)} dish`
                        : "Current dish"}
                    </p>
                  </div>

                  <label className="block">
                    <span className="mb-1 block text-sm font-semibold text-slate-700">
                      Reason
                    </span>
                    <select
                      className="input"
                      value={replacementReason}
                      onChange={handleReplacementReasonChange}
                    >
                      {RECIPE_REPLACEMENT_REASONS.map((reason) => (
                        <option key={reason.value} value={reason.value}>
                          {reason.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  {replacementReason === "dislike_ingredient" && (
                    <div>
                      <span className="mb-2 block text-sm font-semibold text-slate-700">
                        Ingredient to avoid in this replacement
                      </span>
                      <div className="space-y-2 rounded-2xl border border-slate-200 p-3">
                        {(replacementModal.ingredientOptions || []).length ? (
                          replacementModal.ingredientOptions.map((option) => {
                            const checked = selectedAvoidIngredients.some(
                              (item) => item.value === option.value
                            );

                            return (
                              <label
                                key={option.value}
                                className="flex items-center gap-2 text-sm text-slate-700"
                              >
                                <input
                                  type="checkbox"
                                  className="h-4 w-4 rounded border-slate-300 text-emerald-600"
                                  checked={checked}
                                  onChange={() => toggleAvoidIngredient(option)}
                                />
                                {option.label}
                              </label>
                            );
                          })
                        ) : (
                          <p className="text-sm text-slate-500">
                            No ingredients found for this dish.
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {replacementReason === "other" && (
                    <label className="block">
                      <span className="mb-1 block text-sm font-semibold text-slate-700">
                        Note
                      </span>
                      <textarea
                        className="input min-h-24 py-2"
                        value={replacementFreeText}
                        onChange={(event) => setReplacementFreeText(event.target.value)}
                        placeholder="Add a short temporary reason"
                      />
                    </label>
                  )}

                  <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 p-3 text-xs leading-5 text-slate-600">
                    Temporary memory: this avoids the selected dish and ingredients only for the current replacement session.
                  </div>
                </>
              ) : (
                <>
                  <label className="block">
                    <span className="mb-1 block text-sm font-semibold text-slate-700">
                      Reason
                    </span>
                    <select
                      className="input"
                      value={replacementReason}
                      onChange={handleReplacementReasonChange}
                    >
                      <option value="simple_dislike">I simply do not like this menu</option>
                      <option value="disliked_dish">I do not like a dish in this menu</option>
                      <option value="disliked_ingredient">I do not like an ingredient in this menu</option>
                    </select>
                  </label>

                  {replacementReason === "simple_dislike" ? (
                    <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 p-3 text-xs leading-5 text-slate-600">
                      This will refresh the menu without saving any dislike or avoidance behavior.
                    </div>
                  ) : (
                    <label className="block">
                      <span className="mb-1 block text-sm font-semibold text-slate-700">
                        {replacementReason === "disliked_ingredient" ? "Ingredient" : "Dish"}
                      </span>
                      {modalDetailOptions.length ? (
                        <select
                          className="input"
                          value={replacementDetail || modalDetailOptions[0]?.value || ""}
                          onChange={(event) => setReplacementDetail(event.target.value)}
                        >
                          {modalDetailOptions.map((item) => (
                            <option key={item.value} value={item.value}>
                              {item.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          className="input"
                          value={replacementDetail}
                          onChange={(event) => setReplacementDetail(event.target.value)}
                          placeholder="Type item name"
                        />
                      )}
                    </label>
                  )}
                </>
              )}
            </div>

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                className="btn-secondary justify-center rounded-xl"
                onClick={() => setReplacementModal(null)}
                disabled={loading === "replace-plan" || loading === replacementKey("recipe", replacementModal.target)}
              >
                Cancel
              </button>
              {replacementModal.scope === "recipe" ? (
                <button
                  type="button"
                  className="btn-primary justify-center rounded-xl"
                  onClick={handleRecipeReplacementSubmit}
                  disabled={
                    loading === replacementKey("recipe", replacementModal.target) ||
                    (replacementReason === "dislike_ingredient" && !selectedAvoidIngredients.length)
                  }
                >
                  {loading === replacementKey("recipe", replacementModal.target) ? (
                    <>
                      <RefreshCw size={16} className="animate-spin" />
                      Changing...
                    </>
                  ) : (
                    <>
                      <RefreshCw size={16} />
                      Change dish
                    </>
                  )}
                </button>
              ) : (
                <button
                  type="button"
                  className="btn-primary justify-center rounded-xl"
                  onClick={handlePlanReplacementSubmit}
                  disabled={
                    loading === "replace-plan" ||
                    (replacementReason !== "simple_dislike" && !replacementDetail && !modalDetailOptions.length)
                  }
                >
                  {loading === "replace-plan" ? (
                    <>
                      <RefreshCw size={16} className="animate-spin" />
                      Changing...
                    </>
                  ) : (
                    <>
                      <RefreshCw size={16} />
                      Change menu
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
