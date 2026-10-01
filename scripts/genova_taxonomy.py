"""Normalize inherited event categories to the public Genova taxonomy."""

import json
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
