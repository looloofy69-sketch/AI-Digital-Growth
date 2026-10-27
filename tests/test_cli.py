from pathlib import Path

from ai_digital_growth.cli import load_scenario


def test_example_scenarios_run_and_are_labeled_assumptions():
    root = Path(__file__).parents[1]
    base = load_scenario(root / "examples" / "illustrative-baseline.json").analyze()
    triaged = load_scenario(root / "examples" / "triaged-review-sensitivity.json").analyze()
    assert base["assumptions_status"] == "illustrative_not_observed"
    assert triaged["assumptions_status"] == "illustrative_not_observed"
    assert base["capacity"]["over_capacity"] is True
    assert base["capacity"]["hours_by_activity"]["human_review"] == 412.5
    assert triaged["capacity"]["hours_by_activity"]["human_review"] == 41.25
