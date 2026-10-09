import json
from pathlib import Path

from scripts.genova_taxonomy import normalize_genova_event, suggest_categories


ROOT = Path(__file__).resolve().parents[1]


def test_every_inherited_classifier_label_is_mapped_or_intentionally_excluded():
    taxonomy = json.loads((ROOT / "genova-taxonomy.json").read_text())
    inherited = json.loads((ROOT / "categories.json").read_text())
    mapped = {
        label
        for category in taxonomy["categories"]
        for label in category["inherited_labels"]
    }
    excluded = set(taxonomy["excluded_inherited_labels"])
    assert mapped.isdisjoint(excluded)
    assert mapped | excluded == {category["name"] for category in inherited}


def test_normalizer_maps_multiple_labels_to_public_keys_and_keeps_date_night_tag():
    event = {
        "title": "Maker market with family workshops",
        "category": "Craft / Maker",
        "categories": ["Craft / Maker", "Family / Kids"],
        "classification_confidence": 0.92,
        "tags": ["date-night"],
    }

    result = normalize_genova_event(event)

    assert result["categories"] == ["art-exhibitions", "festivals-markets", "family"]
    assert result["category"] == "art-exhibitions"
    assert result["tags"] == ["date-night"]
    assert result["classification_review"]["status"] == "ready"
    assert event["category"] == "Craft / Maker"


def test_unknown_labels_and_low_confidence_remain_reviewable():
    unknown = normalize_genova_event({"category": "Uncatalogued local gathering"})
    low_confidence = normalize_genova_event(
        {"category": "Music / Concerts", "classification_confidence": 0.42}
    )

    assert unknown["categories"] == []
    assert unknown["source_category_labels"] == ["Uncatalogued local gathering"]
    assert unknown["classification_review"]["status"] == "review"
    assert unknown["classification_review"]["unmapped_labels"] == ["Uncatalogued local gathering"]
    assert low_confidence["categories"] == ["music"]
    assert low_confidence["classification_review"]["status"] == "review"
    assert "low_confidence" in low_confidence["classification_review"]["reasons"]


def test_mapped_classification_without_confidence_is_still_reviewable():
    result = normalize_genova_event({"category": "Music / Concerts"})

    assert result["categories"] == ["music"]
    assert result["classification_review"]["status"] == "review"
    assert "confidence_missing" in result["classification_review"]["reasons"]


def test_boolean_confidence_is_invalid_and_cannot_publish_an_event():
    for confidence in (True, False):
        result = normalize_genova_event(
            {"category": "Music / Concerts", "classification_confidence": confidence}
        )

        assert result["classification_review"]["status"] == "review"
        assert "invalid_confidence" in result["classification_review"]["reasons"]


def test_normalizing_an_event_twice_preserves_unknown_source_labels():
    event = normalize_genova_event(
        {
            "category": "Music / Concerts",
            "categories": ["Uncatalogued local gathering"],
            "classification_confidence": 0.95,
        }
    )

    normalized_again = normalize_genova_event(event)

    assert normalized_again["source_category_labels"] == [
        "Music / Concerts",
        "Uncatalogued local gathering",
    ]
    assert normalized_again["classification_review"]["status"] == "review"
    assert normalized_again["classification_review"]["unmapped_labels"] == [
        "Uncatalogued local gathering"
    ]


def test_normalizing_an_event_twice_preserves_excluded_and_mixed_labels():
    excluded = normalize_genova_event(
        {"category": "Government / Civic", "classification_confidence": 0.95}
    )
    mixed = normalize_genova_event(
        {
            "category": "Music / Concerts",
            "categories": ["Government / Civic"],
            "classification_confidence": 0.95,
        }
    )

    excluded_again = normalize_genova_event(excluded)
    mixed_again = normalize_genova_event(mixed)

    assert excluded_again["classification_review"]["status"] == "excluded"
    assert excluded_again["classification_review"]["excluded_labels"] == ["Government / Civic"]
    assert mixed_again["classification_review"]["status"] == "review"
    assert mixed_again["classification_review"]["excluded_labels"] == ["Government / Civic"]


def test_known_exclusion_is_explicit_and_not_silently_discarded():
    result = normalize_genova_event({"category": "Government / Civic"})

    assert result["categories"] == []
    assert result["source_category_labels"] == ["Government / Civic"]
    assert result["classification_review"]["status"] == "excluded"
    assert result["classification_review"]["excluded_labels"] == ["Government / Civic"]


def test_shared_suggester_returns_overlapping_categories_with_confidence_and_safe_evidence():
    suggestions = suggest_categories(
        title="Concerto jazz e performance teatrale",
        section="Festival",
        text="Una serata con musica dal vivo e teatro.",
        venue="Giardini Luzzati",
    )

    keys = {suggestion["category"] for suggestion in suggestions}
    assert {"music", "theatre-performance", "festivals-markets"} <= keys
    assert all(0 <= suggestion["confidence"] <= 1 for suggestion in suggestions)
    assert all(suggestion["evidence"] and len(suggestion["evidence"]) <= 160 for suggestion in suggestions)
    assert "Concerto jazz" not in str(suggestions)


def test_shared_suggester_uses_section_and_structured_category_context():
    suggestions = suggest_categories(
        title="Incontro di quartiere",
        section="Attività per famiglie",
        structured_categories=["Craft / Maker"],
    )

    keys = {suggestion["category"] for suggestion in suggestions}
    assert {"family", "art-exhibitions", "festivals-markets"} <= keys
    assert any("section heading match" in suggestion["evidence"] for suggestion in suggestions)


def test_shared_suggester_returns_low_confidence_best_guess_for_weak_evidence():
    suggestions = suggest_categories(title="Un evento speciale")

    assert suggestions == [{
        "category": "community-social",
        "confidence": 0.2,
        "evidence": "low-confidence fallback; no category-specific cue found",
    }]
    assert suggest_categories() == []
