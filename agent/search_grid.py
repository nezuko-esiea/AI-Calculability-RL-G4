"""
search_grid.py : grid search sur l'espace (w, h) de l'A* pondéré.

Le principe
    On balaie l'espace à pas régulier au lieu de tirer au hasard. Deux
    lancements avec les mêmes bornes donnent exactement les mêmes points :
    il n'y a aucun hasard, donc rien à fixer avec une graine.

Deux façons de balayer
    --step 0.5      pas additif : 1, 1.5, 2, 2.5...
                    pour explorer finement une petite région

    --factor 10     pas multiplicatif : 1, 10, 100, 1000...
                    pour couvrir plusieurs ordres de grandeur avec peu de
                    points, quand on ne sait pas encore où regarder

    Un balayage additif de 1 à 100000 demanderait 100000 points ; le même
    intervalle en multiplicatif par 10 n'en demande que 6.

L'espace de recherche
    w entre --w-min et --w-max, h parmi les métriques admissibles pour la
    connectivité de la grille. En connectivité 8 L1 surestime une diagonale,
    elle est donc exclue dès le départ plutôt que testée puis rejetée.

    La borne haute sert aussi à la contrainte d'evaluate() : --w-max est passé
    en paramètre w_max, pour que la contrainte corresponde à l'espace
    réellement balayé plutôt qu'à la constante du module.

Les mesures
    Le client est mis en cache et préchauffé, donc T mesure le travail de
    l'algorithme et plus la latence réseau. À cette échelle une mesure isolée
    est du bruit : chaque point est donc évalué K_REPETITIONS fois et on garde
    le run dont le T est médian.

Pour le lancer
    python search_grid.py configs/default.json --w-min 1 --w-max 100000 --factor 10
    python search_grid.py configs/default.json --w-min 1 --w-max 20 --step 0.5

A savoir
    Le budget d'évaluations est affiché avant de commencer. C'est lui qu'il
    faut garder égal entre les méthodes pour les comparer honnêtement.
"""
import argparse
import csv
import math
import os

import evaluate
from cached_client import CachedGridClient, prechauffer
from client import GridClient

K_REPETITIONS = 11      # impair : la médiane est un run réel
CSV_PATH = "grid_search.csv"


def metriques_admissibles(connectivity):
    """Les heuristiques utilisables pour cette connectivité."""
    return [h for h in evaluate.HEURISTICS if evaluate.admissible(h, connectivity)]


def run_median(fonction, k=K_REPETITIONS):
    """Lance `fonction` k fois et renvoie le run dont le T est médian.

    C, M et explored sont identiques d'un run à l'autre puisque l'algorithme
    est déterministe ; seuls T et F varient. Renvoyer le run médian donne donc
    un dictionnaire cohérent, sans avoir à recalculer F.
    """
    runs = [fonction() for _ in range(k)]
    runs.sort(key=lambda r: r["T"])
    return runs[len(runs) // 2]


def valeurs_de_w(w_min, w_max, pas=None, facteur=None):
    """Les valeurs de w à tester, en pas additif ou multiplicatif.

    Dans les deux cas on calcule chaque valeur à partir de l'indice plutôt
    que d'accumuler, pour que les erreurs d'arrondi ne se cumulent pas.
    """
    if facteur:
        n = int(math.floor(math.log(w_max / w_min) / math.log(facteur))) + 1
        return [w_min * facteur ** i for i in range(n)]
    n = int(round((w_max - w_min) / pas)) + 1
    return [w_min + i * pas for i in range(n)]


def ecrire_csv(resultats, chemin):
    """Écrit tous les points du balayage, une ligne chacun."""
    colonnes = ["w", "h", "C", "T", "M", "explored", "steps", "F", "feasible", "violated"]
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, extrasaction="ignore")
        w.writeheader()
        for r in resultats:
            ligne = dict(r)
            ligne["violated"] = " ; ".join(r["violated"])
            w.writerow(ligne)


