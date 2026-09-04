"""Coletti & Co. financial reconstruction adapter.

This module is a commercial-facing adapter. It contains no real client or
historical case facts. Default data is explicitly synthetic and exists only to
keep demonstration/UI paths functional during migration.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List


class ForensicEngine:
    """Configurable financial reconstruction and variance engine.

    The engine compares documented baselines with documented financial inputs.
    It does not independently determine fraud, concealment, liability, or legal
    significance. Those are reviewer/professional determinations.
    """

    VERSION = "3.0.0-migration"
    SYSTEM_ID = "ColettiCo_FinancialReconstruction_v3"

    def __init__(
        self,
        *,
        engagement_id: str = "SYNTH-DEMO-001",
        engagement_name: str = "Synthetic Financial Reconstruction",
        jurisdiction: str = "Synthetic / Demonstration",
        analyst_attribution: str = "Coletti & Co.",
        analysis_start_date: str = "2025-01-01",
        analysis_end_date: str = "2025-12-31",
        tracking_months: int = 12,
        demo_mode: bool = True,
    ):
        self.analyst_attribution = analyst_attribution
        self.case_number = engagement_id  # legacy UI compatibility
        self.case_name = engagement_name  # legacy UI compatibility
        self.court = jurisdiction  # legacy UI compatibility
        self.analysis_start_date = analysis_start_date
        self.analysis_end_date = analysis_end_date
        self.tracking_months = tracking_months

        self.sworn_data: dict = {}
        self.income_sources: Dict[str, dict] = {}
        self.assets_discovered: Dict[str, dict] = {}
        self.variance_analysis: dict = {}
        self.cumulative_impact: dict = {}
        self.comparative_economics: dict = {}
        self.audit_trail: List[dict] = []

        self._log("System initialized", {"engagement": self.case_number, "demo_mode": demo_mode})
        if demo_mode:
            self._seed_synthetic_demo()

    # ------------------------------------------------------------------
    # Configuration / synthetic demo
    # ------------------------------------------------------------------

    def set_baseline(
        self,
        *,
        monthly_net_income: float,
        monthly_gross_income: float | None = None,
        annual_gross_income: float | None = None,
        claimed_monthly_deficit: float | None = None,
        source: str,
        source_id: str,
        baseline_date: str | None = None,
    ) -> None:
        if not source_id.strip():
            raise ValueError("Baseline requires a source_id")
        self.sworn_data = {
            "monthly_net_income": float(monthly_net_income),
            "monthly_gross_income": float(monthly_gross_income or 0.0),
            "annual_gross_income": float(annual_gross_income or 0.0),
            "claimed_monthly_deficit": claimed_monthly_deficit,
            "affidavit_date": baseline_date,
            "source": source,
            "source_id": source_id,
        }
        self._log("Baseline configured", {"source_id": source_id})

    def _seed_synthetic_demo(self) -> None:
        """Load fabricated demonstration data only."""
        self.set_baseline(
            monthly_net_income=4200.00,
            monthly_gross_income=5600.00,
            annual_gross_income=67200.00,
            claimed_monthly_deficit=-450.00,
            source="Synthetic baseline statement",
            source_id="SYN-SOURCE-001",
            baseline_date="2025-02-15",
        )
        self.ingest_income_source(
            source_name="Synthetic Employer W-2",
            annual_amount=96000.00,
            source_type="W2",
            documentation="Synthetic test fixture",
            discovered_date="2025-03-01",
            source_id="SYN-SOURCE-002",
        )
        self.ingest_income_source(
            source_name="Synthetic Contract Income",
            annual_amount=18000.00,
            source_type="1099",
            documentation="Synthetic test fixture",
            discovered_date="2025-03-02",
            source_id="SYN-SOURCE-003",
        )
        self.ingest_asset(
            asset_name="Synthetic Savings Account",
            asset_type="Account",
            market_value=12000.00,
            documentation="Synthetic test fixture",
            disclosed=False,
            source_id="SYN-SOURCE-004",
        )
        self.calculate_variance(actual_monthly_net=7600.00)
        self.calculate_cumulative_impact(months=self.tracking_months)
        self.analyze_economic_disparity(
            comparison_name="Synthetic Comparison Business",
            comparison_months=24,
            comparison_net=48000.00,
        )

    # ------------------------------------------------------------------
    # Income reconstruction
    # ------------------------------------------------------------------

    def ingest_income_source(
        self,
        source_name: str,
        annual_amount: float,
        source_type: str,
        documentation: str,
        discovered_date: str | None = None,
        source_id: str | None = None,
    ) -> str:
        source_id = source_id or f"SOURCE_{len(self.income_sources) + 1:02d}"
        if source_id in self.income_sources:
            raise ValueError(f"Duplicate income source ID: {source_id}")
        self.income_sources[source_id] = {
            "name": source_name,
            "annual_gross": float(annual_amount),
            "monthly_gross": float(annual_amount) / 12,
            "source_type": source_type,
            "documentation": documentation,
            "discovered_date": discovered_date or datetime.now().strftime("%Y-%m-%d"),
            "source_id": source_id,
            "evidence_status": "DOCUMENTED_INPUT",
        }
        self._log("Income source ingested", {"source_id": source_id, "annual": annual_amount})
        return source_id

    def reconstruct_total_income(self) -> dict:
        total_annual = sum(s["annual_gross"] for s in self.income_sources.values())
        return {
            "total_annual_gross": total_annual,
            "total_monthly_gross": total_annual / 12 if total_annual else 0.0,
            "estimated_annual_net": total_annual * 0.80,
            "estimated_monthly_net": (total_annual * 0.80) / 12 if total_annual else 0.0,
            "source_count": len(self.income_sources),
            "sources_breakdown": {
                sid: {
                    "name": d["name"],
                    "annual": d["annual_gross"],
                    "monthly": d["monthly_gross"],
                    "type": d["source_type"],
                    "documentation": d["documentation"],
                    "source_id": sid,
                }
                for sid, d in self.income_sources.items()
            },
        }

    # ------------------------------------------------------------------
    # Asset inventory
    # ------------------------------------------------------------------

    def ingest_asset(
        self,
        asset_name: str,
        asset_type: str,
        market_value: float,
        equity_value: float | None = None,
        documentation: str | None = None,
        disclosed: bool = False,
        source_id: str | None = None,
    ) -> str:
        asset_id = f"ASSET_{len(self.assets_discovered) + 1:02d}"
        if not source_id:
            raise ValueError("Asset ingestion requires source_id")
        self.assets_discovered[asset_id] = {
            "name": asset_name,
            "type": asset_type,
            "market_value": float(market_value),
            "equity_value": float(equity_value if equity_value is not None else market_value),
            "documentation": documentation,
            "source_id": source_id,
            "disclosed_in_baseline": bool(disclosed),
            "requires_reconciliation": not disclosed,
            # Legacy compatibility only; this is not a system finding.
            "concealed": not disclosed,
        }
        self._log("Asset ingested", {"asset_id": asset_id, "source_id": source_id})
        return asset_id

    def asset_summary(self) -> dict:
        all_assets = list(self.assets_discovered.values())
        unresolved = [a for a in all_assets if a["requires_reconciliation"]]
        return {
            "total_count": len(all_assets),
            "total_market_value": sum(a["market_value"] for a in all_assets),
            "total_equity_value": sum(a["equity_value"] for a in all_assets),
            "concealed_count": len(unresolved),  # legacy UI key
            "concealed_equity_value": sum(a["equity_value"] for a in unresolved),
            "disclosed_count": len(all_assets) - len(unresolved),
            "requires_reconciliation_count": len(unresolved),
        }

    # ------------------------------------------------------------------
    # Variance / impact
    # ------------------------------------------------------------------

    def calculate_variance(self, actual_monthly_net: float | None = None) -> dict:
        if not self.sworn_data:
            raise ValueError("Configure a documented baseline before variance analysis")
        if actual_monthly_net is None:
            actual_monthly_net = self.reconstruct_total_income()["estimated_monthly_net"]

        baseline = float(self.sworn_data["monthly_net_income"])
        delta = float(actual_monthly_net) - baseline
        self.variance_analysis = {
            "sworn_monthly_net": baseline,  # legacy UI key
            "baseline_monthly_net": baseline,
            "actual_monthly_net": float(actual_monthly_net),
            "monthly_concealment_delta": delta,  # legacy UI key; not a finding
            "monthly_variance_delta": delta,
            "concealment_percentage": (delta / baseline * 100) if baseline else 0.0,
            "variance_percentage": (delta / baseline * 100) if baseline else 0.0,
            "sworn_annual_net": baseline * 12,
            "actual_annual_net": float(actual_monthly_net) * 12,
            "annual_concealment_delta": delta * 12,  # legacy UI key
            "annual_variance_delta": delta * 12,
            "interpretation_status": "REQUIRES_HUMAN_REVIEW",
        }
        self._log("Variance analysis computed", {"monthly_delta": delta})
        return self.variance_analysis

    def calculate_cumulative_impact(
        self,
        months: int | None = None,
        proper_support_rate: float = 0.35,
        court_ordered_support: float = 1300.00,
    ) -> dict:
        months = months or self.tracking_months
        if not self.variance_analysis:
            self.calculate_variance()
        actual_monthly_net = self.variance_analysis["actual_monthly_net"]
        baseline_monthly_net = self.variance_analysis["baseline_monthly_net"]
        monthly_variance = self.variance_analysis["monthly_variance_delta"]
        modeled_support = actual_monthly_net * proper_support_rate
        modeled_shortfall = modeled_support - court_ordered_support
        unresolved_assets = sum(
            a["equity_value"] for a in self.assets_discovered.values() if a["requires_reconciliation"]
        )
        self.cumulative_impact = {
            "tracking_period_months": months,
            "monthly_concealment": monthly_variance,  # legacy UI key
            "monthly_variance": monthly_variance,
            "total_concealed_income": monthly_variance * months,  # legacy UI key
            "total_variance": monthly_variance * months,
            "proper_monthly_support": modeled_support,
            "court_ordered_support": court_ordered_support,
            "monthly_support_shortfall": modeled_shortfall,
            "total_support_arrearage": modeled_shortfall * months,
            "total_respondent_retention": (actual_monthly_net - court_ordered_support) * months,
            "concealed_assets_value": unresolved_assets,  # legacy UI key
            "unresolved_asset_value": unresolved_assets,
            "total_shielded_capital": (monthly_variance * months) + unresolved_assets,
            "baseline_monthly_net": baseline_monthly_net,
            "interpretation_status": "MODELED_OUTPUT_REQUIRES_HUMAN_REVIEW",
        }
        self._log("Cumulative impact modeled", {"months": months})
        return self.cumulative_impact

    def analyze_economic_disparity(
        self,
        petitioner_business_name: str | None = None,
        petitioner_business_months: int | None = None,
        petitioner_business_net: float | None = None,
        *,
        comparison_name: str | None = None,
        comparison_months: int | None = None,
        comparison_net: float | None = None,
    ) -> dict:
        # Accept legacy argument names while storing neutral commercial labels.
        name = comparison_name or petitioner_business_name or "Comparison Entity"
        months = comparison_months or petitioner_business_months or 1
        net = comparison_net if comparison_net is not None else (petitioner_business_net or 0.0)
        if not self.variance_analysis:
            self.calculate_variance()
        subject_monthly = self.variance_analysis["actual_monthly_net"]
        subject_annual = self.variance_analysis["actual_annual_net"]
        comparison_monthly = net / months if months else 0.0
        self.comparative_economics = {
            "petitioner_business": {
                "name": name,
                "total_months": months,
                "total_net_revenue": net,
                "monthly_average": comparison_monthly,
                "annual_equivalent": comparison_monthly * 12,
            },
            "respondent_income": {
                "annual_net": subject_annual,
                "monthly_net": subject_monthly,
                "equiv_period_net": subject_monthly * months,
            },
            "disparity": {
                "monthly_ratio": subject_monthly / comparison_monthly if comparison_monthly else 0.0,
                "annual_ratio": subject_annual / net if net else 0.0,
                "months_to_match": net / subject_monthly if subject_monthly else 0.0,
            },
            "interpretation_status": "DESCRIPTIVE_COMPARISON_ONLY",
        }
        self._log("Economic comparison computed")
        return self.comparative_economics

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_court_manifest(self) -> dict:
        if not self.variance_analysis:
            self.calculate_variance()
        if not self.cumulative_impact:
            self.calculate_cumulative_impact()
        return {
            "METADATA": {
                "system_id": self.SYSTEM_ID,
                "version": self.VERSION,
                "analyst": self.analyst_attribution,
                "case_number": self.case_number,
                "case_name": self.case_name,
                "court": self.court,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "analysis_period": f"{self.analysis_start_date} to {self.analysis_end_date}",
                "audit_hash": self._audit_hash(),
                "data_mode": "SYNTHETIC" if self.case_number.startswith("SYNTH-") else "CONFIGURED",
                "legal_finding": False,
            },
            "SWORN_BASELINE": self.sworn_data,
            "INCOME_RECONSTRUCTION": self.reconstruct_total_income(),
            "VARIANCE_ANALYSIS": self.variance_analysis,
            "CUMULATIVE_IMPACT": self.cumulative_impact,
            "ASSET_SUMMARY": self.asset_summary(),
            "ASSET_DETAIL": self.assets_discovered,
            "COMPARATIVE_ECONOMICS": self.comparative_economics,
            "AUDIT_EVENTS": len(self.audit_trail),
        }

    def generate_text_report(self) -> str:
        manifest = self.generate_court_manifest()
        return json.dumps(manifest, indent=2, default=str)

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    def _log(self, event: str, detail: dict | None = None) -> None:
        self.audit_trail.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "detail": detail or {},
            }
        )

    def _audit_hash(self) -> str:
        payload = json.dumps(self.audit_trail, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
