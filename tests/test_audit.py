import hashlib
import io
import ipaddress
import socket
from datetime import datetime, timezone

import pytest

from ai_digital_growth.audit import AuditFetchError, SafeHTTPSFetcher, WebsiteAuditor, normalize_url


def resolver(*ips):
    return lambda host, port, type=socket.SOCK_STREAM: [
        (socket.AF_INET6 if ":" in x else socket.AF_INET, socket.SOCK_STREAM, 6, "", (x, port)) for x in ips
    ]


class FakeSocket:
    def __init__(self, raw): self.raw, self.sent, self.closed = raw, b"", False
    def settimeout(self, value): self.timeout = value
    def sendall(self, data): self.sent += data
    def makefile(self, mode): return io.BytesIO(self.raw)
    def close(self): self.closed = True


class FakeTLS:
    def __init__(self): self.hosts = []
    def wrap_socket(self, sock, server_hostname): self.hosts.append(server_hostname); return sock


def response(status=200, headers=None, body=b""):
    if headers is None: headers = {"Content-Type": "text/html; charset=utf-8", "Content-Length": str(len(body))}
    return (f"HTTP/1.1 {status} Test\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "Connection: close\r\n\r\n").encode() + body


def test_url_policy_blocks_non_https_credentials_bad_ports_local_and_ip_literals():
    target = normalize_url("https://EXAMPLE.com/path?q=a%20b#x")
    assert target.url == "https://example.com/path?q=a%20b"
    assert target.path_query == "/path?q=a%20b"
    for url, code in [("http://example.com", "scheme_blocked"), ("https://127.0.0.1", "ip_literal_blocked"),
                      ("https://[::1]", "ip_literal_blocked"), ("https://u:p@example.com", "credentials_blocked"),
                      ("https://example.com:444", "port_blocked"), ("https://localhost", "non_public_hostname"),
                      ("https://a.local", "non_public_hostname"), ("https://example.com/a b", "invalid_url")]:
        with pytest.raises(AuditFetchError) as err: normalize_url(url)
        assert err.value.code == code


def test_dns_rejects_private_and_mixed_public_private_answers():
    fetcher = SafeHTTPSFetcher(resolver=resolver("93.184.216.34"))
    assert fetcher._public_ips("example.com") == [ipaddress.ip_address("93.184.216.34")]
    for ips in [("127.0.0.1",), ("10.0.0.2",), ("93.184.216.34", "169.254.1.3")]:
        with pytest.raises(AuditFetchError) as err: SafeHTTPSFetcher(resolver=resolver(*ips))._public_ips("example.com")
        assert err.value.code == "non_public_address"


def test_fetch_pins_checked_ip_and_preserves_tls_hostname():
    sock = FakeSocket(response(body=b"<html><title>OK</title></html>")); tls = FakeTLS(); used = []
    fetcher = SafeHTTPSFetcher(resolver=resolver("93.184.216.34"),
                               socket_factory=lambda addr, timeout: used.append(addr) or sock, tls_context=tls)
    snap = fetcher.fetch("https://example.com/path")
    assert used == [("93.184.216.34", 443)] and tls.hosts == ["example.com"]
    assert b"Host: example.com\r\n" in sock.sent and b"GET /path HTTP/1.1" in sock.sent
    assert snap.status == 200 and snap.body_sha256 == hashlib.sha256(snap.body).hexdigest()


def test_redirect_to_private_literal_is_blocked_before_second_connection():
    sock = FakeSocket(response(302, {"Location": "https://127.0.0.1/admin", "Content-Length": "0"}))
    used = []
    fetcher = SafeHTTPSFetcher(resolver=resolver("93.184.216.34"),
                               socket_factory=lambda addr, timeout: used.append(addr) or sock, tls_context=FakeTLS())
    with pytest.raises(AuditFetchError) as err: fetcher.fetch("https://example.com/start")
    assert err.value.code == "ip_literal_blocked" and used == [("93.184.216.34", 443)]


def test_redirect_loop_is_blocked():
    socks = [FakeSocket(response(302, {"Location": "/b", "Content-Length": "0"})),
             FakeSocket(response(302, {"Location": "/a", "Content-Length": "0"}))]
    fetcher = SafeHTTPSFetcher(resolver=resolver("93.184.216.34"),
                               socket_factory=lambda *a, **k: socks.pop(0), tls_context=FakeTLS())
    with pytest.raises(AuditFetchError) as err: fetcher.fetch("https://example.com/a")
    assert err.value.code == "redirect_loop"


def test_response_size_and_compression_are_bounded():
    fetcher = SafeHTTPSFetcher(max_bytes=4, resolver=resolver("93.184.216.34"),
        socket_factory=lambda *a, **k: FakeSocket(response(body=b"12345")), tls_context=FakeTLS())
    with pytest.raises(AuditFetchError) as err: fetcher.fetch("https://example.com/")
    assert err.value.code == "response_too_large"
    fetcher2 = SafeHTTPSFetcher(resolver=resolver("93.184.216.34"),
        socket_factory=lambda *a, **k: FakeSocket(response(headers={"Content-Type":"text/html","Content-Encoding":"gzip","Content-Length":"4"}, body=b"test")),
        tls_context=FakeTLS())
    with pytest.raises(AuditFetchError) as err: fetcher2.fetch("https://example.com/")
    assert err.value.code == "compressed_response_blocked"


class StubFetcher:
    def fetch(self, url):
        from ai_digital_growth.audit import Snapshot
        body = b"<html><head><title> </title></head><body><img src='/x'><h1>A</h1><h1>B</h1><a href='/empty'></a></body></html>"
        return Snapshot(url, url, 200, {"content-type":"text/html"}, body, datetime.now(timezone.utc).isoformat(),
                        1.0, (), hashlib.sha256(body).hexdigest())


def test_auditor_emits_evidence_linked_findings():
    report = WebsiteAuditor(StubFetcher()).audit("https://example.com/")
    ids = {f["rule_id"] for f in report["findings"]}
    assert {"seo.missing_title", "seo.missing_meta_description", "mobile.missing_viewport",
            "a11y.missing_html_lang", "a11y.images_missing_alt", "a11y.empty_link_name", "content.multiple_h1"} <= ids
    assert all(f["evidence"]["body_sha256"] == report["body_sha256"] for f in report["findings"])
    assert "not proof of commercial impact" in report["limitations"][-1]
