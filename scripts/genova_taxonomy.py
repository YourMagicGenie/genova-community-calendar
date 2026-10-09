"""Normalize inherited event categories to the public Genova taxonomy."""

import json
import re
import unicodedata
from pathlib import Path


TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "genova-taxonomy.json"
with TAXONOMY_PATH.open(encoding="utf-8") as taxonomy_file:
    TAXONOMY = json.load(taxonomy_file)

CATEGORY_BY_KEY = {category["key"]: category for category in TAXONOMY["categories"]}
INHERITED_LABELS = {}
for category in TAXONOMY["categories"]:
    for inherited_label in category["inherited_labels"]:
        INHERITED_LABELS.setdefault(inherited_label, []).append(category["key"])
EXCLUDED_LABELS = set(TAXONOMY["excluded_inherited_labels"])
REVIEW_THRESHOLD = TAXONOMY["classification_review_threshold"]

# Small, deterministic cues are intentionally shared by web-page adapters and
# document parsers. These are category signals, not source-specific rules.
CATEGORY_KEYWORDS = {
    "music": ("musica", "musicale", "concerto", "concerti", "jazz", "dj set", "live music"),
    "theatre-performance": ("teatro", "spettacolo", "performance", "danza", "cabaret", "commedia", "play"),
    "art-exhibitions": ("mostra", "mostre", "esposizione", "arte", "fotografia", "cinema", "film", "proiezione", "documentario"),
    "sports": ("sport", "partita", "torneo", "fitness", "allenamento", "gara"),
    "food-drink": ("degustazione", "cucina", "vino", "birra", "aperitivo", "cena", "street food"),
    "festivals-markets": ("festival", "mercato", "mercatino", "fiera", "sagra", "market"),
    "talks-workshops": ("laboratorio", "workshop", "corso", "conferenza", "presentazione", "poesia", "lettura", "libro", "book", "autore", "scrittore", "dibattito"),
    "family": ("bambini", "famiglie", "per bambini", "family", "kids"),
    "outdoors-tours": ("escursione", "trekking", "passeggiata", "visita guidata", "tour", "natura", "outdoor"),
    "community-social": ("comunita", "socialita", "giochi", "ritrovo", "social gathering", "community"),
}

CATEGORY_ALIASES = {
    "music": "music", "musica": "music", "concerti": "music", "music / concerts": "music",
    "theatre": "theatre-performance", "theater": "theatre-performance", "teatro": "theatre-performance",
    "performance": "theatre-performance", "theatre & performance": "theatre-performance",
    "art": "art-exhibitions", "arte": "art-exhibitions", "mostre": "art-exhibitions",
    "art & exhibitions": "art-exhibitions", "sport": "sports", "sports": "sports",
    "food": "food-drink", "food & drink": "food-drink", "festival": "festivals-markets",
    "festivals": "festivals-markets", "mercati": "festivals-markets", "festivals & markets": "festivals-markets",
    "talks": "talks-workshops", "workshops": "talks-workshops", "laboratori": "talks-workshops",
    "talks & workshops": "talks-workshops", "family": "family", "famiglie": "family",
    "bambini": "family", "family & kids": "family", "outdoors": "outdoors-tours",
    "tours": "outdoors-tours", "outdoor & tours": "outdoors-tours",
    "community": "community-social", "comunita": "community-social", "community & social": "community-social",
}


