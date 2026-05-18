"""
Coletti OS v2.5.5 — Forensic Financial Analysis Engine
Multi-source income reconstruction, variance analysis, cumulative impact,
economic disparity analysis, and court manifest generation.

Case No. 24D-1003 | Coletti v. Brown
Attribution: ACC (Coletti & Co.)
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional


class ForensicEngine:
    """
    Forensic Financial Analysis Engine

    Reconstructs actual income from discovered financial documents,
    calculates concealment, quantifies harm, and generates court-ready
    evidence packages.
    """

    VERSION = "2.5.5"
    SYSTEM_ID = "ColettiOS_v2.5.5_PROD"

    def __init__(self):
        self.analyst_attribution = "ACC (Coletti & Co.)"
        self.case_number = "24D-1003"
        self.case_name = "Coletti v. Brown"
        self.court = "Circuit Court for Davidson County, Tennessee"

        self.analysis_start_date = "2024-07-01"
        self.analysis_end_date = "2026-05-31"
        self.tracking_months = 22

        # Ground truth: opposing party sworn testimony
        self.sworn_data = {
            "monthly_net_income": 4389.80,
            "monthly_gross_income": 5062.50,
            "annual_gross_income": 60750.00,
            "claimed_monthly_deficit": -903.89,
            "affidavit_date": "2025-05-27",
            "source": "Financial Affidavit filed May 27, 2025",
        }

        self.income_sources: Dict[str, dict] = {}
        self.assets_discovered: Dict[str, dict] = {}

        self.variance_analysis: dict = {}
        self.cumulative_impact: dict = {}
        self.comparative_economics: dict = {}

        self.audit_trail: List[dict] = []
        self._log("System initialized", {"case": self.case_number})

        # Pre-load known case data
        self._seed_case_data()

    # ── Seeding ───────────────────────────────────────────────────────────────

    def _seed_case_data(self):
        """Pre-load confirmed case 24D-1003 evidence."""
        self.ingest_income_source(
            source_name="Dreamliner Aircraft Services (W-2)",
            annual_amount=114920.00,
            source_type="W2",
            documentation="Paystubs obtained February 8, 2026",
            discovered_date="2026-02-08",
        )
        self.ingest_income_source(
            source_name="R.E. Garrison Trucking Company (1099-NEC)",
            annual_amount=22611.18,
            source_type="1099",
            documentation="2024 Form 1099-NEC",
            discovered_date="2026-02-15",
        )
        self.ingest_asset(
            asset_name="Real Property (Respondent)",
            asset_type="Real Estate",
            market_value=200535.00,
            equity_value=127000.00,
            documentation="TransUnion credit report",
            disclosed=False,
        )
        self.ingest_asset(
            asset_name="Fidelity 401(k)",
            asset_type="Retirement",
            market_value=61200.00,
            equity_value=61200.00,
            documentation="Disclosed in discovery",
            disclosed=True,
        )
        self.ingest_asset(
            asset_name="First Florida Credit Union Account",
            asset_type="Account",
            market_value=25000.00,
            equity_value=25000.00,
            documentation="Account existence confirmed via subpoena",
            disclosed=False,
        )
        self.ingest_asset(
            asset_name="Coletti & Brown Enterprises LLC",
            asset_type="LLC",
            market_value=20000.00,
            equity_value=20000.00,
            documentation="Florida LLC formation documents, Feb 7, 2024",
            disclosed=False,
        )
        # Run analyses with verified net from paystub analysis
        self.calculate_variance(actual_monthly_net=9983.18)
        self.calculate_cumulative_impact(months=22)
        self.analyze_economic_disparity(
            petitioner_business_name="Coletti & Co. LLC",
            petitioner_business_months=54,
            petitioner_business_net=22798.78,
        )

    # ── Module 1: Income Reconstruction ──────────────────────────────────────

    def ingest_income_source(
        self,
        source_name: str,
        annual_amount: float,
        source_type: str,
        documentation: str,
        discovered_date: str = None,
    ) -> str:
        source_id = f"SOURCE_{len(self.income_sources) + 1:02d}"
        self.income_sources[source_id] = {
            "name": source_name,
            "annual_gross": annual_amount,
            "monthly_gross": annual_amount / 12,
            "source_type": source_type,
            "documentation": documentation,
            "discovered_date": discovered_date or datetime.now().strftime("%Y-%m-%d"),
            "verified": True,
        }
        self._log(f"Income source ingested: {source_name}", {"annual": annual_amount})
        return source_id

    def reconstruct_total_income(self) -> dict:
        total_annual = sum(s["annual_gross"] for s in self.income_sources.values())
        return {
            "total_annual_gross": total_annual,
            "total_monthly_gross": total_annual / 12,
            "estimated_annual_net": total_annual * 0.80,
            "estimated_monthly_net": (total_annual * 0.80) / 12,
            "source_count": len(self.income_sources),
            "sources_breakdown": {
                sid: {
                    "name": d["name"],
                    "annual": d["annual_gross"],
                    "monthly": d["monthly_gross"],
                    "type": d["source_type"],
                    "documentation": d["documentation"],
                }
                for sid, d in self.income_sources.items()
            },
        }

    # ── Module 2: Asset Discovery ─────────────────────────────────────────────

    def ingest_asset(
        self,
        asset_name: str,
        asset_type: str,
        market_value: float,
        equity_value: float = None,
        documentation: str = None,
        disclosed: bool = False,
    ) -> str:
        asset_id = f"ASSET_{len(self.assets_discovered) + 1:02d}"
        self.assets_discovered[asset_id] = {
            "name": asset_name,
            "type": asset_type,
            "market_value": market_value,
            "equity_value": equity_value if equity_value is not None else market_value,
            "documentation": documentation,
            "disclosed_in_affidavit": disclosed,
            "concealed": not disclosed,
        }
        self._log(f"Asset ingested: {asset_name}", {"value": market_value, "disclosed": disclosed})
        return asset_id

    def asset_summary(self) -> dict:
        all_assets = list(self.assets_discovered.values())
        concealed = [a for a in all_assets if a["concealed"]]
        return {
            "total_count": len(all_assets),
            "total_market_value": sum(a["market_value"] for a in all_assets),
            "total_equity_value": sum(a["equity_value"] for a in all_assets),
            "concealed_count": len(concealed),
            "concealed_equity_value": sum(a["equity_value"] for a in concealed),
            "disclosed_count": len(all_assets) - len(concealed),
        }

    # ── Module 3: Variance Analysis ───────────────────────────────────────────

    def calculate_variance(self, actual_monthly_net: float = None) -> dict:
        if actual_monthly_net is None:
            actual_monthly_net = self.reconstruct_total_income()["estimated_monthly_net"]

        sworn = self.sworn_data["monthly_net_income"]
        delta = actual_monthly_net - sworn

        self.variance_analysis = {
            "sworn_monthly_net": sworn,
            "actual_monthly_net": actual_monthly_net,
            "monthly_concealment_delta": delta,
            "concealment_percentage": (delta / sworn * 100) if sworn else 0.0,
            "sworn_annual_net": sworn * 12,
            "actual_annual_net": actual_monthly_net * 12,
            "annual_concealment_delta": (actual_monthly_net - sworn) * 12,
        }
        self._log("Variance analysis computed", {"monthly_delta": delta})
        return self.variance_analysis

    # ── Module 4: Cumulative Impact ───────────────────────────────────────────

    def calculate_cumulative_impact(
        self,
        months: int = None,
        proper_support_rate: float = 0.35,
        court_ordered_support: float = 1300.00,
    ) -> dict:
        months = months or self.tracking_months
        if not self.variance_analysis:
            self.calculate_variance()

        actual_monthly_net = self.variance_analysis["actual_monthly_net"]
        sworn_monthly_net = self.variance_analysis["sworn_monthly_net"]
        monthly_concealment = self.variance_analysis["monthly_concealment_delta"]

        proper_support = actual_monthly_net * proper_support_rate
        support_shortfall = proper_support - court_ordered_support

        concealed_assets = sum(
            a["equity_value"] for a in self.assets_discovered.values() if a["concealed"]
        )

        self.cumulative_impact = {
            "tracking_period_months": months,
            "monthly_concealment": monthly_concealment,
            "total_concealed_income": monthly_concealment * months,
            "proper_monthly_support": proper_support,
            "court_ordered_support": court_ordered_support,
            "monthly_support_shortfall": support_shortfall,
            "total_support_arrearage": support_shortfall * months,
            "total_respondent_retention": (actual_monthly_net - court_ordered_support) * months,
            "concealed_assets_value": concealed_assets,
            "total_shielded_capital": (monthly_concealment * months) + concealed_assets,
        }
        self._log("Cumulative impact computed", {"months": months})
        return self.cumulative_impact

    # ── Module 5: Economic Disparity ──────────────────────────────────────────

    def analyze_economic_disparity(
        self,
        petitioner_business_name: str,
        petitioner_business_months: int,
        petitioner_business_net: float,
    ) -> dict:
        if not self.variance_analysis:
            self.calculate_variance()

        respondent_monthly = self.variance_analysis["actual_monthly_net"]
        respondent_annual = self.variance_analysis["actual_annual_net"]
        pet_monthly_avg = petitioner_business_net / petitioner_business_months

        self.comparative_economics = {
            "petitioner_business": {
                "name": petitioner_business_name,
                "total_months": petitioner_business_months,
                "total_net_revenue": petitioner_business_net,
                "monthly_average": pet_monthly_avg,
                "annual_equivalent": pet_monthly_avg * 12,
            },
            "respondent_income": {
                "annual_net": respondent_annual,
                "monthly_net": respondent_monthly,
                "equiv_period_net": respondent_monthly * petitioner_business_months,
            },
            "disparity": {
                "monthly_ratio": respondent_monthly / pet_monthly_avg if pet_monthly_avg else 0,
                "annual_ratio": respondent_annual / petitioner_business_net if petitioner_business_net else 0,
                "months_to_match": petitioner_business_net / respondent_monthly if respondent_monthly else 0,
            },
        }
        self._log("Economic disparity computed")
        return self.comparative_economics

    # ── Module 6: Court Manifest ──────────────────────────────────────────────

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
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "analysis_period": f"{self.analysis_start_date} to {self.analysis_end_date}",
                "audit_hash": self._audit_hash(),
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

    # ── Module 7: Text Report ─────────────────────────────────────────────────

    def generate_text_report(self) -> str:
        manifest = self.generate_court_manifest()
        va = manifest["VARIANCE_ANALYSIS"]
        ci = manifest["CUMULATIVE_IMPACT"]
        ad = manifest["ASSET_SUMMARY"]
        ce = manifest["COMPARATIVE_ECONOMICS"]
        lines = []

        def hr(char="─", width=76):
            lines.append(char * width)

        hr("═")
        lines.append(f" {self.SYSTEM_ID}  |  FORENSIC ANALYSIS REPORT")
        hr("═")
        lines.append(f"  Case:     {self.case_name}  (No. {self.case_number})")
        lines.append(f"  Court:    {self.court}")
        lines.append(f"  Analyst:  {self.analyst_attribution}")
        lines.append(f"  Period:   {self.analysis_start_date} → {self.analysis_end_date}  ({self.tracking_months} months)")
        lines.append(f"  Hash:     {manifest['METADATA']['audit_hash']}")
        hr()

        lines.append("\n[1] INCOME VARIANCE ANALYSIS")
        hr()
        lines.append(f"  Sworn Monthly Net:          ${va['sworn_monthly_net']:>12,.2f}")
        lines.append(f"  Verified Monthly Net:        ${va['actual_monthly_net']:>12,.2f}")
        lines.append(f"  Monthly Concealment Delta:   ${va['monthly_concealment_delta']:>12,.2f}")
        lines.append(f"  Concealment Rate:            {va['concealment_percentage']:>11.2f}%")
        lines.append(f"  Sworn Annual Net:            ${va['sworn_annual_net']:>12,.2f}")
        lines.append(f"  Verified Annual Net:         ${va['actual_annual_net']:>12,.2f}")
        lines.append(f"  Annual Concealment:          ${va['annual_concealment_delta']:>12,.2f}")

        lines.append(f"\n[2] CUMULATIVE IMPACT  ({ci['tracking_period_months']} months)")
        hr()
        lines.append(f"  Total Concealed Income:      ${ci['total_concealed_income']:>12,.2f}")
        lines.append(f"  Proper Monthly Support:      ${ci['proper_monthly_support']:>12,.2f}")
        lines.append(f"  Court-Ordered Support:       ${ci['court_ordered_support']:>12,.2f}")
        lines.append(f"  Monthly Support Shortfall:   ${ci['monthly_support_shortfall']:>12,.2f}")
        lines.append(f"  Total Support Arrearage:     ${ci['total_support_arrearage']:>12,.2f}")
        lines.append(f"  Respondent Total Retention:  ${ci['total_respondent_retention']:>12,.2f}")
        lines.append(f"  Concealed Assets Value:      ${ci['concealed_assets_value']:>12,.2f}")
        lines.append(f"  {'─'*46}")
        lines.append(f"  TOTAL SHIELDED CAPITAL:      ${ci['total_shielded_capital']:>12,.2f}")

        lines.append("\n[3] ASSET DISCOVERY")
        hr()
        lines.append(f"  Total Assets Found:          {ad['total_count']:>14}")
        lines.append(f"  Total Market Value:          ${ad['total_market_value']:>12,.2f}")
        lines.append(f"  Total Equity Value:          ${ad['total_equity_value']:>12,.2f}")
        lines.append(f"  Concealed Assets Count:      {ad['concealed_count']:>14}")
        lines.append(f"  Concealed Assets Equity:     ${ad['concealed_equity_value']:>12,.2f}")

        for aid, asset in self.assets_discovered.items():
            flag = "CONCEALED" if asset["concealed"] else "disclosed"
            lines.append(f"    [{flag:>9}] {asset['name']} — ${asset['equity_value']:,.2f}  |  {asset['documentation']}")

        if ce:
            lines.append("\n[4] ECONOMIC DISPARITY ANALYSIS")
            hr()
            pb = ce["petitioner_business"]
            da = ce["disparity"]
            lines.append(f"  Petitioner's Business: {pb['name']}")
            lines.append(f"    Operation Period:    {pb['total_months']} months")
            lines.append(f"    Total Revenue:       ${pb['total_net_revenue']:>12,.2f}")
            lines.append(f"    Monthly Average:     ${pb['monthly_average']:>12,.2f}")
            lines.append(f"  Respondent Monthly Net:            ${ce['respondent_income']['monthly_net']:>10,.2f}")
            lines.append(f"  Monthly Disparity Ratio:           {da['monthly_ratio']:>10.2f}x")
            lines.append(f"  Annual Disparity Ratio:            {da['annual_ratio']:>10.2f}x")
            lines.append(f"  Months to Match Business Revenue:  {da['months_to_match']:>10.1f}")

        lines.append("")
        hr("═")
        return "\n".join(lines)

    # ── Audit ─────────────────────────────────────────────────────────────────

    def _log(self, event: str, details: dict = None):
        self.audit_trail.append({
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "details": details or {},
        })

    def _audit_hash(self) -> str:
        s = (f"{self.VERSION}|{self.case_number}|"
             f"{self.variance_analysis.get('monthly_concealment_delta', 0):.2f}|"
             f"{self.cumulative_impact.get('total_support_arrearage', 0):.2f}|"
             f"{len(self.income_sources)}|{len(self.assets_discovered)}")
        return hashlib.sha256(s.encode()).hexdigest()[:16].upper()
