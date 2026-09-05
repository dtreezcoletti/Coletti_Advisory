from coletti_advisory.document_processing import extract_candidate_statements


def test_plain_text_extraction_creates_review_candidates_without_interpretation():
    result = extract_candidate_statements(
        "record.txt",
        b"Invoice total is $120.00.\nPayment date is 2026-09-01.\n",
    )
    assert result.extraction_method == "plain-text"
    assert len(result.candidates) == 2
    assert result.candidates[0].text == "Invoice total is $120.00."
    assert result.candidates[0].locator == "line 1"
    assert result.candidates[0].candidate_id.startswith("CAND-")


def test_csv_extraction_preserves_rows_as_source_derived_candidates():
    result = extract_candidate_statements(
        "ledger.csv",
        b"date,amount,reference\n2026-09-01,120.00,INV-44\n",
    )
    assert result.extraction_method == "csv-row"
    assert [candidate.locator for candidate in result.candidates] == ["row 1", "row 2"]
    assert result.candidates[1].text == "2026-09-01 | 120.00 | INV-44"


def test_json_extraction_flattens_scalar_paths_without_claiming_truth():
    result = extract_candidate_statements(
        "record.json",
        b'{"invoice":{"amount":120,"status":"open"}}',
    )
    texts = {candidate.text for candidate in result.candidates}
    assert '$.invoice.amount = 120' in texts
    assert '$.invoice.status = "open"' in texts


def test_unsupported_format_registers_warning_not_fake_candidates():
    result = extract_candidate_statements("image.png", b"not really an image")
    assert result.extraction_method == "unsupported"
    assert result.candidates == ()
    assert result.warnings
