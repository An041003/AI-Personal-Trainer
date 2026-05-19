from rapidfuzz import process

from apps.common.utils import normalize_text
from apps.nutrition.models import NutritionAtom


FALLBACK_BY_ROLE = {
    "protein": ["chicken_breast", "egg", "tofu"],
    "carb": ["cooked_white_rice", "sweet_potato", "oats"],
    "fat": ["olive_oil", "avocado", "peanut_butter"],
    "veg": ["broccoli", "spinach", "cucumber"],
    "fruit": ["banana", "apple"],
}


def _is_banned(atom, hard_bans):
    haystack = normalize_text(" ".join([atom.canonical_name, atom.display_name_vi, atom.aliases]))
    return any(normalize_text(ban) in haystack for ban in hard_bans or [])


def fallback_atom(role, hard_bans):
    for canonical in FALLBACK_BY_ROLE.get(role, []) + FALLBACK_BY_ROLE["protein"]:
        atom = NutritionAtom.objects.filter(canonical_name=canonical, is_active=True).first()
        if atom and not _is_banned(atom, hard_bans):
            return atom
    return NutritionAtom.objects.filter(is_active=True).first()


def resolve_ingredient(name, role=None, constraints=None):
    constraints = constraints or {}
    hard_bans = constraints.get("hard_bans") or []
    normalized = normalize_text(name)

    candidates = NutritionAtom.objects.filter(is_active=True)
    exact = candidates.filter(canonical_name=normalized).first()
    if exact and not _is_banned(exact, hard_bans):
        return exact, None

    alias = candidates.filter(aliases__icontains=normalized).first()
    if alias and not _is_banned(alias, hard_bans):
        return alias, None

    contains = candidates.filter(display_name_vi__icontains=name).first()
    if contains and not _is_banned(contains, hard_bans):
        return contains, None

    choices = {
        atom.canonical_name: atom
        for atom in candidates
        if not _is_banned(atom, hard_bans)
    }
    if choices:
        match = process.extractOne(normalized, choices.keys(), score_cutoff=80)
        if match:
            return choices[match[0]], None

    fallback = fallback_atom(role or "protein", hard_bans)
    warning = f"Ingredient '{name}' was replaced by fallback '{fallback.canonical_name}'." if fallback else f"Unresolved ingredient '{name}'."
    return fallback, warning

