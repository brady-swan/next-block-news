"""Canonical source-quality registry and deterministic source classification.

Tier is receipt quality, never evidence class.  A registry match cannot by itself prove
that a page supports a story or that two pages are independent.
"""
from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

VALID_TIERS = {"p0", "t1", "t2", "t3", "t4"}
VALID_CATEGORIES = {
    "authority", "market_infrastructure", "reporting", "research_data",
    "technical", "social", "discovery", "aggregator", "syndication",
}
VALID_ROLES = {
    "official", "reporting", "research", "technical", "discovery",
    "aggregator", "syndication", "blocked",
}
TIER_RANK = {"p0": 0, "t1": 1, "t2": 2, "t3": 3, "t4": 4, "unknown": 5}
_HANDLE_RE = re.compile(r"@([A-Za-z0-9_]{1,30})")


class PolicyError(RuntimeError):
    """The canonical policy is invalid; startup must fail closed."""


def normalize_host(value: str) -> str:
    value = (value or "").strip().lower().rstrip(".")
    if "://" in value:
        value = urlsplit(value).hostname or ""
    if value.startswith("www."):
        value = value[4:]
    for prefix in ("m.", "mobile."):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value


def normalize_alias(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def normalize_handle(value: str) -> str:
    return (value or "").strip().lstrip("@").lower()


def normalize_url(value: str) -> str:
    try:
        parts = urlsplit((value or "").strip())
        host = normalize_host(parts.hostname or "")
        scheme = (parts.scheme or "https").lower()
        path = re.sub(r"/{2,}", "/", parts.path or "/")
        path = path.rstrip("/") or "/"
        return urlunsplit((scheme, host, path, parts.query, ""))
    except Exception:  # noqa: BLE001
        return (value or "").strip()


def content_fingerprint(text: str) -> str:
    """A MinHash signature so boilerplate-modified wire copies still collapse."""
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())[:4000]
    if not tokens:
        return ""
    width = min(5, len(tokens))
    shingles = {" ".join(tokens[i:i + width]) for i in range(len(tokens) - width + 1)}
    minima = []
    for seed in range(32):
        salt = seed.to_bytes(2, "big")
        minima.append(min(
            int.from_bytes(hashlib.blake2s(salt + shingle.encode(), digest_size=4).digest(), "big")
            for shingle in shingles
        ))
    return ".".join(f"{value:08x}" for value in minima)


def content_fingerprints_match(left: str, right: str, min_similarity: float = 0.55) -> bool:
    if not left or not right:
        return False
    left_parts, right_parts = left.split("."), right.split(".")
    if len(left_parts) == len(right_parts) == 32:
        agreement = sum(a == b for a, b in zip(left_parts, right_parts)) / 32
        return agreement >= min_similarity
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count() <= 6
    except ValueError:
        return left == right


def artifact_fingerprint(url: str) -> str:
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()[:24] if normalized else ""


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    display_name: str
    tier: str
    category: str
    independence_key: str
    ownership_key: str
    receipt_role: str
    url: str
    domain: str
    handle: str
    matched_by: str

    @property
    def known(self) -> bool:
        return self.tier != "unknown"

    @property
    def base_receipt_eligible(self) -> bool:
        return self.tier in {"p0", "t1", "t2"} and self.receipt_role not in {
            "aggregator", "syndication", "blocked", "discovery",
        }

    @property
    def official(self) -> bool:
        return self.tier == "p0" and self.receipt_role == "official"

    @property
    def trusted_own_research(self) -> bool:
        """Whether this source may stand alone for research it says it published.

        This does not authenticate third-party facts or allegations quoted by the source;
        determining whether a claim is actually the source's own work remains editorial.
        """
        return (
            self.source_id == "bitcoin-policy-institute"
            and self.receipt_role == "research"
        )


@dataclass(frozen=True)
class SourceEntry:
    source_id: str
    display_name: str
    tier: str
    category: str
    independence_key: str
    ownership_key: str
    receipt_role: str
    domains: tuple[str, ...]
    aliases: tuple[str, ...]
    handles: tuple[str, ...]
    url_prefixes: tuple[str, ...]
    handle_ownership: tuple[tuple[str, str], ...]


