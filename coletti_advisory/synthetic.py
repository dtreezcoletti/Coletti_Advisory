SYNTHETIC_ENGAGEMENT = {
    "engagement_id": "eng-synthetic-demo",
    "name": "Coletti & Co. Synthetic Demo",
    "status": "ACTIVE",
}

SYNTHETIC_MANIFEST = {
    "sources": {
        "SRC-DEMO-001": {
            "source_id": "SRC-DEMO-001",
            "content_hash": "demo-hash-001",
            "metadata": {"filename": "synthetic_ledger.csv", "classification": "Operational Record"},
        },
        "SRC-DEMO-002": {
            "source_id": "SRC-DEMO-002",
            "content_hash": "demo-hash-002",
            "metadata": {"filename": "synthetic_invoice.pdf", "classification": "Business Record"},
        },
    },
    "source_states": {"SRC-DEMO-001": "CORROBORATED", "SRC-DEMO-002": "DISPUTED"},
    "propositions": {
        "PROP-DEMO-001": {
            "proposition_id": "PROP-DEMO-001",
            "text": "The ledger records a payment on the stated date.",
            "source_ids": ["SRC-DEMO-001"],
        },
        "PROP-DEMO-002": {
            "proposition_id": "PROP-DEMO-002",
            "text": "The invoice records a different amount for the same reference.",
            "source_ids": ["SRC-DEMO-002"],
        },
    },
    "contradictions": {
        "CON-DEMO-001": {
            "contradiction_id": "CON-DEMO-001",
            "proposition_a": "PROP-DEMO-001",
            "proposition_b": "PROP-DEMO-002",
            "reason": "The records disagree on amount and require human review.",
        }
    },
    "escalations": {
        "TASK-DEMO-001": {
            "task_id": "TASK-DEMO-001",
            "subject": "Resolve amount variance",
            "reason": "Two source records conflict.",
            "source_ids": ["SRC-DEMO-001", "SRC-DEMO-002"],
            "status": "OPEN",
        }
    },
    "audit_log": [],
}
