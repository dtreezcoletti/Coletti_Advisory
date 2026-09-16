from coletti_advisory.owner_docket_surface import _allowed_targets, _documents


def test_docket_transition_targets_are_fail_closed():
    assert _allowed_targets("WORKING_DRAFT") == ("DRAFT",)
    assert _allowed_targets("DRAFT") == ("MASTER", "RETIRED")
    assert _allowed_targets("MASTER") == ("SUPERSEDED", "RETIRED")
    assert _allowed_targets("SUPERSEDED") == ()
    assert _allowed_targets("RETIRED") == ()
    assert _allowed_targets("unknown") == ()


def test_docket_documents_accepts_only_mapping_rows():
    snapshot = {
        "documents": [
            {"document_key": "CCO-FTL-001", "document_state": "MASTER"},
            "bad-row",
            None,
        ]
    }
    assert _documents(snapshot) == [
        {"document_key": "CCO-FTL-001", "document_state": "MASTER"}
    ]
    assert _documents(None) == []
    assert _documents({"documents": "not-a-list"}) == []