class SourcePolicy:
    def __init__(self, entries: list[SourceEntry]):
        self.entries = tuple(entries)
        self.by_id = {e.source_id: e for e in entries}
        self.by_alias = {a: e for e in entries for a in e.aliases}
        self.by_handle = {h: e for e in entries for h in e.handles}
        self.by_domain = {d: e for e in entries for d in e.domains}
        self.by_prefix = {p: e for e in entries for p in e.url_prefixes}
        self._domains = sorted(self.by_domain, key=len, reverse=True)
        self._prefixes = sorted(self.by_prefix, key=len, reverse=True)

    @classmethod
    def from_path(cls, path: Path | str) -> "SourcePolicy":
        policy_path = Path(path)
        try:
            raw = tomllib.loads(policy_path.read_text())
        except Exception as exc:  # noqa: BLE001
            raise PolicyError(f"cannot load source policy {policy_path}: {exc}") from exc
        if raw.get("version") != 1:
            raise PolicyError("source policy version must be 1")
        rows = raw.get("sources")
        if not isinstance(rows, list) or not rows:
            raise PolicyError("source policy must contain [[sources]] entries")

        entries: list[SourceEntry] = []
        seen: dict[str, dict[str, str]] = {
            "id": {}, "domain": {}, "alias": {}, "handle": {}, "prefix": {},
        }
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise PolicyError(f"source entry {index} must be a table")
            required = ("id", "display_name", "tier", "category", "independence_key",
                        "receipt_role", "domains", "aliases", "handles")
            missing = [k for k in required if k not in row]
            if missing:
                raise PolicyError(f"source entry {index} missing: {', '.join(missing)}")
            source_id = normalize_alias(str(row["id"]))
            display_name = str(row["display_name"]).strip()
            tier = normalize_alias(str(row["tier"]))
            category = normalize_alias(str(row["category"]))
            role = normalize_alias(str(row["receipt_role"]))
            independence_key = normalize_alias(str(row["independence_key"]))
            if not source_id or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", source_id):
                raise PolicyError(f"source entry {index}: invalid id {source_id!r}")
            if not display_name or not independence_key:
                raise PolicyError(f"{source_id}: display_name and independence_key are required")
            if tier not in VALID_TIERS:
                raise PolicyError(f"{source_id}: invalid tier {tier!r}")
            if category not in VALID_CATEGORIES:
                raise PolicyError(f"{source_id}: invalid category {category!r}")
            if role not in VALID_ROLES:
                raise PolicyError(f"{source_id}: invalid receipt_role {role!r}")
            for field in ("domains", "aliases", "handles"):
                if not isinstance(row[field], list):
                    raise PolicyError(f"{source_id}: {field} must be an array")
            if not isinstance(row.get("url_prefixes", []), list):
                raise PolicyError(f"{source_id}: url_prefixes must be an array")
            if not isinstance(row.get("handle_ownership", {}), dict):
                raise PolicyError(f"{source_id}: handle_ownership must be a table")
            domains = tuple(normalize_host(v) for v in row["domains"] if normalize_host(v))
            aliases = tuple(normalize_alias(v) for v in row["aliases"] if normalize_alias(v))
            handles = tuple(normalize_handle(v) for v in row["handles"] if normalize_handle(v))
            prefixes = tuple(normalize_url(v) for v in row.get("url_prefixes", []) if v)
            handle_ownership = tuple(
                (normalize_handle(handle), normalize_alias(str(owner)))
                for handle, owner in row.get("handle_ownership", {}).items()
            )
            if any(handle not in handles or not owner for handle, owner in handle_ownership):
                raise PolicyError(f"{source_id}: handle_ownership keys must name configured handles")
            for field, values in (("domains", domains), ("aliases", aliases),
                                  ("handles", handles), ("url_prefixes", prefixes)):
                if len(values) != len(set(values)):
                    raise PolicyError(f"{source_id}: duplicate value in {field}")
            entry = SourceEntry(
                source_id=source_id,
                display_name=display_name,
                tier=tier,
                category=category,
                independence_key=independence_key,
                ownership_key=normalize_alias(str(row.get("ownership_key") or row["independence_key"])),
                receipt_role=role,
                domains=domains,
                aliases=aliases,
                handles=handles,
                url_prefixes=prefixes,
                handle_ownership=handle_ownership,
            )
            for kind, values in (("id", (entry.source_id,)), ("domain", domains),
                                 ("alias", aliases), ("handle", handles),
                                 ("prefix", prefixes)):
                for value in values:
                    prior = seen[kind].get(value)
                    if prior and prior != source_id:
                        raise PolicyError(f"duplicate {kind} {value!r}: {prior}, {source_id}")
                    seen[kind][value] = source_id
            entries.append(entry)
        return cls(entries)

    def classify(self, url: str = "", source_name: str = "") -> SourceRef:
        normalized_url = normalize_url(url)
        host = normalize_host(urlsplit(normalized_url).hostname or "")
        handle = ""
        if host in {"x.com", "twitter.com"}:
            parts = [p for p in urlsplit(normalized_url).path.split("/") if p]
            if parts:
                handle = normalize_handle(parts[0])
        elif not host and (match := _HANDLE_RE.search(source_name or "")):
            handle = normalize_handle(match.group(1))

        x_host = host in {"x.com", "twitter.com"}
        entry = self.by_handle.get(handle) if handle and (x_host or not host) else None
        matched_by = "handle" if entry else ""
        if not entry:
            for prefix in self._prefixes:
                candidate_parts = urlsplit(normalized_url.lower())
                prefix_parts = urlsplit(prefix.lower())
                candidate_path = candidate_parts.path.rstrip("/") or "/"
                prefix_path = prefix_parts.path.rstrip("/") or "/"
                same_origin = (candidate_parts.scheme, candidate_parts.hostname) == (
                    prefix_parts.scheme, prefix_parts.hostname)
                path_match = (prefix_path == "/" or candidate_path == prefix_path
                              or candidate_path.startswith(prefix_path + "/"))
                query_match = not prefix_parts.query or candidate_parts.query == prefix_parts.query
                if same_origin and path_match and query_match:
                    entry, matched_by = self.by_prefix[prefix], "url_prefix"
                    break
        if not entry and host:
            for domain in self._domains:
                if host == domain or host.endswith("." + domain):
                    entry, matched_by = self.by_domain[domain], "domain"
                    break
        # Aliases are labels for hostless provider lookups, never an identity override
        # for a mismatched URL supplied by a feed, model, or external service.
        if not entry and not host:
            alias = normalize_alias(source_name)
            entry = self.by_alias.get(alias)
            matched_by = "alias" if entry else ""
        if not entry and handle and (x_host or not host):
            entry = self.by_handle.get(handle)
            matched_by = "handle" if entry else ""

        if not entry:
            return SourceRef("unknown", source_name or host or "Unknown", "unknown", "discovery",
                             f"unknown:{host or normalize_alias(source_name)}", "unknown",
                             "discovery", normalized_url, host, handle, "unknown")
        source_id, display_name = entry.source_id, entry.display_name
        independence_key, ownership_key = entry.independence_key, entry.ownership_key
        if entry.source_id == "official-x-watch" and handle:
            source_id = f"official-x-{handle}"
            display_name = f"@{handle}"
            independence_key = source_id
            owners = dict(entry.handle_ownership)
            ownership_key = owners.get(handle, source_id)
        return SourceRef(source_id, display_name, entry.tier, entry.category,
                         independence_key, ownership_key, entry.receipt_role,
                         normalized_url, host, handle, matched_by)

    def rank(self, refs: list[SourceRef]) -> list[SourceRef]:
        return sorted(refs, key=lambda ref: (TIER_RANK[ref.tier], ref.display_name.lower()))


POLICY_PATH = Path(__file__).resolve().parent.parent / "config" / "source_tiers.toml"
POLICY = SourcePolicy.from_path(POLICY_PATH)


def classify(url: str = "", source_name: str = "") -> SourceRef:
    return POLICY.classify(url, source_name)
