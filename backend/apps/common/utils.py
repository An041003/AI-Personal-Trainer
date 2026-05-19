import re

from unidecode import unidecode


def normalize_text(value):
    value = unidecode(str(value or "")).lower()
    value = re.sub(r"[^a-z0-9_\s-]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def split_csvish(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [part.strip() for part in str(value).replace(";", ",").split(",") if part.strip()]
