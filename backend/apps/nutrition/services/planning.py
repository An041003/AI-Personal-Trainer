import json
import uuid
from copy import deepcopy

from django.core.exceptions import ImproperlyConfigured
from rapidfuzz import fuzz

from apps.common.audit import record_audit
from apps.common.models import Plan, ShortTermMemoryEntry
from apps.common.openai_client import (
    generate_json,
    get_token_usage,
    reset_token_usage_tracking,
    start_token_usage_tracking,
)
from apps.common.prompt import (
    NUTRITION_MEAL_REPLACEMENT_SYSTEM_PROMPT,
    NUTRITION_PLAN_REPLACEMENT_SYSTEM_PROMPT,
    NUTRITION_PLAN_SYSTEM_PROMPT,
    NUTRITION_RECIPE_REPLACEMENT_SYSTEM_PROMPT,
)
from apps.common.short_term_memory import load_short_term_memory, remember_short_term_memory
from apps.common.utils import normalize_text
from apps.nutrition.models import NutritionAtom
from apps.nutrition.services.calculator import calculate_plan_totals
from apps.nutrition.services.catalog import resolve_ingredient
from apps.nutrition.services.evaluation import evaluate_meal_plan
from apps.nutrition.services.optimizer import assign_nutrients, optimize_grams


ROLE_DEFAULT_GRAMS = {
    "protein": 130,
    "carb": 150,
    "veg": 150,
    "fat": 10,
    "fruit": 120,
}

REPLACEMENT_ROLE_ORDER = ["protein", "carb", "veg", "fat", "fruit", "dairy", "sauce", "snack"]
ROLE_FOOD_ROLE_HINTS = {
    "protein": ["protein_source"],
    "carb": ["carb_source"],
    "veg": ["vegetable"],
    "fat": ["fat_source"],
    "fruit": ["fruit"],
    "dairy": ["dairy"],
    "sauce": ["sauce"],
    "snack": ["snack"],
}


def _as_index(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value, low, high):
    return max(low, min(high, value))


def _unique_strings(values):
    result = []
    seen = set()
    for value in values or []:
        text = str(value or "").strip()
        key = text.lower()
        if text and key not in seen:
            result.append(text)
            seen.add(key)
    return result


def _canonical_role(role):
    role = normalize_text(role).replace("-", "_")
    if role in {"protein_source", "meat", "fish", "seafood"}:
        return "protein"
    if role in {"carb_source", "grain", "starchy_carb"}:
        return "carb"
    if role in {"vegetable", "fiber", "fiber_source"}:
        return "veg"
    if role in {"fat_source", "oil"}:
        return "fat"
    if role in {"fruit"}:
        return "fruit"
    if role in {"dairy"}:
        return "dairy"
    if role in {"sauce", "spice"}:
        return "sauce"
    if role in {"snack"}:
        return "snack"
    return role or "protein"


def _name_matches_any(value, names):
    normalized = normalize_text(value)
    if not normalized:
        return False
    for name in names or []:
        needle = normalize_text(name)
        if needle and (needle in normalized or normalized in needle):
            return True
    return False


def _atom_haystack(atom):
    return " ".join(
        [
            atom.canonical_name or "",
            atom.display_name_vi or "",
            atom.aliases or "",
            atom.category or "",
            atom.food_role or "",
        ]
    )


def _atom_blocked(atom, banned_names=None, banned_atom_ids=None):
    if banned_atom_ids and atom.id in set(banned_atom_ids):
        return True
    return _name_matches_any(_atom_haystack(atom), banned_names or [])


def _ingredient_display_name(ingredient):
    return (
        ingredient.get("canonical_name")
        or ingredient.get("name")
        or ingredient.get("ingredient_name")
        or ""
    )


def _ingredient_nutrients(ingredient):
    return ingredient.get("nutrients") or {}


def _ingredient_totals(recipe):
    totals = {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}
    for ingredient in recipe.get("ingredients", []):
        nutrients = _ingredient_nutrients(ingredient)
        for key in totals:
            totals[key] += _as_float(nutrients.get(key))
    return {key: round(value, 2) for key, value in totals.items()}


def _entity_totals(entity):
    totals = entity.get("totals") or {}
    if totals:
        return {
            "kcal": _as_float(totals.get("kcal")),
            "protein_g": _as_float(totals.get("protein_g")),
            "carbs_g": _as_float(totals.get("carbs_g")),
            "fat_g": _as_float(totals.get("fat_g")),
            "fiber_g": _as_float(totals.get("fiber_g")),
        }
    if entity.get("ingredients"):
        return _ingredient_totals(entity)
    return {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}


def _recipe_names(meal_plan):
    names = []
    for day in meal_plan.get("days", []):
        for meal in day.get("meals", []):
            for recipe in meal.get("recipes", []):
                names.append(recipe.get("recipe_name"))
    return _unique_strings(names)


def _meal_titles(meal_plan):
    names = []
    for day in meal_plan.get("days", []):
        for meal in day.get("meals", []):
            names.extend([meal.get("title"), meal.get("slot")])
    return _unique_strings(names)


def _ingredient_names(meal_plan):
    names = []
    for day in meal_plan.get("days", []):
        for meal in day.get("meals", []):
            for recipe in meal.get("recipes", []):
                for ingredient in recipe.get("ingredients", []):
                    names.extend(
                        [
                            ingredient.get("canonical_name"),
                            ingredient.get("ingredient_name"),
                            ingredient.get("name"),
                        ]
                    )
    return _unique_strings(names)


def _recipe_summary(recipe):
    return {
        "recipe_name": recipe.get("recipe_name"),
        "totals": _entity_totals(recipe),
        "ingredients": _unique_strings(
            [
                ingredient.get("canonical_name") or ingredient.get("ingredient_name") or ingredient.get("name")
                for ingredient in recipe.get("ingredients", [])
            ]
        ),
    }


