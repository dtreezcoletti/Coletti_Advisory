"""
Coletti OS v2.0 — Core Data Framework
"""

import json
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ThreatLevel(Enum):
    LOW = "Monitoring"
    ELEVATED = "Active Defense Required"
    CRITICAL = "Immediate Tactical Execution"
    CONTAINED = "Asset/Advantage Secured"


class ProjectPhase(Enum):
    DRAFTING = "Blueprint & Drafting"
    ACTIVE = "Live Operations"
    ARCHIVED = "Completed/Archived"


# ── Forensic Accounting ───────────────────────────────────────────────────────

@dataclass
class Transaction:
    effective_date: str
    amount: float
    description: str
    category: str
    is_marital_dissipation: bool = False
    balance_after: float = 0.0

    def to_dict(self) -> dict:
        return {
            "effective_date": self.effective_date,
            "amount": self.amount,
            "description": self.description,
            "category": self.category,
            "is_marital_dissipation": self.is_marital_dissipation,
            "balance_after": self.balance_after,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        return cls(**d)


@dataclass
class ForensicLedger:
    institution: str
    target_account: str
    known_balance: float
    transactions: List[Transaction] = field(default_factory=list)

    def calculate_dissipation(self) -> float:
        return sum(t.amount for t in self.transactions if t.is_marital_dissipation)

    def calculate_total(self) -> float:
        return sum(t.amount for t in self.transactions)

    def dissipation_rate(self) -> float:
        total = self.calculate_total()
        return (self.calculate_dissipation() / total * 100) if total else 0.0


# ── Litigation Command ────────────────────────────────────────────────────────

@dataclass
class LegalMotion:
    title: str
    date_filed: str          # ISO string for serialisation simplicity
    hearing_date: Optional[str]
    status: str
    strategic_objective: str

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "date_filed": self.date_filed,
            "hearing_date": self.hearing_date,
            "status": self.status,
            "strategic_objective": self.strategic_objective,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LegalMotion":
        return cls(**d)


@dataclass
class LitigationDocket:
    case_number: str = "24D1003"
    jurisdiction: str = "Fourth Circuit Court, Davidson County"
    judge: str = "Hon. Stephanie J. Williams"
    motions: List[LegalMotion] = field(default_factory=list)
    active_subpoenas: List[str] = field(default_factory=list)
    rule_36_days_default: int = 89

    def evaluate_docket_leverage(self) -> int:
        score = 0
        if self.rule_36_days_default > 30:
            score += 100
        score += len(self.active_subpoenas) * 20
        return score

    def next_hearing(self) -> Optional[str]:
        future = [
            m.hearing_date for m in self.motions
            if m.hearing_date and m.hearing_date >= date.today().isoformat()
        ]
        return min(future) if future else None


# ── Enterprise Management ─────────────────────────────────────────────────────

@dataclass
class AdvisoryClient:
    entity_name: str
    primary_objective: str
    phase: str               # ProjectPhase value string
    retainer_active: bool = False

    def to_dict(self) -> dict:
        return {
            "entity_name": self.entity_name,
            "primary_objective": self.primary_objective,
            "phase": self.phase,
            "retainer_active": self.retainer_active,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AdvisoryClient":
        return cls(**d)


@dataclass
class EnterpriseManagement:
    firm_name: str = "Coletti & Co."
    founder: str = "Demetries James Lucio Coletti"
    active_portfolios: List[AdvisoryClient] = field(default_factory=list)

    def add_client(self, client: AdvisoryClient):
        self.active_portfolios.append(client)

    def retainer_count(self) -> int:
        return sum(1 for c in self.active_portfolios if c.retainer_active)


# ── Key Case Dates ───────────────────────────────────────────────────────────

@dataclass
class CaseDates:
    marriage_start: str = "2013-01-01"
    assault_date: str = "2024-06-13"
    separation_date: str = "2024-06-13"
    filing_date: str = "2024-07-24"

    def marriage_years(self) -> float:
        return (date.fromisoformat(self.separation_date) - date.fromisoformat(self.marriage_start)).days / 365.25

    def to_dict(self) -> dict:
        return {
            "marriage_start": self.marriage_start,
            "assault_date": self.assault_date,
            "separation_date": self.separation_date,
            "filing_date": self.filing_date,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CaseDates":
        return cls(**d)


# ── Income Fraud (Opposing Party) ─────────────────────────────────────────────

@dataclass
class IncomeFraud:
    sworn_annual: float = 60750.00
    verified_w2: float = 114920.00
    verified_1099: float = 22611.00

    @property
    def verified_total(self) -> float:
        return self.verified_w2 + self.verified_1099

    @property
    def concealment_amount(self) -> float:
        return self.verified_total - self.sworn_annual

    @property
    def concealment_pct(self) -> float:
        return (self.concealment_amount / self.sworn_annual * 100) if self.sworn_annual else 0.0

    def to_dict(self) -> dict:
        return {
            "sworn_annual": self.sworn_annual,
            "verified_w2": self.verified_w2,
            "verified_1099": self.verified_1099,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "IncomeFraud":
        return cls(**d)


# ── Pre-Assault Income (Coletti) ──────────────────────────────────────────────

@dataclass
class ColettisIncome:
    modeling_annual: float = 36750.00
    coletti_co_annual: float = 20000.00

    @property
    def total_independent(self) -> float:
        return self.modeling_annual + self.coletti_co_annual

    def to_dict(self) -> dict:
        return {"modeling_annual": self.modeling_annual, "coletti_co_annual": self.coletti_co_annual}

    @classmethod
    def from_dict(cls, d: dict) -> "ColettisIncome":
        return cls(**d)


# ── Case Valuation ────────────────────────────────────────────────────────────

@dataclass
class Tier1Relief:
    suit_money: float = 5000.00
    income_concealment_proven: float = 76781.00
    income_concealment_suspected: float = 21758.68
    animal_equalization: float = 20000.00
    pendente_lite_monthly: float = 4355.15
    pendente_lite_arrearage: float = 33666.60
    king_personal_sanctions: float = 27000.00

    @property
    def income_concealment_total(self) -> float:
        return self.income_concealment_proven + self.income_concealment_suspected

    @property
    def subtotal(self) -> float:
        return (self.suit_money + self.income_concealment_total +
                self.animal_equalization + self.pendente_lite_arrearage +
                self.king_personal_sanctions)

    def to_dict(self) -> dict:
        return {
            "suit_money": self.suit_money,
            "income_concealment_proven": self.income_concealment_proven,
            "income_concealment_suspected": self.income_concealment_suspected,
            "animal_equalization": self.animal_equalization,
            "pendente_lite_monthly": self.pendente_lite_monthly,
            "pendente_lite_arrearage": self.pendente_lite_arrearage,
            "king_personal_sanctions": self.king_personal_sanctions,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Tier1Relief":
        return cls(**d)


@dataclass
class Tier2Damages:
    homemaker_contributions: float = 715000.00
    human_capital_loss: float = 158000.00
    business_sabotage: float = 365597.56
    property_division: float = 108000.00
    alimony_in_solido: float = 300000.00
    marital_fault_damages: float = 350000.00

    @property
    def subtotal(self) -> float:
        return (self.homemaker_contributions + self.human_capital_loss +
                self.business_sabotage + self.property_division +
                self.alimony_in_solido + self.marital_fault_damages)

    def to_dict(self) -> dict:
        return {
            "homemaker_contributions": self.homemaker_contributions,
            "human_capital_loss": self.human_capital_loss,
            "business_sabotage": self.business_sabotage,
            "property_division": self.property_division,
            "alimony_in_solido": self.alimony_in_solido,
            "marital_fault_damages": self.marital_fault_damages,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Tier2Damages":
        return cls(**d)


@dataclass
class Tier3Punitive:
    assault_punitive: float = 554468.00
    economic_destruction_punitive: float = 200000.00

    @property
    def total(self) -> float:
        return self.assault_punitive + self.economic_destruction_punitive

    def to_dict(self) -> dict:
        return {
            "assault_punitive": self.assault_punitive,
            "economic_destruction_punitive": self.economic_destruction_punitive,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Tier3Punitive":
        return cls(**d)


@dataclass
class BusinessSabotageDetail:
    physical_property: float = 8800.00
    # Modeling career
    modeling_immediate_recovery: float = 6125.00
    modeling_forced_leave_23mo: float = 70437.50
    modeling_slam_contract_loss: float = 45000.00
    modeling_future_5yr: float = 192951.69
    # Coletti & Co.
    coletti_co_base_annual: float = 20000.00
    coletti_co_years_closed: float = 1.92
    coletti_co_growth_adj: float = 3843.94

    @property
    def modeling_total(self) -> float:
        return (self.modeling_immediate_recovery + self.modeling_forced_leave_23mo +
                self.modeling_slam_contract_loss + self.modeling_future_5yr)

    @property
    def coletti_co_lost_revenue(self) -> float:
        return self.coletti_co_base_annual * self.coletti_co_years_closed

    @property
    def coletti_co_total(self) -> float:
        return self.coletti_co_lost_revenue + self.coletti_co_growth_adj

    @property
    def grand_total(self) -> float:
        return self.physical_property + self.modeling_total + self.coletti_co_total

    def to_dict(self) -> dict:
        return {
            "physical_property": self.physical_property,
            "modeling_immediate_recovery": self.modeling_immediate_recovery,
            "modeling_forced_leave_23mo": self.modeling_forced_leave_23mo,
            "modeling_slam_contract_loss": self.modeling_slam_contract_loss,
            "modeling_future_5yr": self.modeling_future_5yr,
            "coletti_co_base_annual": self.coletti_co_base_annual,
            "coletti_co_years_closed": self.coletti_co_years_closed,
            "coletti_co_growth_adj": self.coletti_co_growth_adj,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BusinessSabotageDetail":
        return cls(**d)


@dataclass
class CaseValuation:
    case_dates: CaseDates = field(default_factory=CaseDates)
    income_fraud: IncomeFraud = field(default_factory=IncomeFraud)
    colettis_income: ColettisIncome = field(default_factory=ColettisIncome)
    tier1: Tier1Relief = field(default_factory=Tier1Relief)
    tier2: Tier2Damages = field(default_factory=Tier2Damages)
    tier3: Tier3Punitive = field(default_factory=Tier3Punitive)
    sabotage: BusinessSabotageDetail = field(default_factory=BusinessSabotageDetail)
    premeditation_score: float = 1.0
    premeditation_assessment: str = "HIGHLY PREMEDITATED"
    premeditation_event_count: int = 10

    @property
    def total_capped(self) -> float:
        return self.tier1.subtotal + self.tier2.subtotal + self.tier3.total

    @property
    def total_uncapped(self) -> float:
        return self.total_capped + self.tier1.pendente_lite_monthly * 12

    def to_dict(self) -> dict:
        return {
            "case_dates": self.case_dates.to_dict(),
            "income_fraud": self.income_fraud.to_dict(),
            "colettis_income": self.colettis_income.to_dict(),
            "tier1": self.tier1.to_dict(),
            "tier2": self.tier2.to_dict(),
            "tier3": self.tier3.to_dict(),
            "sabotage": self.sabotage.to_dict(),
            "premeditation_score": self.premeditation_score,
            "premeditation_assessment": self.premeditation_assessment,
            "premeditation_event_count": self.premeditation_event_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CaseValuation":
        obj = cls()
        if "case_dates" in d:
            obj.case_dates = CaseDates.from_dict(d["case_dates"])
        if "income_fraud" in d:
            obj.income_fraud = IncomeFraud.from_dict(d["income_fraud"])
        if "colettis_income" in d:
            obj.colettis_income = ColettisIncome.from_dict(d["colettis_income"])
        if "tier1" in d:
            obj.tier1 = Tier1Relief.from_dict(d["tier1"])
        if "tier2" in d:
            obj.tier2 = Tier2Damages.from_dict(d["tier2"])
        if "tier3" in d:
            obj.tier3 = Tier3Punitive.from_dict(d["tier3"])
        if "sabotage" in d:
            obj.sabotage = BusinessSabotageDetail.from_dict(d["sabotage"])
        obj.premeditation_score = d.get("premeditation_score", obj.premeditation_score)
        obj.premeditation_assessment = d.get("premeditation_assessment", obj.premeditation_assessment)
        obj.premeditation_event_count = d.get("premeditation_event_count", obj.premeditation_event_count)
        return obj


# ── Income Disparity Tracker ──────────────────────────────────────────────────

@dataclass
class IncomeDisparity:
    """Tracks the gap between sworn income disclosures and verified actual income."""
    sworn_monthly_net: float = 4389.80
    verified_monthly_net: float = 9983.18
    tracking_months: int = 22
    sequestered_hard_assets: float = 205642.80

    def monthly_understatement(self) -> float:
        return self.verified_monthly_net - self.sworn_monthly_net

    def cumulative_understatement(self) -> float:
        return self.monthly_understatement() * self.tracking_months

    def understatement_pct(self) -> float:
        if self.sworn_monthly_net == 0:
            return 0.0
        return (self.monthly_understatement() / self.sworn_monthly_net) * 100

    def total_concealed_value(self) -> float:
        return self.cumulative_understatement() + self.sequestered_hard_assets

    def to_dict(self) -> dict:
        return {
            "sworn_monthly_net": self.sworn_monthly_net,
            "verified_monthly_net": self.verified_monthly_net,
            "tracking_months": self.tracking_months,
            "sequestered_hard_assets": self.sequestered_hard_assets,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "IncomeDisparity":
        return cls(**d)


# ── Master Controller ─────────────────────────────────────────────────────────

class ColettiOS:
    VERSION = "2.5.5"
    SYSTEM_ID = "ColettiOS_v2.5.5_PROD"

    def __init__(self):
        self.boot_time = datetime.now()
        self.forensics = ForensicLedger(
            institution="First Florida Credit Union",
            target_account="XXXX-0094",
            known_balance=0.00,
        )
        self.litigation = LitigationDocket()
        self.enterprise = EnterpriseManagement()
        self.income_disparity = IncomeDisparity()
        self.case_valuation = CaseValuation()
        self._seed_environment()

    def _seed_environment(self):
        self.litigation.motions = [
            LegalMotion(
                title="Motion to Confirm Rule 36 Deemed Admissions",
                date_filed="2026-02-18",
                hearing_date="2026-05-29",
                status="Pending Judicial Signature",
                strategic_objective="Lock in 27 counts of asset dissipation.",
            ),
            LegalMotion(
                title="Emergency Motion for Immediate Disqualification",
                date_filed="2026-05-10",
                hearing_date="2026-05-29",
                status="Active",
                strategic_objective="Neutralize opposing counsel via RPC violations.",
            ),
        ]
        self.litigation.active_subpoenas = [
            "Dreamliner HQ – Payroll Manifests",
            "First Florida Credit Union – Unredacted Ledgers",
        ]

        # Pre-loaded FFCU ledger — confirmed transactions from subpoena returns
        self.forensics.transactions = [
            Transaction(
                effective_date="2023-05-12",
                amount=700.00,
                description="Lyons HR LLC Payroll",
                category="income",
                is_marital_dissipation=False,
                balance_after=2959.37,
            ),
            Transaction(
                effective_date="2023-05-29",
                amount=3498.90,
                description="PayPal *ColettiAndBrown",
                category="coletti_brown_entity",
                is_marital_dissipation=True,   # funds diverted to joint entity without consent
                balance_after=314.52,
            ),
            Transaction(
                effective_date="2023-10-27",
                amount=700.00,
                description="Lyons HR LLC Payroll",
                category="income",
                is_marital_dissipation=False,
                balance_after=3005.46,
            ),
            Transaction(
                effective_date="2023-11-28",
                amount=50.00,
                description="Capital One Auto",
                category="vehicle",
                is_marital_dissipation=True,   # personal vehicle during withholding period
                balance_after=2902.92,
            ),
            Transaction(
                effective_date="2024-01-09",
                amount=2961.12,
                description="American Homes 4 Rent",
                category="housing",
                is_marital_dissipation=True,   # housing paid while withholding court-ordered support
                balance_after=14.21,
            ),
        ]

        # Tactical status — updated after ceasefire expiry May 18, 2026
        self.tactical_status = {
            "ceasefire_expired": True,
            "ceasefire_date": "2026-05-18",
            "ceasefire_time": "4:30 PM CST",
            "active_strategy": "Full evidentiary preparation for May 29th hearing.",
            "counter_measure": (
                "Starvation tactics by opposing counsel neutralized. "
                "No further settlement negotiations. Proceeding with "
                "Disqualification Motion and Rule 36 Default confirmation."
            ),
            "dissipation_payroll_diverted": 11125.00,
            "dissipation_housing_withheld": 7858.62,
        }

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "forensics": {
                "institution": self.forensics.institution,
                "target_account": self.forensics.target_account,
                "known_balance": self.forensics.known_balance,
                "transactions": [t.to_dict() for t in self.forensics.transactions],
            },
            "litigation": {
                "case_number": self.litigation.case_number,
                "jurisdiction": self.litigation.jurisdiction,
                "judge": self.litigation.judge,
                "rule_36_days_default": self.litigation.rule_36_days_default,
                "motions": [m.to_dict() for m in self.litigation.motions],
                "active_subpoenas": self.litigation.active_subpoenas,
            },
            "enterprise": {
                "firm_name": self.enterprise.firm_name,
                "founder": self.enterprise.founder,
                "portfolios": [c.to_dict() for c in self.enterprise.active_portfolios],
            },
            "income_disparity": self.income_disparity.to_dict(),
            "case_valuation": self.case_valuation.to_dict(),
        }

    def load_dict(self, data: dict):
        f = data.get("forensics", {})
        self.forensics.institution = f.get("institution", self.forensics.institution)
        self.forensics.target_account = f.get("target_account", self.forensics.target_account)
        self.forensics.known_balance = f.get("known_balance", self.forensics.known_balance)
        self.forensics.transactions = [Transaction.from_dict(t) for t in f.get("transactions", [])]

        l = data.get("litigation", {})
        self.litigation.case_number = l.get("case_number", self.litigation.case_number)
        self.litigation.jurisdiction = l.get("jurisdiction", self.litigation.jurisdiction)
        self.litigation.judge = l.get("judge", self.litigation.judge)
        self.litigation.rule_36_days_default = l.get("rule_36_days_default", self.litigation.rule_36_days_default)
        self.litigation.motions = [LegalMotion.from_dict(m) for m in l.get("motions", [])]
        self.litigation.active_subpoenas = l.get("active_subpoenas", self.litigation.active_subpoenas)

        e = data.get("enterprise", {})
        self.enterprise.firm_name = e.get("firm_name", self.enterprise.firm_name)
        self.enterprise.founder = e.get("founder", self.enterprise.founder)
        self.enterprise.active_portfolios = [AdvisoryClient.from_dict(c) for c in e.get("portfolios", [])]

        if "income_disparity" in data:
            self.income_disparity = IncomeDisparity.from_dict(data["income_disparity"])
        if "case_valuation" in data:
            self.case_valuation = CaseValuation.from_dict(data["case_valuation"])
