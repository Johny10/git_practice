"""Collecte GDELT DOC 2.0 (mode timelinevolraw) par enjeu, 2020 -> aujourd'hui.

Sortie : data/gdelt_daily.csv (issue, date, count, total)
  count = articles correspondant à la requête ; total = articles surveillés par GDELT
  ce jour-là avec les mêmes filtres pays/langue ("norm" dans l'API).
Les réponses brutes sont gardées dans data/raw/gdelt/ : une année déjà close n'est
pas re-téléchargée, l'année en cours l'est à chaque lancement.

Usage : python collect/gdelt.py [--start 2020] [--issues inflation,taxes]
"""
import argparse
import csv
import datetime as dt
import json
import sys
import time

import requests

from queries import ROOT, gdelt_query, load_issues

API = "https://api.gdeltproject.org/api/v2/doc/doc"
RAW = ROOT / "data" / "raw" / "gdelt"
OUT = ROOT / "data" / "gdelt_daily.csv"
PAUSE = 6  # GDELT demande au plus une requête toutes les 5 secondes


def fetch(query, start, end):
    params = {
        "query": query,
        "mode": "timelinevolraw",
        "format": "json",
        "startdatetime": start.strftime("%Y%m%d000000"),
        "enddatetime": end.strftime("%Y%m%d235959"),
    }
    for attempt in range(5):
        r = requests.get(API, params=params, timeout=120)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(PAUSE * 2 ** (attempt + 1))
            continue
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            # GDELT renvoie ses erreurs de requête en texte brut avec un statut 200
            raise RuntimeError(f"GDELT a refusé la requête : {r.text.strip()[:300]}")
    raise RuntimeError(f"GDELT indisponible après 5 essais (HTTP {r.status_code})")


def parse(payload):
    timeline = payload.get("timeline") or []
    if not timeline:
        return []
    return [
        (dt.datetime.strptime(p["date"][:8], "%Y%m%d").date().isoformat(), p["value"], p.get("norm"))
        for p in timeline[0]["data"]
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2020)
    ap.add_argument("--issues", help="liste d'enjeux séparés par des virgules (défaut : tous)")
    args = ap.parse_args()

    issues = load_issues()
    if args.issues:
        issues = {k: issues[k] for k in args.issues.split(",")}
    today = dt.date.today()
    RAW.mkdir(parents=True, exist_ok=True)
    failures = []

    for key, issue in issues.items():
        q = gdelt_query(issue)
        for year in range(args.start, today.year + 1):
            path = RAW / f"{key}_{year}.json"
            if path.exists() and year < today.year:
                continue
            end = min(dt.date(year, 12, 31), today)
            try:
                payload = fetch(q, dt.date(year, 1, 1), end)
            except Exception as e:
                failures.append((key, year, str(e)))
                print(f"ÉCHEC {key} {year} : {e}", file=sys.stderr)
                time.sleep(PAUSE)
                continue
            path.write_text(json.dumps({"query": q, "fetched": today.isoformat(), "payload": payload}))
            print(f"{key} {year} : {len(parse(payload))} jours")
            time.sleep(PAUSE)

    rows = []
    for path in sorted(RAW.glob("*.json")):
        key = path.stem.rsplit("_", 1)[0]
        if key in issues:
            rows += [(key, *r) for r in parse(json.loads(path.read_text())["payload"])]
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue", "date", "count", "total"])
        w.writerows(sorted(rows))
    print(f"{len(rows)} lignes -> {OUT.relative_to(ROOT)}")
    if failures:
        sys.exit(f"{len(failures)} requêtes en échec, relancer le script pour les reprendre")


if __name__ == "__main__":
    main()