def _meal_summary(meal):
    return {
        "slot": meal.get("slot"),
        "title": meal.get("title"),
        "totals": _entity_totals(meal),
        "recipes": [_recipe_summary(recipe) for recipe in meal.get("recipes", [])],
    }


def _plan_summary(meal_plan):
    return {
        "days": [
            {
                "day_index": day.get("day_index"),
                "meals": [_meal_summary(meal) for meal in day.get("meals", [])],
            }
            for day in meal_plan.get("days", [])
        ]
    }


def _get_day(meal_plan, target):
    days = meal_plan.get("days") or []
    if not days:
        raise ValueError("Current meal plan is missing days.")

    raw_index = target.get("day_index")
    day_index = _as_index(raw_index, 0)
    if day_index >= len(days) and day_index > 0:
        day_index -= 1

    if day_index < 0 or day_index >= len(days):
        raise ValueError("Selected day was not found.")
    return days[day_index], day_index


def _get_meal(day, target):
    meals = day.get("meals") or []
    if not meals:
        raise ValueError("Selected day is missing meals.")

    meal_index = _as_index(target.get("meal_index"), -1)
    if 0 <= meal_index < len(meals):
        return meals[meal_index], meal_index

    target_slot = str(target.get("meal_slot") or "").strip().lower()
    if target_slot:
        for index, meal in enumerate(meals):
            if str(meal.get("slot") or "").strip().lower() == target_slot:
                return meal, index

    raise ValueError("Selected meal was not found.")


def _get_recipe(meal, target):
    recipes = meal.get("recipes") or []
    if not recipes:
        raise ValueError("Selected meal is missing recipes.")

    recipe_index = _as_index(target.get("recipe_index"), -1)
    if 0 <= recipe_index < len(recipes):
        return recipes[recipe_index], recipe_index

    target_name = str(target.get("recipe_name") or "").strip().lower()
    if target_name:
        for index, recipe in enumerate(recipes):
            if str(recipe.get("recipe_name") or "").strip().lower() == target_name:
                return recipe, index

    raise ValueError("Selected recipe was not found.")


def _get_recipe_from_plan(meal_plan, target):
    day, _ = _get_day(meal_plan, target)
    meal, _ = _get_meal(day, target)
    recipe, _ = _get_recipe(meal, target)
    return recipe


def _role_profile_for_recipe(recipe, meal=None):
    ingredients = []
    roles = set()
    for ingredient in recipe.get("ingredients", []):
        role = _canonical_role(ingredient.get("role") or "")
        roles.add(role)
        nutrients = _ingredient_nutrients(ingredient)
        ingredients.append(
            {
                "atom_id": ingredient.get("atom_id"),
                "name": _ingredient_display_name(ingredient),
                "role": role,
                "grams": _as_float(ingredient.get("grams")),
                "kcal": _as_float(nutrients.get("kcal")),
                "protein_g": _as_float(nutrients.get("protein_g")),
                "carbs_g": _as_float(nutrients.get("carbs_g")),
                "fat_g": _as_float(nutrients.get("fat_g")),
                "fiber_g": _as_float(nutrients.get("fiber_g")),
            }
        )

    totals = _entity_totals(recipe)
    required_roles = set()
    for role in ["protein", "carb", "veg", "fat", "fruit", "dairy"]:
        if role in roles:
            required_roles.add(role)

    if totals.get("protein_g", 0) >= 10:
        required_roles.add("protein")
    if totals.get("carbs_g", 0) >= 15:
        required_roles.add("carb")
    if totals.get("fiber_g", 0) >= 3:
        required_roles.add("veg")

    return {
        "meal_slot": (meal or {}).get("slot"),
        "meal_title": (meal or {}).get("title"),
        "recipe_name": recipe.get("recipe_name"),
        "ingredients": ingredients,
        "required_roles": [role for role in REPLACEMENT_ROLE_ORDER if role in required_roles],
        "totals": totals,
        "target_ranges": {
            "kcal": {
                "min": round(totals["kcal"] * 0.90, 1) if totals["kcal"] else 0,
                "max": round(totals["kcal"] * 1.10, 1) if totals["kcal"] else 0,
                "relaxed_min": round(totals["kcal"] * 0.85, 1) if totals["kcal"] else 0,
                "relaxed_max": round(totals["kcal"] * 1.15, 1) if totals["kcal"] else 0,
            },
            "protein_g": {
                "min": round(totals["protein_g"] * 0.85, 1) if totals["protein_g"] else 0,
                "max": round(totals["protein_g"] * 1.15, 1) if totals["protein_g"] else 0,
            },
        },
    }


def _session_memory(replacement_request):
    session = replacement_request.get("session_short_term_memory") or {}
    reason_code = (
        replacement_request.get("reason_code")
        or replacement_request.get("reason_type")
        or session.get("last_replace_reason")
        or "unknown"
    )
    avoid_recipes = _unique_strings(
        (replacement_request.get("avoid_recipes") or [])
        + (replacement_request.get("old_recipe_names") or [])
        + (session.get("avoid_recipe_names") or [])
    )
    avoid_ingredients = _unique_strings(
        (replacement_request.get("avoid_ingredients") or [])
        + (replacement_request.get("old_ingredient_names") or [])
        + (session.get("avoid_ingredient_names") or [])
    )

    reason_detail = str(replacement_request.get("reason_detail") or "").strip()
    if reason_code in {"dislike_ingredient", "disliked_ingredient"} and reason_detail:
        avoid_ingredients = _unique_strings(avoid_ingredients + [reason_detail])
    if reason_code in {"dislike_recipe", "disliked_dish", "refresh_recipe"} and reason_detail:
        avoid_recipes = _unique_strings(avoid_recipes + [reason_detail])

    return {
        "scope": replacement_request.get("scope") or "replace_recipe",
        "domain": "nutrition",
        "meal_slot": replacement_request.get("meal_slot"),
        "avoid_recipe_names": avoid_recipes,
        "avoid_ingredient_names": avoid_ingredients,
        "avoid_atom_ids": replacement_request.get("avoid_atom_ids") or session.get("avoid_atom_ids") or [],
        "reason_code": reason_code,
        "must_not_repeat_old_recipe": True,
        "allow_same_ingredient_group": bool(replacement_request.get("allow_same_main_ingredient")),
        "expires_policy": "after_successful_replace",
        "created_from_action": "replace_recipe",
    }


