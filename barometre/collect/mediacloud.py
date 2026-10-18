"""Collecte Media Cloud : comptages quotidiens par enjeu dans la collection France.

Sortie : data/mediacloud_daily.csv (issue, date, count, total)
  total = toutes les stories de la collection ce jour-là (pour normaliser).
Prérequis : MEDIACLOUD_API_KEY et MEDIACLOUD_COLLECTION_ID (id de la collection
nationale France). Sans id, le script liste les collections candidates.

Usage : python collect/mediacloud.py [--start 2020-01-01] [--issues inflation,taxes]
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import time

import mediacloud.api

from queries import ROOT, load_issues, mediacloud_query

RAW = ROOT / "data" / "raw" / "mediacloud"
OUT = ROOT / "data" / "mediacloud_daily.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--issues")
    args = ap.parse_args()

    key = os.environ.get("MEDIACLOUD_API_KEY")
    if not key:
        sys.exit("MEDIACLOUD_API_KEY absente")
    coll = os.environ.get("MEDIACLOUD_COLLECTION_ID")
    if not coll:
        page = mediacloud.api.DirectoryApi(key).collection_list(name="France", limit=50)
        for c in page["results"]:
            print(c["id"], c["name"], c.get("source_count"))
        sys.exit("Choisir une collection et définir MEDIACLOUD_COLLECTION_ID")

    search = mediacloud.api.SearchApi(key)
    issues = load_issues()
    if args.issues:
        issues = {k: issues[k] for k in args.issues.split(",")}
    start, today = dt.date.fromisoformat(args.start), dt.date.today()
    RAW.mkdir(parents=True, exist_ok=True)
    failures = []

    for k, issue in issues.items():
        q = mediacloud_query(issue)
        for year in range(start.year, today.year + 1):
            path = RAW / f"{k}_{year}.json"
            if path.exists() and year < today.year:
                continue
            try:
                points = search.story_count_over_time(
                    q, max(start, dt.date(year, 1, 1)), min(dt.date(year, 12, 31), today),
                    collection_ids=[int(coll)])
            except Exception as e:
                failures.append((k, year, str(e)))
                print(f"ÉCHEC {k} {year} : {e}", file=sys.stderr)
                time.sleep(5)
                continue
            path.write_text(json.dumps({"query": q, "collection_id": int(coll), "fetched": today.isoformat(),
                                        "counts": points}, default=str))
            print(f"{k} {year} : {len(points)} jours")
            time.sleep(2)

    rows = []
    for path in sorted(RAW.glob("*.json")):
        k = path.stem.rsplit("_", 1)[0]
        if k in issues:
            rows += [(k, p["date"], p["count"], p["total_count"]) for p in json.loads(path.read_text())["counts"]]
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue", "date", "count", "total"])
        w.writerows(sorted(rows))
    print(f"{len(rows)} lignes -> {OUT.relative_to(ROOT)}")
    if failures:
        sys.exit(f"{len(failures)} requêtes en échec, relancer le script pour les reprendre")


if __name__ == "__main__":
    main()
