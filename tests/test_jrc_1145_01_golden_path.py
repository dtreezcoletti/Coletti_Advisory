from coletti_advisory.golden_path import JRC_CASE_ID, run_jrc_1145_01_delivery


def test_jrc_1145_01_builds_all_reports_and_never_auto_publishes():
    result = run_jrc_1145_01_delivery()

    assert result.case_id == JRC_CASE_ID
    assert len(result.report_types) == 3
    assert result.human_review_staged is True
    assert result.exact_report_publication_invoked is False
    assert result.published_report_types == ()

    assert set(result.report_fingerprints) == set(result.report_types)
    assert all(len(value) == 64 for value in result.report_fingerprints.values())

    # The controlled fixture contains a known unresolved variance. The client
    # report may be reviewed/approved as a faithful unresolved reconstruction,
    # but publication is still a separate explicit action.
    assert all(
        status in {"REVIEW REQUIRED", "READY FOR FINAL HUMAN APPROVAL"}
        for status in result.publication_gate_statuses.values()
    )

    for record in result.publication_records.values():
        assert record["status"].value == "APPROVED"
        assert record["published_snapshot"] is None
        assert record["published_by"] is None
        assert record["published_at"] is None


def test_jrc_1145_01_report_fingerprints_are_repeatable():
    first = run_jrc_1145_01_delivery()
    second = run_jrc_1145_01_delivery()

    assert first.report_types == second.report_types
    assert first.report_fingerprints == second.report_fingerprints
    assert first.published_report_types == second.published_report_types == ()
