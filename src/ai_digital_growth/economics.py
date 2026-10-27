"""Transparent capacity and unit-economics scenario model; values are assumptions, not forecasts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any


class InputValidationError(ValueError):
    """Raised when a scenario contains invalid inputs."""


def _finite_non_negative(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
        raise InputValidationError(f"{name} must be finite and >= 0; got {value!r}")


def _rate(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 <= value <= 1:
        raise InputValidationError(f"{name} must be between 0 and 1; got {value!r}")


@dataclass(frozen=True)
class FunnelAssumptions:
    positive_reply_rate: float = 0.03
    meeting_booked_per_positive_reply: float = 0.60
    meeting_attendance_rate: float = 0.80
    proposal_rate_per_attended_meeting: float = 0.70
    proposal_win_rate: float = 0.30

    def validate(self) -> None:
        for name, value in asdict(self).items():
            _rate(name, value)

    def forecast(self, contacts: float) -> dict[str, float]:
        _finite_non_negative("contacts", contacts)
        self.validate()
        replies = contacts * self.positive_reply_rate
        booked = replies * self.meeting_booked_per_positive_reply
        attended = booked * self.meeting_attendance_rate
        proposals = attended * self.proposal_rate_per_attended_meeting
        wins = proposals * self.proposal_win_rate
        return {
            "contacts": contacts,
            "positive_replies_expected": replies,
            "meetings_booked_expected": booked,
            "meetings_attended_expected": attended,
            "proposals_expected": proposals,
            "clients_won_expected": wins,
            "overall_contact_to_win_rate": wins / contacts if contacts else 0.0,
        }


@dataclass(frozen=True)
class EconomicsInputs:
    contacts_per_month: float
    human_review_share: float
    reviews_per_contact: float
    minutes_per_review: float
    research_minutes_per_contact: float
    sales_minutes_per_attended_meeting: float
    proposal_hours_per_proposal: float
    delivery_hours_per_client: float
    support_hours_per_client: float
    fixed_operations_hours_per_month: float
    available_hours_per_week: float
    weeks_per_month: float
    capacity_reserve_fraction: float
    loaded_hourly_cost: float
    revenue_per_client: float
    direct_delivery_cost_per_client: float
    fixed_tools_cost_per_month: float
    cash_acquisition_cost_per_contact: float
    funnel: FunnelAssumptions = FunnelAssumptions()
    currency: str = "EUR"
    scenario_name: str = "illustrative"

    def validate(self) -> None:
        fields = (
            "contacts_per_month", "reviews_per_contact", "minutes_per_review",
            "research_minutes_per_contact", "sales_minutes_per_attended_meeting",
            "proposal_hours_per_proposal", "delivery_hours_per_client",
            "support_hours_per_client", "fixed_operations_hours_per_month",
            "available_hours_per_week", "weeks_per_month", "loaded_hourly_cost",
            "revenue_per_client", "direct_delivery_cost_per_client",
            "fixed_tools_cost_per_month", "cash_acquisition_cost_per_contact",
        )
        for name in fields:
            _finite_non_negative(name, getattr(self, name))
        _rate("human_review_share", self.human_review_share)
        _rate("capacity_reserve_fraction", self.capacity_reserve_fraction)
        if self.capacity_reserve_fraction >= 1:
            raise InputValidationError("capacity_reserve_fraction must be < 1")
        if self.weeks_per_month <= 0:
            raise InputValidationError("weeks_per_month must be > 0")
        if not isinstance(self.currency, str) or not self.currency.strip():
            raise InputValidationError("currency must be a non-empty label")
        self.funnel.validate()

    def analyze(self) -> dict[str, Any]:
        self.validate()
        funnel = self.funnel.forecast(self.contacts_per_month)
        clients = funnel["clients_won_expected"]
        hours = {
            "human_review": self.contacts_per_month * self.reviews_per_contact * self.human_review_share * self.minutes_per_review / 60,
            "research_and_qualification": self.contacts_per_month * self.research_minutes_per_contact / 60,
            "sales_meetings": funnel["meetings_attended_expected"] * self.sales_minutes_per_attended_meeting / 60,
            "proposal_preparation": funnel["proposals_expected"] * self.proposal_hours_per_proposal,
            "delivery": clients * self.delivery_hours_per_client,
            "support": clients * self.support_hours_per_client,
            "fixed_operations": self.fixed_operations_hours_per_month,
        }
        required = sum(hours.values())
        available = self.available_hours_per_week * self.weeks_per_month
        reserve = available * self.capacity_reserve_fraction
        usable = available - reserve
        revenue = clients * self.revenue_per_client
        labor = required * self.loaded_hourly_cost
        direct_delivery = clients * self.direct_delivery_cost_per_client
        tools = self.fixed_tools_cost_per_month
        acquisition = self.contacts_per_month * self.cash_acquisition_cost_per_contact
        total_cost = labor + direct_delivery + tools + acquisition
        contribution = revenue - total_cost
        return {
            "scenario_name": self.scenario_name,
            "currency": self.currency,
            "assumptions_status": "illustrative_not_observed",
            "funnel": funnel,
            "capacity": {
                "hours_by_activity": hours,
                "total_required_hours": required,
                "available_hours_before_reserve": available,
                "reserve_hours": reserve,
                "usable_hours_after_reserve": usable,
                "headroom_hours": usable - required,
                "capacity_utilization": required / usable if usable > 0 else None,
                "over_capacity": required > usable,
            },
            "economics": {
                "expected_revenue": revenue,
                "loaded_labor_cost": labor,
                "direct_delivery_cost": direct_delivery,
                "fixed_tools_cost": tools,
                "cash_acquisition_cost": acquisition,
                "total_cost_including_loaded_labor": total_cost,
                "operating_contribution_after_modeled_costs": contribution,
                "contribution_margin_after_modeled_costs": contribution / revenue if revenue > 0 else None,
                "cost_per_expected_client": total_cost / clients if clients > 0 else None,
            },
            "limitations": [
                "All inputs are assumptions unless replaced by observed data.",
                "Expected clients are fractional statistical expectations, not guaranteed wins.",
                "Revenue is treated as recognized in this modeled month; payment timing is not modeled.",
                "Taxes, refunds, bad debt and price/volume interactions are not modeled unless entered explicitly.",
                "Capacity overload is reported, never silently capped.",
            ],
        }