def _merge_nutrition_session_memory(replacement_request, db_memory):
    updated = deepcopy(replacement_request or {})
    session = deepcopy(updated.get("session_short_term_memory") or {})
    session["avoid_recipe_names"] = _unique_strings(
        (db_memory.get("avoid_recipe_names") or [])
        + (session.get("avoid_recipe_names") or [])
    )
    session["avoid_ingredient_names"] = _unique_strings(
        (db_memory.get("avoid_ingredient_names") or [])
        + (session.get("avoid_ingredient_names") or [])
    )
    session["avoid_atom_ids"] = list(
        {
            int(atom_id)
            for atom_id in (db_memory.get("avoid_atom_ids") or []) + (session.get("avoid_atom_ids") or [])
            if str(atom_id).isdigit()
        }
    )
    session["last_replace_reason"] = (
        session.get("last_replace_reason")
        or db_memory.get("last_replace_reason")
        or ""
    )
    updated["session_short_term_memory"] = session
    return updated


def _remember_nutrition_memory(user, memory, *, request_id, target):
    entities = []
    for name in memory.get("avoid_recipe_names") or []:
        entities.append({"entity_type": "recipe", "entity_key": name, "raw_label": name})
    for name in memory.get("avoid_ingredient_names") or []:
        entities.append({"entity_type": "ingredient", "entity_key": name, "raw_label": name})
    for atom_id in memory.get("avoid_atom_ids") or []:
        entities.append({"entity_type": "atom_id", "entity_key": atom_id, "raw_label": str(atom_id)})
    if not entities:
        return []
    return remember_short_term_memory(
        user,
        domain=ShortTermMemoryEntry.DOMAIN_NUTRITION,
        scope=memory.get("scope") or "replace_recipe",
        entities=entities,
        reason_code=memory.get("reason_code") or "unknown",
        source_action=memory.get("created_from_action") or "replace_nutrition",
        metadata={"request_id": str(request_id), "target": target},
    )


def remember_stale_nutrition_plan(user, payload, *, source_plan_id=None, source_created_at=None):
    meal_plan = (payload or {}).get("meal_plan") if isinstance(payload, dict) else {}
    if not isinstance(meal_plan, dict):
        return []

    recipe_names = _recipe_names(meal_plan)
    if not recipe_names:
        return []

    source_created_value = source_created_at.isoformat() if source_created_at else None
    memory = {
        "scope": "daily_rollover",
        "avoid_recipe_names": recipe_names,
        "avoid_ingredient_names": [],
        "avoid_atom_ids": [],
        "reason_code": "new_day_rollover",
        "created_from_action": "stale_latest_plan",
    }
    return _remember_nutrition_memory(
        user,
        memory,
        request_id=uuid.uuid4(),
        target={
            "source_plan_id": source_plan_id,
            "source_created_at": source_created_value,
        },
    )


def _memory_for_recipe_replace(replacement_request, old_recipe):
    memory = _session_memory(replacement_request)
    memory["avoid_recipe_names"] = _unique_strings(
        memory["avoid_recipe_names"] + [old_recipe.get("recipe_name")]
    )
    old_avoid_atoms = []
    for ingredient in old_recipe.get("ingredients", []):
        if _name_matches_any(_ingredient_display_name(ingredient), memory["avoid_ingredient_names"]):
            old_avoid_atoms.append(ingredient.get("atom_id"))
    memory["avoid_atom_ids"] = [atom_id for atom_id in set(memory["avoid_atom_ids"] + old_avoid_atoms) if atom_id]
    return memory


def _constraints_for_memory(constraints, memory):
    updated = deepcopy(constraints or {})
    hard_bans = list(updated.get("hard_bans") or [])
    hard_bans = _unique_strings(hard_bans + (memory.get("avoid_ingredient_names") or []))
    updated["hard_bans"] = hard_bans
    updated.setdefault("short_term_memory", memory)
    return updated


def _candidate_pool_for_roles(role_profile, constraints, memory):
    banned_names = _unique_strings(
        (constraints.get("hard_bans") or [])
        + (memory.get("avoid_ingredient_names") or [])
    )
    banned_atom_ids = memory.get("avoid_atom_ids") or []
    required_roles = role_profile.get("required_roles") or ["protein", "carb", "veg"]
    pools = {}

    for role in required_roles:
        hints = ROLE_FOOD_ROLE_HINTS.get(role, [role])
        atoms = []
        queryset = NutritionAtom.objects.filter(is_active=True)
        for atom in queryset:
            role_text = normalize_text(" ".join([atom.food_role or "", atom.category or ""]))
            if not any(normalize_text(hint) in role_text for hint in hints):
                continue
            if _atom_blocked(atom, banned_names=banned_names, banned_atom_ids=banned_atom_ids):
                continue
            atoms.append(atom)
            if len(atoms) >= 12:
                break
        pools[role] = [
            {
                "canonical_name": atom.canonical_name,
                "display_name_vi": atom.display_name_vi,
                "food_role": atom.food_role,
                "default_serving_g": float(atom.default_serving_g or ROLE_DEFAULT_GRAMS.get(role, 100)),
            }
            for atom in atoms
        ]
    return pools