def main():
    p = argparse.ArgumentParser(description="Grid search sur (w, h) de l'A* pondéré.")
    p.add_argument("config", nargs="?", default="configs/default.json")
    p.add_argument("--w-min", type=float, default=1.0)
    p.add_argument("--w-max", type=float, default=100000.0)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--step", type=float, help="pas additif")
    mode.add_argument("--factor", type=float, help="pas multiplicatif")
    p.add_argument("--csv", default=CSV_PATH)
    args = p.parse_args()

    if args.step is None and args.factor is None:
        args.factor = 10.0      # par défaut : balayage grossier en ordres de grandeur

    client = CachedGridClient(GridClient(os.environ.get("GRID_URL", "http://localhost:8000")))

    mission = evaluate.load_grid(client, args.config)
    start, target = tuple(mission["start"]), tuple(mission["target"])
    etat = client.state()
    connectivity, size = etat["connectivity"], etat["size"]
    threshold = mission["threshold"]

    print(f"Config {args.config} : {start} -> {target}, connectivité {connectivity}")
    print("Préchauffage du cache...", end=" ", flush=True)
    prechauffer(client, size, target, evaluate.HEURISTICS.values())
    print(f"{client.appels_reseau} requêtes, cache rempli")

    metriques = metriques_admissibles(connectivity)
    exclues = [h for h in evaluate.HEURISTICS if h not in metriques]
    print(f"Heuristiques testées : {', '.join(metriques)}"
          + (f"  (exclue : {', '.join(exclues)}, non admissible en connectivité {connectivity})"
             if exclues else ""))

    ws = valeurs_de_w(args.w_min, args.w_max, args.step, args.factor)
    budget = len(ws) * len(metriques)

    ref = run_median(lambda: evaluate.reference(client, start, target))
    print(f"Référence A* (w = 1, L2) : C* = {ref['C']:g}  T* = {ref['T']:.6f} s  M* = {ref['M']}")
    mode_txt = f"pas additif de {args.step:g}" if args.step else f"pas multiplicatif x{args.factor:g}"
    print(f"Grid search : w de {args.w_min:g} à {args.w_max:g}, {mode_txt} ({len(ws)} valeurs), "
          f"médiane sur {K_REPETITIONS} répétitions")
    print(f"Budget : {budget} évaluations\n")

    resultats = []
    i = 0
    for h in metriques:
        for w in ws:
            i += 1
            r = run_median(lambda: evaluate.evaluate(
                client, start, target, w, h, ref, connectivity, threshold,
                w_max=args.w_max))
            resultats.append(r)
            print(f"  {i:>3}/{budget}  w = {w:>12g}  h = {h:<6}  "
                  f"C = {r['C']:>5g}  explored = {r['explored']:>3}  F = {r['F']:.3f}"
                  f"{'' if r['feasible'] else '  (non faisable)'}")

    resultats.sort(key=lambda r: r["score"])

    print(f"\n{'rang':>4} {'w':>12} {'h':>6} {'C':>7} {'T (µs)':>8} {'M':>4} {'explored':>8} {'F':>7}  faisable")
    for rang, r in enumerate(resultats, start=1):
        statut = "oui" if r["feasible"] else "non : " + ", ".join(r["violated"])
        print(f"{rang:>4} {r['w']:>12g} {r['h']:>6} {r['C']:>7g} {r['T'] * 1e6:>8.1f} "
              f"{r['M']:>4} {r['explored']:>8} {r['F']:>7.3f}  {statut}")

    faisables = [r for r in resultats if r["feasible"]]
    print(f"\n{len(faisables)} points faisables sur {budget}")

    if faisables:
        best = faisables[0]
        print(f"Meilleur : w = {best['w']:g}, h = {best['h']}, F = {best['F']:.3f}, "
              f"C = {best['C']:g}, explored = {best['explored']}, M = {best['M']}")
        identiques = [r for r in faisables
                      if (r["C"], r["M"], r["explored"]) == (best["C"], best["M"], best["explored"])]
        if len(identiques) > 1:
            ws_id = sorted(r["w"] for r in identiques)
            print(f"Attention : {len(identiques)} points donnent exactement le même résultat "
                  f"(C, M, explored), pour w de {ws_id[0]:g} à {ws_id[-1]:g}.")
            print("Leur classement ne tient donc qu'à T : c'est un palier, pas un minimum.")
    else:
        print("Aucun point faisable : élargir l'intervalle ou revoir les contraintes.")

    # les paliers : regroupe les points qui donnent le même (C, M, explored)
    paliers = {}
    for r in resultats:
        cle = (r["C"], r["M"], r["explored"])
        paliers.setdefault(cle, []).append(r["w"])
    print(f"\n{len(paliers)} comportements distincts sur {budget} évaluations :")
    for (c, m, e), liste in sorted(paliers.items()):
        liste.sort()
        etendue = f"w = {liste[0]:g}" if len(liste) == 1 else f"w de {liste[0]:g} à {liste[-1]:g}"
        print(f"  C = {c:>7g}  M = {m:>3}  explored = {e:>3}   {etendue}  ({len(liste)} points)")

    ecrire_csv(resultats, args.csv)
    print(f"\nRésultats écrits dans {args.csv}")


if __name__ == "__main__":
    main()
