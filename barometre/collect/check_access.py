"""Vérifie l'accès réel à chaque source de données et imprime un état par source.

Usage : python collect/check_access.py
Variables d'environnement optionnelles : MEDIACLOUD_API_KEY
"""
import os
import shutil
import subprocess
from pathlib import Path

import requests
import yaml

CONFIG = Path(__file__).resolve().parent.parent / "config" / "issues.yaml"
TIMEOUT = 30


def gdelt_query(issue):
    """Construit la requête GDELT DOC 2.0 : (a OR "b c") -"x" sourcecountry:FR."""
    def term(t):
        return f'"{t}"' if " " in t or "'" in t or "-" in t else t
    terms = [term(t) for t in issue["any"]]
    q = "(" + " OR ".join(terms) + ")" if len(terms) > 1 else terms[0]
    for x in issue.get("exclude") or []:
        q += f" -{term(x)}"
    return q + " sourcecountry:FR sourcelang:french"


def check_gdelt():
    issue = yaml.safe_load(CONFIG.read_text())["issues"]["inflation"]
    params = {
        "query": gdelt_query(issue),
        "mode": "timelinevolraw",
        "format": "json",
        "startdatetime": "20260901000000",
        "enddatetime": "20260915000000",
    }
    r = requests.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    n = len(data["timeline"][0]["data"])
    return f"OK, {n} points de série pour 'inflation'"


def check_mediacloud():
    key = os.environ.get("MEDIACLOUD_API_KEY")
    if not key:
        return "IGNORÉ : MEDIACLOUD_API_KEY absente"
    r = requests.get(
        "https://search.mediacloud.org/api/search/total-count",
        params={"q": "inflation", "start": "2026-09-01", "end": "2026-09-15", "platform": "onlinenews-mediacloud"},
        headers={"Authorization": f"Token {key}"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return f"OK : {r.json()}"


def check_bigquery():
    if not shutil.which("bq"):
        return "IGNORÉ : bq non installé"
    out = subprocess.run(
        ["bq", "query", "--use_legacy_sql=false", "--dry_run",
         "SELECT COUNT(*) FROM `gdelt-bq.gdeltv2.gkg_partitioned` "
         "WHERE _PARTITIONTIME = TIMESTAMP('2026-09-01')"],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip().splitlines()[-1])
    return "OK (dry run) : " + out.stdout.strip().splitlines()[-1]


def check_url(url):
    def run():
        r = requests.get(url, timeout=TIMEOUT)
        return f"HTTP {r.status_code}"
    return run


CHECKS = {
    "GDELT DOC 2.0": check_gdelt,
    "Media Cloud": check_mediacloud,
    "GDELT GKG / BigQuery": check_bigquery,
    "data.gouv.fr (INA)": check_url("https://www.data.gouv.fr/api/1/datasets/?q=classement+thematique+journaux+televises"),
    "Ipsos (pages WWW)": check_url("https://www.ipsos.com/en/what-worries-world"),
    "Google Trends": check_url("https://trends.google.com/trends/"),
}


if __name__ == "__main__":
    for name, fn in CHECKS.items():
        try:
            status = fn()
        except Exception as e:  # on veut l'état de chaque source, pas un arrêt au premier échec
            status = f"ÉCHEC : {type(e).__name__}: {str(e)[:200]}"
        print(f"{name:24} {status}")
