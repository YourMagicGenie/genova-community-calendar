from scripts.summarize_genova_luzzati_report import summarize


def test_summary_preserves_field_gaps_and_escapes_table_cells():
    report = {'status': 'ok', 'diagnostics': {'candidates': [{
        'title': 'Title | A', 'url': 'https://www.spazio-comune.org/prodotto/a/',
        'coverage': 'detail_fetched', 'http_status': 200,
        'unresolved_reasons': ['year_missing'],
        'fields': {'date_text': ['9 ottobre'], 'explicit_years': [], 'local_times': ['18:00']},
    }]}}
    result = summarize(report)
    assert 'Title \\| A' in result
    assert '9 ottobre' in result
    assert '18:00' in result
    assert 'year_missing' in result
    assert 'detail_fetched / 200' in result


def test_failed_preflight_without_candidates_can_still_be_summarized():
    assert 'Result: skipped' in summarize({'status': 'skipped', 'reason': 'approval missing'})
