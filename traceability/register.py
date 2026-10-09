#### created by Diego G. Salas
#
# Verification register. Every figure that feeds a model is logged with its source,
# retrieval date and confirmation status, and only confirmed figures may be used.
#   source_type = worldbank  -> source_ref is a World Bank indicator code, the country comes from --country
#   source_type = derived    -> source_ref is an expression over other claim ids, e.g. C01*C02/1000
#   source_type = none       -> no checkable source, so the figure is unconfirmable and excluded
# Each API response is cached byte for byte with its SHA-256, so a later run can prove
# which data the verdict was based on.
import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

API = "https://api.worldbank.org/v2/country/{country}/indicator/{code}?format=json&date={year}"


def fetch_worldbank(code, year, country, cache_dir, offline=False):
    """Return the value or None, and the provenance dict. Reads the cache first and downloads if allowed."""
    url = API.format(country=country, code=code, year=year)
    path = os.path.join(cache_dir, f"{country}_{code}_{year}.json")
    meta_path = path + ".meta.json"
    if os.path.exists(path):
        raw = open(path, "rb").read()
        meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
        retrieved = meta.get("retrieved_at", "")
    elif offline:
        return None, {"source_url": url, "retrieved_at": "", "sha256": "", "note": "not in cache"}
    else:
        with urllib.request.urlopen(url, timeout=30) as resp:
            raw = resp.read()
        retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
        os.makedirs(cache_dir, exist_ok=True)
        open(path, "wb").write(raw)
        json.dump({"source_url": url, "retrieved_at": retrieved}, open(meta_path, "w"), indent=1)
    payload = json.loads(raw)
    rows = payload[1] if len(payload) > 1 and payload[1] else []
    value = next((r["value"] for r in rows if r["date"] == str(year) and r["value"] is not None), None)
    return value, {"source_url": url, "retrieved_at": retrieved,
                   "sha256": hashlib.sha256(raw).hexdigest(), "note": ""}


def _derive(expr, observed):
    """Evaluate an arithmetic expression over confirmed claim ids, digits, ids and + - * / only."""
    if not re.fullmatch(r"[C0-9.+\-*/() ]+", expr):
        raise ValueError(f"unsupported expression: {expr}")
    ids = re.findall(r"C\d+", expr)
    if any(observed.get(i) is None for i in ids):
        return None
    return eval(re.sub(r"C\d+", lambda m: repr(observed[m.group()]), expr), {"__builtins__": {}})


def verify(claims, cache_dir, country="PER", tolerance=0.05, offline=False):
    """Return the register with observed value, relative difference, status and model use."""
    observed, out = {}, []
    for c in claims:
        row = dict(c)
        prov = {"source_url": "", "retrieved_at": "", "sha256": "", "note": ""}
        value = None
        if c["source_type"] == "worldbank":
            value, prov = fetch_worldbank(c["source_ref"], c["year"], country, cache_dir, offline)
        elif c["source_type"] == "derived":
            value = _derive(c["source_ref"], observed)
            prov["note"] = f"derived from {c['source_ref']} using observed values"
        observed[c["claim_id"]] = value

        claimed = float(c["claimed_value"])
        if value is None:
            status, rel = "unconfirmable", ""
        else:
            rel_diff = abs(claimed - value) / abs(value)
            status, rel = ("confirmed" if rel_diff <= tolerance else "contradicted"), f"{rel_diff:.4f}"
        row.update({"observed_value": "" if value is None else f"{value:.6g}", "rel_diff": rel,
                    "status": status, "used_in_model": "yes" if status == "confirmed" else "no",
                    **prov})
        out.append(row)
    return out


def summarise(verified, tolerance):
    n = len(verified)
    count = lambda s: sum(r["status"] == s for r in verified)
    return [{"metric": "claims_logged", "value": n},
            {"metric": "tolerance", "value": f"{tolerance:.0%}"},
            {"metric": "confirmed", "value": count("confirmed")},
            {"metric": "contradicted", "value": count("contradicted")},
            {"metric": "unconfirmable", "value": count("unconfirmable")},
            {"metric": "excluded_from_model", "value": n - count("confirmed")}]