def _extract_plan_draft(value):
    draft = value.get("meal_plan") if isinstance(value, dict) and isinstance(value.get("meal_plan"), dict) else value
    if not isinstance(draft, dict) or not draft.get("days"):
        raise RuntimeError("LLM returned an invalid meal plan draft.")
    draft.setdefault("version", "draft_v1")
    draft.setdefault("mode", "day")
    return draft


def _extract_meal(value):
    meal = value.get("meal") if isinstance(value, dict) and isinstance(value.get("meal"), dict) else value
    if not isinstance(meal, dict) or not meal.get("recipes"):
        raise RuntimeError("LLM returned an invalid replacement meal.")
    return meal


def _extract_recipe(value):
    recipe = value.get("recipe") if isinstance(value, dict) and isinstance(value.get("recipe"), dict) else value
    if not isinstance(recipe, dict) or not recipe.get("ingredients"):
        raise RuntimeError("LLM returned an invalid replacement recipe.")
    return recipe


def _constraints_for_replacement(constraints, replacement_request):
    updated = deepcopy(constraints or {})
    reason_type = replacement_request.get("reason_type") or replacement_request.get("reason_code")
    reason_detail = str(replacement_request.get("reason_detail") or "").strip()
    temp_avoid_ingredients = list(replacement_request.get("avoid_ingredients") or [])
    session = replacement_request.get("session_short_term_memory") or {}
    temp_avoid_ingredients += list(session.get("avoid_ingredient_names") or [])
    if reason_type in {"disliked_ingredient", "dislike_ingredient"} and reason_detail:
        temp_avoid_ingredients.append(reason_detail)
    if temp_avoid_ingredients:
        hard_bans = list(updated.get("hard_bans") or [])
        hard_bans = _unique_strings(hard_bans + temp_avoid_ingredients)
        updated["hard_bans"] = hard_bans
    return updated


def _replacement_prompt(
    payload,
    current_plan,
    constraints,
    scope,
    target,
    replacement_request,
    *,
    short_term_memory=None,
    role_profile=None,
    candidate_pools=None,
):
    old_recipe_names = _unique_strings(
        _recipe_names(current_plan) + (replacement_request.get("old_recipe_names") or [])
    )
    old_meal_titles = _unique_strings(
        _meal_titles(current_plan) + (replacement_request.get("old_meal_titles") or [])
    )
    if scope == "plan":
        old_ingredient_names = _unique_strings(
            _ingredient_names(current_plan) + (replacement_request.get("old_ingredient_names") or [])
        )
    else:
        session = replacement_request.get("session_short_term_memory") or {}
        old_ingredient_names = _unique_strings(
            (replacement_request.get("old_ingredient_names") or [])
            + (replacement_request.get("avoid_ingredients") or [])
            + (session.get("avoid_ingredient_names") or [])
        )
    prompt = {
        "scope": scope,
        "target": target,
        "replacement_request": {
            **replacement_request,
            "old_recipe_names": old_recipe_names,
            "old_meal_titles": old_meal_titles,
            "old_ingredient_names": old_ingredient_names,
        },
        "short_term_memory": short_term_memory or {},
        "old_meal_role_profile": role_profile or {},
        "candidate_pools": candidate_pools or {},
        "derived_targets": payload.get("derived_targets") or {},
        "constraints": constraints,
        "preferences": payload.get("preferences") or {},
        "medical_flags": payload.get("medical_flags") or {},
        "extra_restrictions": payload.get("extra_restrictions") or [],
        "current_plan_summary": _plan_summary(current_plan),
    }

    if scope in {"meal", "recipe"}:
        day, _ = _get_day(current_plan, target)
        meal, _ = _get_meal(day, target)
        prompt["target_meal"] = _meal_summary(meal)
        if scope == "recipe":
            recipe, _ = _get_recipe(meal, target)
            prompt["target_recipe"] = _recipe_summary(recipe)

    return prompt


def _replace_meal(current_plan, target, replacement_meal):
    updated = deepcopy(current_plan)
    day, _ = _get_day(updated, target)
    current_meal, meal_index = _get_meal(day, target)
    replacement_meal = deepcopy(replacement_meal)
    replacement_meal["slot"] = current_meal.get("slot") or target.get("meal_slot") or replacement_meal.get("slot")
    day["meals"][meal_index] = replacement_meal
    return updated


def _replace_recipe(current_plan, target, replacement_recipe):
    updated = deepcopy(current_plan)
    day, _ = _get_day(updated, target)
    meal, _ = _get_meal(day, target)
    _, recipe_index = _get_recipe(meal, target)
    meal["recipes"][recipe_index] = deepcopy(replacement_recipe)
    return updated


def _recipe_names_overlap(old_recipe, new_recipe):
    old_names = {
        normalize_text(_ingredient_display_name(ingredient))
        for ingredient in old_recipe.get("ingredients", [])
        if _canonical_role(ingredient.get("role")) in {"protein", "carb", "veg", "fat"}
    }
    new_names = {
        normalize_text(_ingredient_display_name(ingredient))
        for ingredient in new_recipe.get("ingredients", [])
        if _canonical_role(ingredient.get("role")) in {"protein", "carb", "veg", "fat"}
    }
    old_names.discard("")
    new_names.discard("")
    if not old_names:
        return 0
    return len(old_names.intersection(new_names)) / len(old_names)


