import json
from pathlib import Path
from ai_digital_growth import audit


class FakeAuditor:
    def audit(self, url): return {"url": url, "findings": []}


def test_cli_writes_json(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(audit, "WebsiteAuditor", FakeAuditor)
    output = tmp_path / "report.json"
    assert audit.main(["https://example.com/", "--output", str(output)]) == 0
    assert json.loads(output.read_text()) == {"url": "https://example.com/", "findings": []}


def test_cli_error_is_structured(monkeypatch, capsys):
    def fail(self, url): raise audit.AuditFetchError("ip_literal_blocked", "blocked")
    monkeypatch.setattr(audit.WebsiteAuditor, "audit", fail)
    assert audit.main(["https://127.0.0.1/"]) == 2
    assert json.loads(capsys.readouterr().err)["error_code"] == "ip_literal_blocked"
