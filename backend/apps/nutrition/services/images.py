import json
import re
import time
from copy import deepcopy
from functools import lru_cache
from urllib import parse, request
from urllib.error import HTTPError, URLError


COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
OPENVERSE_API_URL = "https://api.openverse.org/v1/images/"
USER_AGENT = "AI-Personal-Trainer/0.1 local-development"
ENRICH_TIME_BUDGET_SEC = 8
GENERIC_RECIPE_WORDS = {
    "plate",
    "bowl",
    "menu",
    "meal",
    "dish",
    "side",
    "staple",
    "protein",
    "vegetable",
    "fresh",
    "simple",
    "breakfast",
    "lunch",
    "dinner",
    "snack",
}


def _clean_html(value):
    return re.sub(r"<[^>]+>", "", str(value or "")).strip()


def _display_name(value):
    return str(value or "").replace("_", " ").replace("-", " ").strip()


def _valid_llm_image_url(value):
    text = str(value or "").strip()
    if not text.lower().startswith("https://"):
        return ""
    parsed = parse.urlparse(text)
    if not parsed.netloc or "." not in parsed.netloc:
        return ""
    return text


def _recipe_ingredient_names(recipe):
    names = []
    for ingredient in recipe.get("ingredients") or []:
        name = (
            ingredient.get("canonical_name")
            or ingredient.get("name")
            or ingredient.get("ingredient_name")
        )
        if name:
            names.append(_display_name(name))
    return names


def _recipe_search_queries(recipe):
    recipe_name = _display_name(recipe.get("recipe_name"))
    image_query = _display_name(recipe.get("image_search_query"))
    ingredients = _recipe_ingredient_names(recipe)
    words = {word.lower() for word in re.findall(r"[a-zA-Z]+", recipe_name)}
    name_is_generic = not recipe_name or len(words - GENERIC_RECIPE_WORDS) <= 1

    queries = []
    if image_query:
        queries.append(image_query)
    if recipe_name and not name_is_generic:
        queries.append(f"{recipe_name} food")
    if ingredients:
        queries.append(f"{' '.join(ingredients[:3])} food dish")
    if recipe_name:
        queries.append(recipe_name)
    return list(dict.fromkeys(queries))


def _image_score(title):
    normalized = title.lower()
    bad_terms = ["logo", "icon", "diagram", "map", "chart", "symbol", "raw", "uncooked"]
    score = 0
    for term in bad_terms:
        if term in normalized:
            score -= 5
    for term in ["food", "dish", "meal", "cooked", "salad", "soup", "rice", "chicken", "egg"]:
        if term in normalized:
            score += 1
    return score


@lru_cache(maxsize=256)
def _search_openverse_image(query):
    params = {
        "format": "json",
        "q": query,
        "page_size": "12",
        "mature": "false",
    }
    url = f"{OPENVERSE_API_URL}?{parse.urlencode(params)}"
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with request.urlopen(req, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    candidates = []
    for item in payload.get("results") or []:
        image_url = item.get("thumbnail") or item.get("url")
        if not image_url:
            continue
        title = item.get("title") or ""
        candidates.append(
            {
                "url": image_url,
                "source": f"Openverse/{item.get('source')}" if item.get("source") else "Openverse",
                "source_url": item.get("foreign_landing_url") or item.get("url"),
                "title": title,
                "license": item.get("license") or item.get("license_version") or "",
                "artist": item.get("creator") or "",
                "score": _image_score(title),
            }
        )

    if not candidates:
        return None
    candidates.sort(key=lambda item: item["score"], reverse=True)
    selected = candidates[0]
    selected.pop("score", None)
    return selected


@lru_cache(maxsize=256)
def _search_commons_image(query):
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrlimit": "8",
        "gsrsearch": query,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": "480",
    }
    url = f"{COMMONS_API_URL}?{parse.urlencode(params)}"
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with request.urlopen(req, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    pages = (payload.get("query") or {}).get("pages") or {}
    candidates = []
    for page in pages.values():
        imageinfo = (page.get("imageinfo") or [{}])[0]
        mime = str(imageinfo.get("mime") or "")
        if not mime.startswith("image/") or mime == "image/svg+xml":
            continue
        image_url = imageinfo.get("thumburl") or imageinfo.get("url")
        if not image_url:
            continue
        title = page.get("title") or ""
        metadata = imageinfo.get("extmetadata") or {}
        candidates.append(
            {
                "url": image_url,
                "source": "Wikimedia Commons",
                "source_url": imageinfo.get("descriptionurl"),
                "title": title.replace("File:", ""),
                "license": _clean_html((metadata.get("LicenseShortName") or {}).get("value")),
                "artist": _clean_html((metadata.get("Artist") or {}).get("value")),
                "score": _image_score(title),
            }
        )

    if not candidates:
        return None
    candidates.sort(key=lambda item: item["score"], reverse=True)
    selected = candidates[0]
    selected.pop("score", None)
    return selected


def enrich_nutrition_payload(payload):
    enriched = deepcopy(payload or {})
    meal_plan = enriched.get("meal_plan") if isinstance(enriched.get("meal_plan"), dict) else enriched
    if not isinstance(meal_plan, dict):
        return enriched

    deadline = time.monotonic() + ENRICH_TIME_BUDGET_SEC
    for day in meal_plan.get("days") or []:
        for meal in day.get("meals") or []:
            for recipe in meal.get("recipes") or []:
                if time.monotonic() > deadline:
                    return enriched
                llm_image_url = _valid_llm_image_url(recipe.get("image_url"))
                if llm_image_url:
                    recipe["image_url"] = llm_image_url
                    recipe.setdefault(
                        "image",
                        {
                            "url": llm_image_url,
                            "source": "LLM provided image URL",
                            "source_url": llm_image_url,
                            "title": recipe.get("recipe_name") or "",
                            "license": "",
                            "artist": "",
                        },
                    )
                    continue
                recipe.pop("image_url", None)
                if (recipe.get("image") or {}).get("url"):
                    continue
                for query in _recipe_search_queries(recipe):
                    image = _search_openverse_image(query) or _search_commons_image(query)
                    if image:
                        recipe["image_url"] = image["url"]
                        recipe["image"] = image
                        break
    return enriched