def _validate_replacement_recipe(new_recipe, old_recipe, role_profile, memory):
    issues = []
    warnings = []
    recipe_name = str(new_recipe.get("recipe_name") or "")
    normalized_name = normalize_text(recipe_name)
    for old_name in memory.get("avoid_recipe_names") or []:
        old_normalized = normalize_text(old_name)
        if not old_normalized:
            continue
        if normalized_name == old_normalized or fuzz.token_set_ratio(normalized_name, old_normalized) >= 92:
            issues.append(f"Replacement repeats an avoided recipe name: {old_name}")
            break

    avoid_names = memory.get("avoid_ingredient_names") or []
    avoid_atom_ids = set(memory.get("avoid_atom_ids") or [])
    new_roles = set()
    for ingredient in new_recipe.get("ingredients", []):
        new_roles.add(_canonical_role(ingredient.get("role")))
        if ingredient.get("atom_id") in avoid_atom_ids:
            issues.append(f"Replacement uses an avoided ingredient atom: {ingredient.get('name')}")
        if _name_matches_any(_ingredient_display_name(ingredient), avoid_names):
            issues.append(f"Replacement uses an avoided ingredient: {_ingredient_display_name(ingredient)}")

    required_roles = set(role_profile.get("required_roles") or [])
    for role in required_roles:
        if role == "veg":
            if not new_roles.intersection({"veg", "fruit"}):
                issues.append("Old recipe had a vegetable/fiber role, but replacement does not.")
        elif role not in new_roles:
            issues.append(f"Old recipe had role '{role}', but replacement does not.")

    reason_code = memory.get("reason_code")
    if reason_code in {"dislike_recipe", "disliked_dish", "repeated_or_bored", "refresh_recipe"}:
        overlap = _recipe_names_overlap(old_recipe, new_recipe)
        if overlap >= 0.80 and not memory.get("allow_same_ingredient_group"):
            issues.append("Replacement uses almost the same core ingredients as the old recipe.")

    old_totals = role_profile.get("totals") or {}
    new_totals = _entity_totals(new_recipe)
    old_kcal = _as_float(old_totals.get("kcal"))
    new_kcal = _as_float(new_totals.get("kcal"))
    if old_kcal and new_kcal:
        if new_kcal < old_kcal * 0.85 or new_kcal > old_kcal * 1.15:
            issues.append("Replacement calories are outside the relaxed old recipe range.")
        elif new_kcal < old_kcal * 0.90 or new_kcal > old_kcal * 1.10:
            warnings.append("Replacement calories are outside +/-10% of the old recipe.")

    old_protein = _as_float(old_totals.get("protein_g"))
    new_protein = _as_float(new_totals.get("protein_g"))
    if old_protein >= 10 and new_protein:
        if new_protein < old_protein * 0.75:
            issues.append("Replacement protein is too low compared with the old recipe.")
        elif new_protein < old_protein * 0.85 or new_protein > old_protein * 1.20:
            warnings.append("Replacement protein is not close to the old recipe.")

    return {"issues": _unique_strings(issues), "warnings": _unique_strings(warnings), "totals": new_totals}


def _tune_recipe_to_profile(recipe, role_profile):
    old_totals = role_profile.get("totals") or {}
    target_kcal = _as_float(old_totals.get("kcal"))
    target_protein = _as_float(old_totals.get("protein_g"))
    if not target_kcal and not target_protein:
        return recipe

    totals = _entity_totals(recipe)
    current_kcal = _as_float(totals.get("kcal"))
    if target_kcal and current_kcal:
        scale = _clamp(target_kcal / current_kcal, 0.70, 1.40)
        for ingredient in recipe.get("ingredients", []):
            grams = _as_float(ingredient.get("grams"), ROLE_DEFAULT_GRAMS.get(_canonical_role(ingredient.get("role")), 100))
            ingredient["grams"] = round(max(5.0, grams * scale), 1)

    assign_nutrients({"days": [{"meals": [{"recipes": [recipe]}]}]})
    calculate_plan_totals({"days": [{"meals": [{"recipes": [recipe]}]}]})
    totals = _entity_totals(recipe)
    current_protein = _as_float(totals.get("protein_g"))
    if target_protein and current_protein and current_protein < target_protein * 0.85:
        for ingredient in recipe.get("ingredients", []):
            if _canonical_role(ingredient.get("role")) == "protein":
                factor = _clamp((target_protein * 0.95) / current_protein, 1.05, 1.50)
                ingredient["grams"] = round(_as_float(ingredient.get("grams")) * factor, 1)
                break
    return recipe


def _fallback_recipe(role_profile, candidate_pools, memory):
    ingredients = []
    required_roles = role_profile.get("required_roles") or ["protein", "carb", "veg"]
    if not required_roles:
        required_roles = ["protein", "carb", "veg"]

    for role in REPLACEMENT_ROLE_ORDER:
        if role not in required_roles:
            continue
        pool = candidate_pools.get(role) or []
        if not pool:
            continue
        candidate = pool[0]
        ingredients.append(
            {
                "ingredient_name": candidate["canonical_name"],
                "quantity": "default serving",
                "role": role,
                "notes": "rule-based short-term replacement",
            }
        )

    if not ingredients:
        ingredients = [
            {"ingredient_name": "chicken_breast", "quantity": "default serving", "role": "protein", "notes": ""},
            {"ingredient_name": "cooked_white_rice", "quantity": "default serving", "role": "carb", "notes": ""},
            {"ingredient_name": "broccoli", "quantity": "default serving", "role": "veg", "notes": ""},
        ]

    return {
        "recipe_name": "Simple balanced replacement",
        "instructions": ["Prepare with simple cooking methods and low added salt."],
        "ingredients": ingredients,
    }


def _comparison(old_profile, new_recipe):
    old_totals = old_profile.get("totals") or {}
    new_totals = _entity_totals(new_recipe)
    old_kcal = _as_float(old_totals.get("kcal"))
    new_kcal = _as_float(new_totals.get("kcal"))
    old_protein = _as_float(old_totals.get("protein_g"))
    new_protein = _as_float(new_totals.get("protein_g"))
    return {
        "old_kcal": round(old_kcal, 1),
        "new_kcal": round(new_kcal, 1),
        "kcal_delta": round(new_kcal - old_kcal, 1),
        "old_protein_g": round(old_protein, 1),
        "new_protein_g": round(new_protein, 1),
        "protein_delta_g": round(new_protein - old_protein, 1),
    }


