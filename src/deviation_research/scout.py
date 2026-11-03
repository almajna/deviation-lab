"""Bounded public metadata searches. Network content is never executable."""
import hashlib
import json
from pathlib import Path
import time
import signal
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit
from urllib.request import build_opener, HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request
import xml.etree.ElementTree as ET

from .records import sha, write

QUERIES = ["prediction market strategic manipulation", "branch and bound certificate verification", "forecast aggregation resource allocation"]
HOSTS = {"export.arxiv.org", "api.semanticscholar.org", "api.github.com", "api.crossref.org"}
MAX_BYTES = 600_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("redirect refused")


def request(url, timeout):
    target = urlsplit(url)
    if target.scheme != "https" or target.hostname not in HOSTS or target.username or target.port:
        raise ValueError("unapproved source endpoint")
    opener = build_opener(ProxyHandler({}), HTTPSHandler(), NoRedirect())
    req = Request(url, headers={"User-Agent": "DEVIATION-research/1.0 (public metadata; bounded academic research)",
                               "Accept": "application/json, application/atom+xml"})
    with opener.open(req, timeout=timeout) as response:
        body = response.read(MAX_BYTES+1)
        if len(body) > MAX_BYTES:
            raise ValueError("response byte budget exceeded")
        return body, {"http_status": response.status, "final_url": response.url}


def endpoints(query):
    return {
        "arxiv": "https://export.arxiv.org/api/query?"+urlencode({"search_query": "all:"+query, "max_results": 3}),
        "semantic_scholar": "https://api.semanticscholar.org/graph/v1/paper/search?"+urlencode({
            "query": query, "limit": 3, "fields": "title,authors,year,url,externalIds,venue"}),
        "conference": "https://api.crossref.org/works?"+urlencode({"query": query,
            "filter": "type:proceedings-article", "rows": 3, "select": "DOI,title,author,published,URL"}),
        "github": "https://api.github.com/search/repositories?"+urlencode({"q": query, "per_page": 3}),
    }


def normalize(provider, body):
    if provider == "arxiv":
        if b"<!DOCTYPE" in body or b"<!ENTITY" in body:
            raise ValueError("XML declarations refused")
        root = ET.fromstring(body)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        return [{"title": " ".join(e.findtext("a:title", "", ns).split()),
                 "url": e.findtext("a:id", "", ns).replace("http://", "https://"),
                 "authors": [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)],
                 "year": e.findtext("a:published", "", ns)[:4]} for e in root.findall("a:entry", ns)]
    value = json.loads(body)
    if provider == "semantic_scholar":
        return [{"title": r["title"], "url": r["url"], "authors": [a["name"] for a in r["authors"]],
                 "year": r.get("year"), "external_ids": r.get("externalIds", {}), "venue": r.get("venue")} for r in value.get("data", [])]
    if provider == "conference":
        return [{"title": r.get("title", [""])[0], "url": r["URL"], "doi": r["DOI"],
                 "authors": [a.get("given", "")+" "+a.get("family", "") for a in r.get("author", [])]}
                for r in value["message"].get("items", [])]
    return [{"title": r["full_name"], "url": r["html_url"], "revision": None,
             "license": (r.get("license") or {}).get("spdx_id"), "code_execution": "NEVER"} for r in value.get("items", [])]


def scout(destination, *, queries=None, max_requests=12, wall_seconds=65, fetch=request):
    if type(max_requests) is not int or not 1 <= max_requests <= 12 or not 0 < wall_seconds <= 90:
        raise ValueError("invalid scout budget")
    queries = QUERIES if queries is None else queries
    if not 1 <= len(queries) <= 3 or any(not isinstance(q, str) or not 1 <= len(q) <= 160 for q in queries):
        raise ValueError("invalid search query")
    started = time.monotonic()
    records = []
    for query in queries:
        for provider, url in endpoints(query).items():
            remaining = wall_seconds-(time.monotonic()-started)
            if len(records) >= max_requests or remaining <= 0:
                break
            receipt = {"provider": provider, "query": query, "request_url": url,
                       "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
            try:
                # A socket timeout does not bound DNS or slow streaming. A real
                # process timer caps the complete request on supported POSIX hosts.
                def timeout_handler(*_):
                    raise TimeoutError("request wall budget exhausted")
                previous = signal.signal(signal.SIGALRM, timeout_handler)
                signal.setitimer(signal.ITIMER_REAL, min(5, remaining))
                try:
                    response = fetch(url, min(5, remaining))
                    if isinstance(response, tuple):
                        body, response_meta = response
                        receipt.update(response_meta)
                    else:
                        body = response
                    if len(body) > MAX_BYTES:
                        raise ValueError("response byte budget exceeded")
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    signal.signal(signal.SIGALRM, previous)
                receipt.update(status="ok", response_bytes=len(body), response_sha256=hashlib.sha256(body).hexdigest(),
                               results=normalize(provider, body)[:3])
            except Exception as exc:
                receipt.update(status="failed", error=type(exc).__name__+": "+str(exc)[:240], results=[])
                if hasattr(exc, "code"):
                    receipt["http_status"] = exc.code
            records.append(receipt)
    result = {"version": "research-scout-1", "mode": "PUBLIC_METADATA_NO_INFERENCE",
              "requests": records, "budget": {"request_cap": max_requests, "wall_seconds": wall_seconds,
              "per_response_bytes": MAX_BYTES, "paid_spend_usd": 0},
              "warning": "Discovery metadata is not proof of a paper's claims or novelty. Failed searches remain visible."}
    result["sha256"] = sha(result)
    write(destination, result)
    return result


def validate_sources(registry):
    if registry.get("version") != "research-sources-1":
        raise ValueError("source registry version")
    ids = set()
    for source in registry["sources"]:
        if source["id"] in ids:
            raise ValueError("duplicate citation")
        ids.add(source["id"])
        if not source["title"] or not source["authors"]:
            raise ValueError("missing citation identity")
        for field in ("url", "verification_url"):
            url = urlsplit(source[field])
            if url.scheme != "https" or not url.hostname or url.username:
                raise ValueError("invalid citation URL")
        if source.get("identity_sha256") != sha({k: source[k] for k in ("title", "authors", "url")}):
            raise ValueError("citation identity changed without verification")
        if source["verification"]["method"] != "primary_metadata_read" or not source["verification"].get("retrieved_on"):
            raise ValueError("unverified citation")
    return ids
