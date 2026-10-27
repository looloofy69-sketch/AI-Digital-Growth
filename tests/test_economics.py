import pytest

from ai_digital_growth.economics import EconomicsInputs, FunnelAssumptions, InputValidationError


def baseline(**overrides):
    values = dict(
        contacts_per_month=1650, human_review_share=1.0, reviews_per_contact=1.0,
        minutes_per_review=15, research_minutes_per_contact=2, sales_minutes_per_attended_meeting=45,
        proposal_hours_per_proposal=1.0, delivery_hours_per_client=24, support_hours_per_client=2,
        fixed_operations_hours_per_month=20, available_hours_per_week=50, weeks_per_month=4,
        capacity_reserve_fraction=0.2, loaded_hourly_cost=25, revenue_per_client=1200,
        direct_delivery_cost_per_client=150, fixed_tools_cost_per_month=500,
        cash_acquisition_cost_per_contact=0,
    )
    values.update(overrides)
    return EconomicsInputs(**values)


def test_blueprint_funnel_arithmetic():
    x = FunnelAssumptions().forecast(1000)
    assert x["positive_replies_expected"] == pytest.approx(30)
    assert x["meetings_booked_expected"] == pytest.approx(18)
    assert x["meetings_attended_expected"] == pytest.approx(14.4)
    assert x["proposals_expected"] == pytest.approx(10.08)
    assert x["clients_won_expected"] == pytest.approx(3.024)
    assert x["overall_contact_to_win_rate"] == pytest.approx(0.003024)


def test_full_review_recreates_capacity_mismatch():
    x = baseline().analyze()
    assert x["capacity"]["hours_by_activity"]["human_review"] == pytest.approx(412.5)
    assert x["capacity"]["usable_hours_after_reserve"] == pytest.approx(160)
    assert x["capacity"]["over_capacity"] is True
    assert x["capacity"]["total_required_hours"] > x["capacity"]["usable_hours_after_reserve"]
    assert x["assumptions_status"] == "illustrative_not_observed"


def test_review_sensitivity_reduces_hours_but_still_overloads_capacity():
    full = baseline().analyze()
    triaged = baseline(human_review_share=.1, scenario_name="triaged").analyze()
    assert triaged["capacity"]["hours_by_activity"]["human_review"] == pytest.approx(41.25)
    assert triaged["capacity"]["total_required_hours"] < full["capacity"]["total_required_hours"]
    assert triaged["capacity"]["over_capacity"] is True


def test_zero_contacts_well_defined():
    x = baseline(contacts_per_month=0).analyze()
    assert x["funnel"]["clients_won_expected"] == 0
    assert x["economics"]["expected_revenue"] == 0
    assert x["economics"]["contribution_margin_after_modeled_costs"] is None
    assert x["capacity"]["over_capacity"] is False


@pytest.mark.parametrize("field,value", [
    ("human_review_share", -0.01), ("human_review_share", 1.01),
    ("capacity_reserve_fraction", 1.0), ("minutes_per_review", -1),
    ("available_hours_per_week", float("inf")), ("weeks_per_month", 0), ("currency", "  "),
])
def test_invalid_scenario_rejected(field, value):
    with pytest.raises(InputValidationError):
        baseline(**{field: value}).analyze()


def test_invalid_funnel_rate_rejected():
    with pytest.raises(InputValidationError):
        baseline(funnel=FunnelAssumptions(positive_reply_rate=1.5)).analyze()


def test_cost_formula_includes_modeled_items():
    x = baseline().analyze()["economics"]
    assert x["total_cost_including_loaded_labor"] == pytest.approx(
        x["loaded_labor_cost"] + x["direct_delivery_cost"] + x["fixed_tools_cost"] + x["cash_acquisition_cost"]
    )
    assert x["operating_contribution_after_modeled_costs"] == pytest.approx(x["expected_revenue"] - x["total_cost_including_loaded_labor"])