def _build_response(user, request_id, optimized, totals, targets, constraints, evaluation, title, response_extra=None):
    response = {
        "request_id": str(request_id),
        "meal_plan": optimized,
        "totals": totals,
        "derived_targets": targets,
        "shopping_list": shopping_list(optimized),
        "issues": evaluation["issues"],
        "warnings": evaluation["warnings"],
        "constraint_report": constraints,
    }
    if response_extra:
        response.update(response_extra)
    plan = Plan.objects.create(
        user=user,
        plan_type=Plan.PLAN_NUTRITION,
        title=title,
        payload=response,
    )
    record_audit(
        request_id=request_id,
        domain="nutrition",
        step="final",
        plan=plan,
        payload={
            "issues": response["issues"],
            "warnings": response["warnings"],
            "token_usage": get_token_usage(),
        },
    )
    return response


def _finalize_draft(
    user,
    request_id,
    draft,
    targets,
    constraints,
    options,
    *,
    title="One-day meal plan",
    draft_step="draft",
    response_extra=None,
):
    max_iters = int(options.get("optimizer_iters") or 200)
    record_audit(request_id=request_id, domain="nutrition", step=draft_step, payload={"draft": draft})
    resolved, resolver_warnings = _resolve_draft(draft, constraints)
    optimized, totals = optimize_grams(resolved, targets, constraints=constraints, max_iters=max_iters)
    evaluation = evaluate_meal_plan(optimized, totals, targets, constraints, warnings=resolver_warnings)
    return _build_response(user, request_id, optimized, totals, targets, constraints, evaluation, title, response_extra)


def _fallback_ingredient_for_role(role, preferred, avoided_names):
    alternatives = {
        "protein": ["chicken_breast", "egg", "tofu", "greek_yogurt"],
        "carb": ["cooked_white_rice", "sweet_potato", "oats"],
        "veg": ["broccoli", "spinach", "cucumber"],
        "fat": ["olive_oil", "avocado", "peanut_butter"],
        "fruit": ["banana", "apple"],
    }
    for candidate in [preferred] + alternatives.get(role, []):
        if candidate and not _name_matches_any(candidate, avoided_names):
            return candidate
    return preferred


def _fallback_recipe_name(slot_name, memory):
    avoid_names = (memory or {}).get("avoid_recipe_names") or []
    title = str(slot_name or "meal").title()
    candidates = [
        f"{title} plate",
        f"Fresh {title} bowl",
        f"New {title} menu",
        f"{title} reset meal",
    ]
    for candidate in candidates:
        if not _name_matches_any(candidate, avoid_names):
            return candidate
    return f"{title} option"


def _draft_uses_avoided_recipes(draft, memory):
    avoided = (memory or {}).get("avoid_recipe_names") or []
    if not avoided or not isinstance(draft, dict):
        return False
    meal_plan = draft.get("meal_plan") if isinstance(draft.get("meal_plan"), dict) else draft
    return any(_name_matches_any(name, avoided) for name in _recipe_names(meal_plan))


def _fallback_draft(targets, constraints, memory=None):
    slots = (targets.get("meal_structure") or {}).get("slots") or [{"slot": "breakfast"}, {"slot": "lunch"}]
    memory = memory or {}
    avoided_ingredients = _unique_strings(
        (constraints.get("hard_bans") or [])
        + (memory.get("avoid_ingredient_names") or [])
    )
    meal_templates = {
        "breakfast": [("oats", "carb"), ("egg", "protein"), ("banana", "fruit")],
        "lunch": [("chicken_breast", "protein"), ("cooked_white_rice", "carb"), ("broccoli", "veg")],
        "dinner": [("tofu", "protein"), ("sweet_potato", "carb"), ("spinach", "veg"), ("olive_oil", "fat")],
        "snack": [("greek_yogurt", "protein"), ("apple", "fruit")],
    }
    meals = []
    for slot in slots:
        slot_name = slot.get("slot")
        ingredients = [
            {
                "ingredient_name": _fallback_ingredient_for_role(role, name, avoided_ingredients),
                "quantity": "default",
                "role": role,
                "notes": "",
            }
            for name, role in meal_templates.get(slot_name, meal_templates["lunch"])
        ]
        meals.append(
            {
                "slot": slot_name,
                "title": slot_name.title(),
                "recipes": [
                    {
                        "recipe_name": _fallback_recipe_name(slot_name, memory),
                        "ingredients": ingredients,
                        "instructions": ["Prepare with low added salt and simple cooking methods."],
                    }
                ],
            }
        )
    return {"version": "draft_v1", "mode": "day", "days": [{"day_index": 1, "meals": meals, "draft_notes": []}]}


def _resolve_draft(draft, constraints):
    warnings = []
    for day in draft.get("days", []):
        for meal in day.get("meals", []):
            for recipe in meal.get("recipes", []):
                for ingredient in recipe.get("ingredients", []):
                    role = _canonical_role(ingredient.get("role") or "protein")
                    atom, warning = resolve_ingredient(
                        ingredient.get("canonical_name") or ingredient.get("ingredient_name") or ingredient.get("name"),
                        role=role,
                        constraints=constraints,
                    )
                    if warning:
                        warnings.append(warning)
                    if not atom:
                        continue
                    ingredient["atom_id"] = atom.id
                    ingredient["name"] = atom.canonical_name
                    ingredient["canonical_name"] = atom.canonical_name
                    existing_grams = _as_float(ingredient.get("grams"), 0)
                    ingredient["grams"] = (
                        existing_grams
                        if existing_grams > 0
                        else float(atom.default_serving_g or ROLE_DEFAULT_GRAMS.get(role, 100))
                    )
                    ingredient["role"] = role
    return draft, warnings


