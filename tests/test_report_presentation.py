from coletti_advisory.report_presentation import responsive_table_html, summary_items


def test_responsive_report_table_includes_mobile_data_labels():
    html = responsive_table_html(
        [
            {
                "Issue": "CON-DEMO-001",
                "Classification": "Inconsistency",
                "Description": "The records disagree on amount.",
            }
        ]
    )
    assert "cc-report-table" in html
    assert "data-label='Issue'" in html
    assert "data-label='Description'" in html
    assert "The records disagree on amount." in html


def test_report_table_escapes_untrusted_cell_content():
    html = responsive_table_html([{"Detail": "<script>alert('x')</script>"}])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_engagement_summary_labels_are_client_readable():
    items = dict(
        summary_items(
            {
                "sources": 2,
                "propositions": 3,
                "inconsistencies": 1,
                "open_issues": 1,
            }
        )
    )
    assert items == {
        "Sources": "2",
        "Record statements": "3",
        "Inconsistencies": "1",
        "Open issues": "1",
    }