def _fold_text(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _category_key(value):
    if not isinstance(value, str):
        return None
    label = value.strip()
    if label in CATEGORY_BY_KEY:
        return label
    if label in INHERITED_LABELS:
        return INHERITED_LABELS[label][0]
    folded = _fold_text(label)
    if folded in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[folded]
    return None


def suggest_categories(*, title=None, text=None, section=None, venue=None, structured_categories=None):
    """Suggest stable taxonomy keys with confidence and concise evidence.

    Inputs are transient source facts. The result contains only category keys,
    confidence values, and generic evidence summaries; it never copies source
    prose. Callers may pass the same fields from a web page or a PDF parser.
    """
    title_text = _fold_text(title) if isinstance(title, str) else ""
    text_value = _fold_text(text) if isinstance(text, str) else ""
    section_text = _fold_text(section) if isinstance(section, str) else ""
    venue_text = _fold_text(venue) if isinstance(venue, str) else ""
    scores = {}
    evidence = {}

    def add(key, points, reason):
        if key not in CATEGORY_BY_KEY:
            return
        scores[key] = scores.get(key, 0) + points
        evidence.setdefault(key, set()).add(reason)

    if isinstance(structured_categories, (list, tuple)):
        structured_keys = set()
        for label in structured_categories:
            key = _category_key(label)
            if key:
                structured_keys.add(key)
            if isinstance(label, str):
                structured_keys.update(INHERITED_LABELS.get(label, []))
        for key in structured_keys:
            add(key, 5, "structured category metadata")

    for category, phrases in CATEGORY_KEYWORDS.items():
        for phrase in phrases:
            needle = _fold_text(phrase)
            pattern = re.compile(r"(?<!\w)" + re.escape(needle) + r"(?!\w)")
            if pattern.search(title_text):
                add(category, 3, "title keyword match")
            if pattern.search(section_text):
                add(category, 4, "section heading match")
            if pattern.search(text_value):
                add(category, 1, "event text keyword match")
            if pattern.search(venue_text):
                add(category, 1, "venue keyword match")

    if not scores:
        if not any((title_text, text_value, section_text, venue_text)):
            return []
        # A visible low-confidence fallback lets reviewers see the uncertain
        # best guess. It never changes the event's review/publication status.
        return [{
            "category": "community-social",
            "confidence": 0.2,
            "evidence": "low-confidence fallback; no category-specific cue found",
        }]

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    selected = [item for item in ranked if item[1] >= 2][:3]
    if not selected:
        selected = ranked[:1]
    return [
        {
            "category": key,
            "confidence": round(min(0.98, 0.45 + score * 0.1), 2),
            "evidence": "; ".join(sorted(evidence[key])),
        }
        for key, score in selected
    ]


def normalize_genova_event(event):
    """Return a copy using stable Genova keys and an explicit review status.

    The inherited ``category`` text and optional ``categories`` list are
    retained in ``source_category_labels``. Unknown labels are never dropped.
    """
    normalized = dict(event)
    source_labels = event.get("source_category_labels")
    raw_values = (
        [value for value in source_labels if isinstance(value, str) and value.strip()]
        if isinstance(source_labels, list)
        else []
    )
    already_mapped_keys = set()
    for value in raw_values:
        if value in CATEGORY_BY_KEY:
            already_mapped_keys.add(value)
        else:
            already_mapped_keys.update(INHERITED_LABELS.get(value, []))
    if isinstance(event.get("category"), str) and event["category"].strip():
        if event["category"] not in already_mapped_keys:
            raw_values.append(event["category"])
    if isinstance(event.get("categories"), list):
        raw_values.extend(
            value
            for value in event["categories"]
            if isinstance(value, str) and value.strip() and value not in already_mapped_keys
        )
    raw_labels = list(dict.fromkeys(value for value in raw_values if isinstance(value, str) and value.strip()))

    category_keys = []
    unmapped_labels = []
    excluded_labels = []
    for value in raw_labels:
        if value in CATEGORY_BY_KEY:
            mapped = [value]
        elif value in INHERITED_LABELS:
            mapped = INHERITED_LABELS[value]
        elif value in EXCLUDED_LABELS:
            excluded_labels.append(value)
            continue
        else:
            unmapped_labels.append(value)
            continue
        for key in mapped:
            if key not in category_keys:
                category_keys.append(key)

    confidence = event.get("classification_confidence")
    reasons = []
    if not raw_labels:
        reasons.append("category_missing")
    if unmapped_labels:
        reasons.append("unmapped_category")
    if confidence is None:
        reasons.append("confidence_missing")
    elif (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0 <= confidence <= 1
    ):
        reasons.append("invalid_confidence")
    elif confidence < REVIEW_THRESHOLD:
        reasons.append("low_confidence")
    if excluded_labels and category_keys:
        reasons.append("mixed_excluded_and_public_labels")

    if excluded_labels and not category_keys and not unmapped_labels:
        status = "excluded"
    elif reasons:
        status = "review"
    else:
        status = "ready"

    normalized["source_category_labels"] = raw_labels
    normalized["categories"] = category_keys
    normalized["category"] = category_keys[0] if category_keys else None
    normalized["classification_review"] = {
        "status": status,
        "reasons": reasons,
        "unmapped_labels": unmapped_labels,
        "excluded_labels": excluded_labels,
        "confidence": confidence,
    }
    return normalized
