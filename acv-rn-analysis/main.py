################################################################################
# main.py
# Script maître — exécute l'analyse complète end-to-end
# Usage : python main.py
#         python main.py --etapes 1 2 3   (étapes spécifiques)
################################################################################

import sys
import time
import argparse
from pathlib import Path

# Ajouter le dossier code au path
sys.path.insert(0, str(Path(__file__).parent / "code"))

def run_step(nom: str, module_path: str, etape_num: int) -> bool:
    import importlib.util
    print(f"\n{'='*70}")
    print(f"  ÉTAPE {etape_num} : {nom}")
    print(f"{'='*70}")
    t0 = time.time()
    try:
        spec = importlib.util.spec_from_file_location(
            f"step_{etape_num}",
            Path(__file__).parent / "code" / module_path
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            mod.main()
        elapsed = time.time() - t0
        print(f"\n  ✓ Étape {etape_num} terminée en {elapsed:.1f}s")
        return True
    except FileNotFoundError as e:
        print(f"\n  ⚠️  Fichier manquant : {e}")
        print(f"     → Voir TELECHARGEMENTS_MANUELS.md")
        return False
    except Exception as e:
        print(f"\n  ❌ Erreur étape {etape_num} : {e}")
        import traceback
        traceback.print_exc()
        return False


ETAPES = [
    (1, "Téléchargement données",           "01_download_data.py"),
    (2, "Nettoyage liste ACV",              "02_clean_acv.py"),
    (3, "Nettoyage résultats électoraux",   "03_clean_elections.py"),
    (4, "Nettoyage données INSEE",          "04_clean_insee.py"),
    (5, "Construction panel final",         "05_build_panel.py"),
    (6, "Statistiques descriptives",        "06_descriptive.py"),
    (7, "Propensity score matching",        "07_matching.py"),
    (8, "Estimation DiD principale",        "08_did_main.py"),
    (9, "Robustness checks",               "09_robustness.py"),
]


def main():
    parser = argparse.ArgumentParser(
        description="ACV → Vote RN : analyse empirique end-to-end"
    )
    parser.add_argument(
        "--etapes", nargs="+", type=int, default=None,
        help="Numéros d'étapes à exécuter (ex: --etapes 2 3 5)"
    )
    parser.add_argument(
        "--depuis", type=int, default=1,
        help="Commencer depuis l'étape N (ex: --depuis 3)"
    )
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  ACV → Vote Rassemblement National : Analyse empirique           ║")
    print("║  Méthode : Callaway-Sant'Anna (2021) + Matching + HonestDiD     ║")
    print("║  Cible : Electoral Studies / EJPR / AJPS                        ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    t_global = time.time()
    succes = []
    echecs = []

    etapes_a_executer = [
        (num, nom, script) for num, nom, script in ETAPES
        if (args.etapes is None and num >= args.depuis) or
           (args.etapes is not None and num in args.etapes)
    ]

    for num, nom, script in etapes_a_executer:
        ok = run_step(nom, script, num)
        if ok:
            succes.append(num)
        else:
            echecs.append(num)
            # Arrêter si étape critique (1-5) échoue
            if num <= 5 and num != 1:
                print(f"\n  ⛔ Étape critique {num} échouée — arrêt.")
                print(f"     Vérifier les données manquantes dans TELECHARGEMENTS_MANUELS.md")
                break

    elapsed = time.time() - t_global
    print(f"\n{'='*70}")
    print(f"  BILAN : {len(succes)} étapes réussies, {len(echecs)} en échec")
    print(f"  Temps total : {elapsed:.0f}s ({elapsed/60:.1f} min)")
    if echecs:
        print(f"  Étapes en échec : {echecs}")
        print(f"  → Voir TELECHARGEMENTS_MANUELS.md pour les données manquantes")
    print(f"\n  Outputs :")
    print(f"    data/processed/   ← panels de données")
    print(f"    output/tables/    ← tables LaTeX")
    print(f"    output/figures/   ← figures PDF")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
