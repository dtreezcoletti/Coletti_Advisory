from coletti_advisory.record_vocabulary import (
    display_label,
    display_page_label,
    display_rows,
)


def test_legacy_internal_route_displays_as_records():
    assert display_page_label("Evidence") == "Records"
    assert display_page_label("Analysis") == "Analysis"


def test_source_lifecycle_label_does_not_collide_with_first_truth_record_state():
    assert display_label("Evidence State") == "Source State"
    assert display_label("Evidence State Summary") == "Source State Summary"
    assert display_label("Evidence Passport") == "Record Passport"


def test_table_translation_preserves_values_and_changes_only_visible_keys():
    rows = [{"Evidence state": "CORROBORATED", "Source": "SRB-001"}]
    translated = display_rows(rows)
    assert translated == [{"Source state": "CORROBORATED", "Source": "SRB-001"}]
    assert rows == [{"Evidence state": "CORROBORATED", "Source": "SRB-001"}]
