"""Single-page, bounded HTTPS audit. No crawling, JS execution, forms, or sending."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

TOOL_VERSION = "adg-audit/0.1.0"
RULE_VERSION = "website-static-checks/0.1.0"
REDIRECTS = {301, 302, 303, 307, 308}
LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.I)


class AuditFetchError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@dataclass(frozen=True)
class Target:
    url: str
    host: str
    path_query: str


def normalize_url(raw: str) -> Target:
    if not isinstance(raw, str) or not raw or any(ord(c) < 33 or ord(c) == 127 for c in raw):
        raise AuditFetchError("invalid_url", "URL must be non-empty and contain no whitespace/control characters.")
    try:
        p = urlsplit(raw)
        port = p.port
    except ValueError as e:
        raise AuditFetchError("invalid_url", "Malformed URL authority or port.") from e
    if p.scheme.lower() != "https":
        raise AuditFetchError("scheme_blocked", "Only HTTPS is allowed.")
    if not p.hostname or not p.netloc:
        raise AuditFetchError("invalid_url", "URL must contain a hostname.")
    if p.username is not None or p.password is not None or "@" in p.netloc:
        raise AuditFetchError("credentials_blocked", "Embedded URL credentials are not allowed.")
    if port not in (None, 443):
        raise AuditFetchError("port_blocked", "Only port 443 is allowed.")
    host = p.hostname.rstrip(".").lower()
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise AuditFetchError("ip_literal_blocked", "Use a public DNS hostname, not an IP literal.")
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as e:
        raise AuditFetchError("invalid_host", "Hostname IDNA normalization failed.") from e
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".home", ".test", ".invalid")):
        raise AuditFetchError("non_public_hostname", "Local, reserved, and test hostnames are blocked.")
    if len(host) > 253 or "." not in host or any(not LABEL.fullmatch(x) for x in host.split(".")):
        raise AuditFetchError("invalid_host", "A valid fully-qualified DNS hostname is required.")
    path = quote(p.path or "/", safe="/%:@!$&'()*+,;=-._~")
    query = quote(p.query, safe="/?:@!$&'()*+,;=%-._~")
    target = path + ("?" + query if query else "")
    return Target(urlunsplit(("https", host, path, query, "")), host, target)


@dataclass(frozen=True)
class Snapshot:
    requested_url: str
    final_url: str
    status: int
    headers: dict[str, str]
    body: bytes
    captured_at: str
    elapsed_ms: float
    redirects: tuple[str, ...]
    body_sha256: str


Resolver = Callable[..., list[tuple[Any, ...]]]
SocketFactory = Callable[..., Any]


class SafeHTTPSFetcher:
    def __init__(self, *, timeout: float = 5, max_bytes: int = 1_000_000, max_redirects: int = 5,
                 resolver: Resolver | None = None, socket_factory: SocketFactory | None = None,
                 tls_context: Any | None = None):
        if timeout <= 0 or max_bytes <= 0 or max_redirects < 0:
            raise ValueError("timeout/max_bytes must be positive and max_redirects non-negative")
        self.timeout, self.max_bytes, self.max_redirects = float(timeout), int(max_bytes), int(max_redirects)
        self.resolver = resolver or socket.getaddrinfo
        self.socket_factory = socket_factory or socket.create_connection
        self.tls = tls_context or ssl.create_default_context()

    def _public_ips(self, host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        try:
            answers = self.resolver(host, 443, type=socket.SOCK_STREAM)
        except OSError as e:
            raise AuditFetchError("dns_failed", "DNS lookup failed.") from e
        if not answers:
            raise AuditFetchError("dns_empty", "DNS returned no addresses.")
        out = []
        for answer in answers:
            try:
                ip = ipaddress.ip_address(answer[4][0].split("%", 1)[0])
            except (ValueError, IndexError, TypeError) as e:
                raise AuditFetchError("dns_invalid_answer", "DNS returned an invalid address.") from e
            checked = ip.ipv4_mapped if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped else ip
            if not checked.is_global or checked.is_multicast or checked.is_unspecified:
                raise AuditFetchError("non_public_address", "DNS includes a non-public or reserved IP address.")
            if ip not in out:
                out.append(ip)
        return out

    def _one(self, target: Target) -> tuple[int, dict[str, str], bytes, float]:
        errors = []
        # Connect directly to the vetted numeric address, retaining hostname TLS verification.
        for ip in self._public_ips(target.host):
            raw = tls = None
            start = time.monotonic()
            try:
                raw = self.socket_factory((str(ip), 443), timeout=self.timeout)
                raw.settimeout(self.timeout)
                tls = self.tls.wrap_socket(raw, server_hostname=target.host)
                tls.settimeout(self.timeout)
                req = (f"GET {target.path_query} HTTP/1.1\r\nHost: {target.host}\r\n"
                       "User-Agent: AI-Digital-Growth-AuditBot/0.1\r\n"
                       "Accept: text/html,application/xhtml+xml;q=0.9\r\n"
                       "Accept-Encoding: identity\r\nConnection: close\r\n\r\n").encode("ascii")
                tls.sendall(req)
                response = http.client.HTTPResponse(tls, method="GET")
                response.begin()
                headers = {k.lower(): v.strip() for k, v in response.getheaders()}
                status = response.status
                # Redirects have no HTML requirement and their bodies are deliberately ignored.
                if status in REDIRECTS:
                    elapsed = (time.monotonic() - start) * 1000
                    response.close()
                    return status, headers, b"", elapsed
                length = headers.get("content-length")
                if length:
                    try:
                        size = int(length)
                    except ValueError as e:
                        raise AuditFetchError("invalid_content_length", "Invalid Content-Length.") from e
                    if size < 0 or size > self.max_bytes:
                        raise AuditFetchError("response_too_large", "Response exceeds configured byte limit.")
                if headers.get("content-encoding", "identity").lower() not in ("", "identity"):
                    raise AuditFetchError("compressed_response_blocked", "Compressed responses are disabled.")
                mime = headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if mime not in ("text/html", "application/xhtml+xml"):
                    raise AuditFetchError("unsupported_content_type", f"Expected HTML; received {mime or 'no Content-Type'}.")
                body = response.read(self.max_bytes + 1)
                if len(body) > self.max_bytes:
                    raise AuditFetchError("response_too_large", "Response exceeds configured byte limit.")
                elapsed = (time.monotonic() - start) * 1000
                response.close()
                return status, headers, body, elapsed
            except AuditFetchError:
                raise
            except (OSError, ssl.SSLError, http.client.HTTPException) as e:
                errors.append(type(e).__name__)
            finally:
                for sock in (tls, raw):
                    if sock is not None:
                        try:
                            sock.close()
                        except OSError:
                            pass
        raise AuditFetchError("connection_failed", f"Could not connect to a vetted public IP ({', '.join(errors)}).")

    def fetch(self, raw_url: str) -> Snapshot:
        current = normalize_url(raw_url)
        requested = current.url
        visited = {current.url}
        chain: list[str] = []
        total_ms = 0.0
        while True:
            status, headers, body, elapsed = self._one(current)
            total_ms += elapsed
            if status in REDIRECTS:
                location = headers.get("location")
                if not location:
                    raise AuditFetchError("redirect_without_location", "Redirect response lacks Location.")
                if len(chain) >= self.max_redirects:
                    raise AuditFetchError("too_many_redirects", "Redirect limit exceeded.")
                nxt = normalize_url(urljoin(current.url, location))
                if nxt.url in visited:
                    raise AuditFetchError("redirect_loop", "Redirect loop detected.")
                chain.append(current.url)
                visited.add(nxt.url)
                current = nxt
                continue
            return Snapshot(requested, current.url, status, headers, body, datetime.now(timezone.utc).isoformat(),
                           round(total_ms, 2), tuple(chain), hashlib.sha256(body).hexdigest())


class _Summary(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_bits: list[str] = []
        self.in_title = False
        self.lang = self.description = self.viewport = self.robots = None
        self.h1 = self.images = self.images_missing_alt = self.empty_links = 0
        self.anchors: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): v for k, v in attrs}
        if tag == "html": self.lang = (a.get("lang") or "").strip() or None
        elif tag == "title": self.in_title = True
        elif tag == "meta":
            name, value = (a.get("name") or "").strip().lower(), (a.get("content") or "").strip()
            if name == "description": self.description = value or None
            elif name == "viewport": self.viewport = value or None
            elif name == "robots": self.robots = value.lower() or None
        elif tag == "h1": self.h1 += 1
        elif tag == "img":
            self.images += 1
            if a.get("alt") is None: self.images_missing_alt += 1
            elif a.get("alt") and self.anchors: self.anchors[-1]["labeled_child"] = True
        elif tag == "svg" and self.anchors and (a.get("aria-label") or "").strip(): self.anchors[-1]["labeled_child"] = True
        elif tag == "a":
            self.anchors.append({"text": [], "aria": (a.get("aria-label") or "").strip(),
                                 "title": (a.get("title") or "").strip(), "labeled_child": False})

    def handle_endtag(self, tag: str) -> None:
        if tag == "title": self.in_title = False
        elif tag == "a" and self.anchors:
            a = self.anchors.pop()
            if not (" ".join(a["text"]).strip() or a["aria"] or a["title"] or a["labeled_child"]): self.empty_links += 1

    def handle_data(self, data: str) -> None:
        if self.in_title: self.title_bits.append(data)
        for anchor in self.anchors: anchor["text"].append(data)

    @property
    def title(self) -> str | None:
        return " ".join(" ".join(self.title_bits).split()) or None

    @property
    def noindex(self) -> bool:
        if not self.robots: return False
        tokens = {x.strip() for x in self.robots.replace(";", ",").split(",")}
        return bool(tokens & {"noindex", "none"})


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    description: str
    severity: str
    confidence: float
    evidence: dict[str, Any]


class WebsiteAuditor:
    def __init__(self, fetcher: SafeHTTPSFetcher | None = None): self.fetcher = fetcher or SafeHTTPSFetcher()

    def audit(self, url: str) -> dict[str, Any]:
        s = self.fetcher.fetch(url)
        p = _Summary()
        try:
            p.feed(s.body.decode("utf-8", errors="replace")); p.close()
        except Exception as e:
            raise AuditFetchError("html_parse_failed", "HTML snapshot parsing failed.") from e
        metrics = {"title": p.title, "meta_description_present": p.description is not None,
                   "viewport_present": p.viewport is not None, "html_lang": p.lang, "h1_count": p.h1,
                   "image_count": p.images, "images_missing_alt": p.images_missing_alt,
                   "empty_link_text_count": p.empty_links, "robots_meta": p.robots, "noindex_present": p.noindex}
        base = {"url": s.final_url, "captured_at": s.captured_at, "body_sha256": s.body_sha256}
        findings: list[Finding] = []
        def add(rule: str, title: str, desc: str, severity: str, loc: str, observed: Any):
            findings.append(Finding(rule, title, desc, severity, 0.95,
                                    {**base, "location": loc, "observed": observed}))
        if s.status >= 500: add("http.server_error", "Page returned a server error", f"HTTP {s.status}; response alone does not establish the cause.", "high", "HTTP status", s.status)
        elif s.status >= 400: add("http.client_error", "Page returned a client error", f"HTTP {s.status}; verify this is the intended public page.", "medium", "HTTP status", s.status)
        checks = [
            (not p.title, "seo.missing_title", "Page title is missing", "No non-empty title element was observed.", "medium", "head/title", None),
            (p.description is None, "seo.missing_meta_description", "Meta description is missing", "No non-empty meta description was observed.", "low", "head/meta description", None),
            (p.viewport is None, "mobile.missing_viewport", "Viewport declaration is missing", "No non-empty viewport meta element was observed.", "medium", "head/meta viewport", None),
            (p.lang is None, "a11y.missing_html_lang", "Document language is not declared", "The root html element has no lang attribute.", "low", "html[lang]", None),
            (p.h1 == 0, "content.missing_h1", "No level-one heading was observed", "No h1 element was found in the response.", "low", "body/h1", 0),
            (p.images_missing_alt > 0, "a11y.images_missing_alt", "Images without alt attributes were observed", f"{p.images_missing_alt} of {p.images} images lacked an alt attribute.", "medium", "img[alt]", p.images_missing_alt),
            (p.empty_links > 0, "a11y.empty_link_name", "Links without accessible names were observed", f"{p.empty_links} anchors lacked text or an accessible label.", "medium", "anchor elements", p.empty_links),
            (p.noindex, "seo.meta_noindex", "Page requests non-indexing", "Robots metadata includes noindex/none; confirm intentional.", "medium", "meta robots", p.robots),
        ]
        for condition, rule, title, desc, severity, loc, observed in checks:
            if condition: add(rule, title, desc, severity, loc, observed)
        if p.h1 > 1: add("content.multiple_h1", "Multiple level-one headings were observed", "Review the intended document outline.", "info", "body/h1", p.h1)
        return {
            "tool_version": TOOL_VERSION, "rule_version": RULE_VERSION,
            "requested_url": s.requested_url, "final_url": s.final_url, "status_code": s.status,
            "content_type": s.headers.get("content-type", "").split(";", 1)[0].lower(),
            "captured_at": s.captured_at, "elapsed_ms": s.elapsed_ms, "body_sha256": s.body_sha256,
            "redirect_chain": list(s.redirects), "metrics": metrics,
            "findings": [asdict(x) for x in findings],
            "limitations": ["Static single-response audit; JavaScript-rendered content is not inspected.",
                "No performance lab/field metrics, screenshot review, full crawl or accessibility-tree analysis was done.",
                "Findings are observations, not proof of commercial impact; independent human verification remains required."],
        }


def report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one bounded HTTPS static audit. No crawling or outbound messaging.")
    parser.add_argument("url", help="One public HTTPS page URL")
    parser.add_argument("--output", type=Path, help="Write report JSON to this path instead of stdout")
    args = parser.parse_args(argv)
    try:
        rendered = report_json(WebsiteAuditor().audit(args.url)) + "\n"
        if args.output: args.output.write_text(rendered, encoding="utf-8")
        else: print(rendered, end="")
        return 0
    except AuditFetchError as e:
        print(json.dumps({"error_code": e.code, "error": e.message}), file=sys.stderr); return 2
    except OSError as e:
        print(json.dumps({"error_code": "output_error", "error": str(e)}), file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
