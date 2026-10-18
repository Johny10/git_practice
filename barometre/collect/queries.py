"""Charge la grille d'enjeux et traduit chaque enjeu dans la syntaxe de chaque source."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "issues.yaml"


def load_issues():
    return yaml.safe_load(CONFIG.read_text())["issues"]


def _quote(t):
    return f'"{t}"' if any(c in t for c in " '-") else t


def gdelt_query(issue):
    """GDELT DOC 2.0 : (a OR "b c") -"x" sourcecountry:FR sourcelang:french."""
    terms = [_quote(t) for t in issue["any"]]
    q = "(" + " OR ".join(terms) + ")" if len(terms) > 1 else terms[0]
    for x in issue.get("exclude") or []:
        q += f" -{_quote(x)}"
    return q + " sourcecountry:FR sourcelang:french"


def mediacloud_query(issue):
    """Media Cloud (Lucene) : (a OR "b c") AND NOT ("x"). Pays restreint par la collection."""
    q = "(" + " OR ".join(_quote(t) for t in issue["any"]) + ")"
    excl = issue.get("exclude") or []
    if excl:
        q += " AND NOT (" + " OR ".join(_quote(x) for x in excl) + ")"
    return q