def _finalize_recipe_replacement(
    user,
    request_id,
    draft,
    targets,
    constraints,
    options,
    *,
    current_plan,
    target,
    old_recipe,
    role_profile,
    memory,
    candidate_pools,
    used_llm_error=False,
):
    max_iters = int(options.get("optimizer_iters") or 200)
    attempts = [("llm", draft)]
    used_fallback = False
    validation = {"issues": [], "warnings": []}
    resolver_warnings = []
    optimized = None
    totals = None
    replacement_recipe = None

    for source, attempt_draft in attempts:
        working = deepcopy(attempt_draft)
        record_audit(
            request_id=request_id,
            domain="nutrition",
            step=f"recipe_replacement_{source}_draft",
            payload={"draft": working, "short_term_memory": memory},
        )
        resolved, resolver_warnings = _resolve_draft(working, constraints)
        assign_nutrients(resolved)
        calculate_plan_totals(resolved)
        replacement_recipe = _get_recipe_from_plan(resolved, target)
        _tune_recipe_to_profile(replacement_recipe, role_profile)
        assign_nutrients(resolved)
        calculate_plan_totals(resolved)

        optimized, totals = optimize_grams(resolved, targets, constraints=constraints, max_iters=max_iters)
        replacement_recipe = _get_recipe_from_plan(optimized, target)
        validation = _validate_replacement_recipe(replacement_recipe, old_recipe, role_profile, memory)
        if not validation["issues"] or source == "fallback":
            used_fallback = source == "fallback"
            break

        fallback = _replace_recipe(current_plan, target, _fallback_recipe(role_profile, candidate_pools, memory))
        attempts.append(("fallback", fallback))

    evaluation = evaluate_meal_plan(optimized, totals, targets, constraints, warnings=resolver_warnings)
    warnings = _unique_strings(evaluation["warnings"] + validation.get("warnings", []))
    issues = list(evaluation["issues"])
    if validation.get("issues") and used_fallback:
        issues = _unique_strings(issues + validation["issues"])
    if used_fallback or used_llm_error:
        warnings.append("A rule-based replacement was used because the LLM draft failed or was unavailable.")
    evaluation = {"issues": _unique_strings(issues), "warnings": _unique_strings(warnings)}

    response = _build_response(
        user,
        request_id,
        optimized,
        totals,
        targets,
        constraints,
        evaluation,
        "Updated one-day meal plan",
        response_extra={
            "replacement": {
                "scope": "recipe",
                "target": target,
                "reason_code": memory.get("reason_code"),
                "old_recipe_names": memory.get("avoid_recipe_names"),
                "candidate_pools": candidate_pools,
                "validation": validation,
            },
            "comparison": _comparison(role_profile, replacement_recipe),
            "short_term_memory_applied": {
                "avoid_recipes": memory.get("avoid_recipe_names"),
                "avoid_ingredients": memory.get("avoid_ingredient_names"),
                "reason_code": memory.get("reason_code"),
            },
        },
    )
    _remember_nutrition_memory(user, memory, request_id=request_id, target=target)
    return response


def shopping_list(meal_plan):
    items = {}
    for day in meal_plan.get("days", []):
        for meal in day.get("meals", []):
            for recipe in meal.get("recipes", []):
                for ingredient in recipe.get("ingredients", []):
                    atom_id = ingredient.get("atom_id")
                    if not atom_id:
                        continue
                    entry = items.setdefault(
                        atom_id,
                        {
                            "atom_id": atom_id,
                            "name": ingredient.get("name"),
                            "canonical_name": ingredient.get("canonical_name"),
                            "grams": 0.0,
                        },
                    )
                    entry["grams"] += float(ingredient.get("grams") or 0)
    return [{**item, "grams": round(item["grams"], 1)} for item in items.values()]


def generate_nutrition_plan(user, payload):
    token = start_token_usage_tracking()
    try:
        return _generate_nutrition_plan(user, payload)
    finally:
        reset_token_usage_tracking(token)


def _generate_nutrition_plan(user, payload):
    request_id = uuid.uuid4()
    targets = payload.get("derived_targets") or {}
    constraints = payload.get("constraints") or {}
    options = payload.get("options") or {}
    short_term_memory = load_short_term_memory(user, domain=ShortTermMemoryEntry.DOMAIN_NUTRITION)
    constraints = _constraints_for_memory(
        constraints,
        {**short_term_memory, "scope": "plan_generation"},
    )

    prompt = {
        "derived_targets": targets,
        "constraints": constraints,
        "preferences": payload.get("preferences") or {},
        "medical_flags": payload.get("medical_flags") or {},
        "extra_restrictions": payload.get("extra_restrictions") or [],
        "short_term_memory": short_term_memory,
        "avoid_recipe_names": short_term_memory.get("avoid_recipe_names") or [],
        "avoid_ingredient_names": short_term_memory.get("avoid_ingredient_names") or [],
    }
    try:
        draft = generate_json(
            NUTRITION_PLAN_SYSTEM_PROMPT,
            json.dumps(prompt, ensure_ascii=True),
            max_retries=int(options.get("max_llm_retries") or 1),
        )
        if _draft_uses_avoided_recipes(draft, short_term_memory):
            record_audit(
                request_id=request_id,
                domain="nutrition",
                step="short_term_memory_conflict",
                payload={
                    "avoid_recipe_names": short_term_memory.get("avoid_recipe_names") or [],
                    "draft_recipe_names": _recipe_names(draft.get("meal_plan") or draft),
                },
            )
            draft = _fallback_draft(targets, constraints, short_term_memory)
    except ImproperlyConfigured:
        draft = _fallback_draft(targets, constraints, short_term_memory)
    except Exception as exc:
        record_audit(request_id=request_id, domain="nutrition", step="openai_error", payload={"error": str(exc)[:500]})
        draft = _fallback_draft(targets, constraints, short_term_memory)

    return _finalize_draft(user, request_id, draft, targets, constraints, options)


def replace_nutrition_plan(user, payload):
    token = start_token_usage_tracking()
    try:
        return _replace_nutrition_plan(user, payload)
    finally:
        reset_token_usage_tracking(token)


def _replace_nutrition_plan(user, payload):
    request_id = uuid.uuid4()
    scope = str(payload.get("scope") or "").strip().lower()
    replacement_request = deepcopy(payload.get("replacement_request") or {})
    replacement_request = _merge_nutrition_session_memory(
        replacement_request,
        load_short_term_memory(user, domain=ShortTermMemoryEntry.DOMAIN_NUTRITION),
    )
    if not scope:
        scope = str(replacement_request.get("scope") or "plan").strip().lower()
    if scope not in {"plan", "meal", "recipe"}:
        raise ValueError("Replacement scope must be plan, meal, or recipe.")

    current_plan = deepcopy(payload.get("current_plan") or payload.get("meal_plan") or {})
    if not current_plan.get("days"):
        raise ValueError("current_plan is required for nutrition replacement.")

    target = payload.get("target") or {}
    targets = payload.get("derived_targets") or {}
    constraints = _constraints_for_replacement(
        payload.get("constraints") or payload.get("constraint_report") or {},
        replacement_request,
    )
    options = payload.get("options") or {}

    role_profile = None
    memory = None
    candidate_pools = None
    old_recipe = None
    if scope == "recipe":
        day, _ = _get_day(current_plan, target)
        meal, _ = _get_meal(day, target)
        old_recipe, _ = _get_recipe(meal, target)
        role_profile = _role_profile_for_recipe(old_recipe, meal)
        memory = _memory_for_recipe_replace(replacement_request, old_recipe)
        memory["meal_slot"] = meal.get("slot")
        constraints = _constraints_for_memory(constraints, memory)
        candidate_pools = _candidate_pool_for_roles(role_profile, constraints, memory)
    else:
        memory = _session_memory({**replacement_request, "scope": scope})

    prompt = _replacement_prompt(
        payload,
        current_plan,
        constraints,
        scope,
        target,
        replacement_request,
        short_term_memory=memory,
        role_profile=role_profile,
        candidate_pools=candidate_pools,
    )
    prompt_json = json.dumps(prompt, ensure_ascii=True)

    record_audit(
        request_id=request_id,
        domain="nutrition",
        step="replacement_request",
        payload={"scope": scope, "target": target, "replacement_request": replacement_request},
    )

    if scope == "plan":
        try:
            raw = generate_json(
                NUTRITION_PLAN_REPLACEMENT_SYSTEM_PROMPT,
                prompt_json,
                max_retries=int(options.get("max_llm_retries") or 1),
            )
            draft = _extract_plan_draft(raw)
        except Exception as exc:
            record_audit(
                request_id=request_id,
                domain="nutrition",
                step="replacement_openai_error",
                payload={"scope": scope, "error": str(exc)[:500]},
            )
            raise RuntimeError(f"Could not generate nutrition replacement with LLM: {exc}") from exc
    elif scope == "meal":
        try:
            raw = generate_json(
                NUTRITION_MEAL_REPLACEMENT_SYSTEM_PROMPT,
                prompt_json,
                max_retries=int(options.get("max_llm_retries") or 1),
            )
            draft = _replace_meal(current_plan, target, _extract_meal(raw))
        except Exception as exc:
            record_audit(
                request_id=request_id,
                domain="nutrition",
                step="replacement_openai_error",
                payload={"scope": scope, "error": str(exc)[:500]},
            )
            raise RuntimeError(f"Could not generate nutrition replacement with LLM: {exc}") from exc
    else:
        used_llm_error = False
        try:
            raw = generate_json(
                NUTRITION_RECIPE_REPLACEMENT_SYSTEM_PROMPT,
                prompt_json,
                max_retries=int(options.get("max_llm_retries") or 1),
            )
            draft = _replace_recipe(current_plan, target, _extract_recipe(raw))
        except Exception as exc:
            used_llm_error = True
            record_audit(
                request_id=request_id,
                domain="nutrition",
                step="replacement_openai_error",
                payload={"scope": scope, "error": str(exc)[:500]},
            )
            draft = _replace_recipe(current_plan, target, _fallback_recipe(role_profile, candidate_pools, memory))

        return _finalize_recipe_replacement(
            user,
            request_id,
            draft,
            targets,
            constraints,
            options,
            current_plan=current_plan,
            target=target,
            old_recipe=old_recipe,
            role_profile=role_profile,
            memory=memory,
            candidate_pools=candidate_pools,
            used_llm_error=used_llm_error,
        )

    response = _finalize_draft(
        user,
        request_id,
        draft,
        targets,
        constraints,
        options,
        title="Updated one-day meal plan",
        draft_step="replacement_draft",
        response_extra={
            "replacement": {
                "scope": scope,
                "target": target,
                "reason_type": replacement_request.get("reason_type"),
                "reason_detail": replacement_request.get("reason_detail"),
                "old_recipe_names": prompt["replacement_request"]["old_recipe_names"],
            },
            "short_term_memory_applied": {
                "avoid_recipes": memory.get("avoid_recipe_names"),
                "avoid_ingredients": memory.get("avoid_ingredient_names"),
                "reason_code": memory.get("reason_code"),
            },
        },
    )
    _remember_nutrition_memory(user, memory, request_id=request_id, target=target)
    return response
