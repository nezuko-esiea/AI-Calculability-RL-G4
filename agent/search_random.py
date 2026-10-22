"""
search_random.py : random search sur l'espace (w, h) de l'A* pondéré.

Le principe
    On tire au hasard N solutions dans l'espace de recherche, on les évalue
    toutes, et on garde la meilleure. C'est la méthode la plus simple : elle
    ne regarde pas les résultats précédents pour choisir le tirage suivant.

L'espace de recherche
    w uniforme entre --w-min et --w-max, h parmi les métriques admissibles
    pour la connectivité de la grille. En connectivité 8, L1 surestime une
    diagonale (elle la compte 2 alors qu'elle coûte 1.5) : elle est exclue dès
    le tirage, inutile de dépenser des tirages sur des solutions dont on sait
    d'avance qu'elles violeront une contrainte.

    Les bornes servent aussi à la contrainte d'evaluate() : --w-max est passé
    en paramètre w_max, pour que la contrainte corresponde à l'espace
    réellement tiré plutôt qu'à la constante du module.

Le cache
    Les évaluations passent par un CachedGridClient, préchauffé avant les
    mesures. Sans lui la campagne fait des milliers de requêtes HTTP ; avec
    lui le réseau n'est sollicité qu'une fois.

    Conséquence : T ne mesure plus la latence réseau mais le travail de
    l'algorithme. Les valeurs tombent à quelques microsecondes.

La médiane sur les répétitions
    À cette échelle une mesure isolée de T est du bruit. On relance donc
    chaque évaluation K_REPETITIONS fois et on garde celle dont le T est
    médian. L'algorithme étant déterministe, C, M et explored sont identiques
    d'une répétition à l'autre : seuls T et F changent, et prendre le run
    médian donne un résultat cohérent sans recalculer F soi-même.

    Même traitement pour la référence, ce qui évite que le tout premier appel,
    systématiquement plus lent, serve de dénominateur à tous les F.

Pour le lancer
    python search_random.py configs/default.json
    python search_random.py configs/default.json --w-min 1 --w-max 20 --draws 50

A savoir
    La graine est fixée, donc deux lancements donnent les mêmes tirages.
    Nécessaire pour la reproductibilité et pour comparer équitablement avec
    les autres méthodes de recherche, à budget d'évaluations égal.
"""
import argparse
import csv
import os
import random

import evaluate
from cached_client import CachedGridClient, prechauffer
from client import GridClient

K_REPETITIONS = 11      # impair : la médiane est un run réel
CSV_PATH = "random_search.csv"


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


def tirages(n, seed, w_min, w_max, metriques):
    """Renvoie n couples (w, h) tirés au hasard dans l'espace de recherche."""
    rng = random.Random(seed)
    return [(rng.uniform(w_min, w_max), rng.choice(metriques)) for _ in range(n)]


def ecrire_csv(resultats, chemin):
    """Écrit le nuage complet, une ligne par tirage."""
    colonnes = ["w", "h", "C", "T", "M", "explored", "steps", "F", "feasible", "violated"]
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, extrasaction="ignore")
        w.writeheader()
        for r in resultats:
            ligne = dict(r)
            ligne["violated"] = " ; ".join(r["violated"])
            w.writerow(ligne)


def main():
    p = argparse.ArgumentParser(description="Random search sur (w, h) de l'A* pondéré.")
    p.add_argument("config", nargs="?", default="configs/default.json")
    p.add_argument("--w-min", type=float, default=1.0)
    p.add_argument("--w-max", type=float, default=float(evaluate.W_MAX))
    p.add_argument("--draws", type=int, default=30, help="nombre de tirages")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--csv", default=CSV_PATH)
    args = p.parse_args()

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

    ref = run_median(lambda: evaluate.reference(client, start, target))
    print(f"Référence A* (w = 1, L2) : C* = {ref['C']:g}  T* = {ref['T']:.6f} s  M* = {ref['M']}")
    print(f"Random search : {args.draws} tirages, w uniforme dans "
          f"[{args.w_min:g}, {args.w_max:g}], graine {args.seed}, "
          f"médiane sur {K_REPETITIONS} répétitions")
    print(f"Budget : {args.draws} évaluations\n")

    resultats = []
    couples = tirages(args.draws, args.seed, args.w_min, args.w_max, metriques)
    for i, (w, h) in enumerate(couples, start=1):
        r = run_median(lambda: evaluate.evaluate(
            client, start, target, w, h, ref, connectivity, threshold,
            w_max=args.w_max))
        resultats.append(r)
        print(f"  tirage {i:>3}/{args.draws}  w = {w:>12g}  h = {h:<6}  "
              f"C = {r['C']:>5g}  explored = {r['explored']:>3}  F = {r['F']:.3f}"
              f"{'' if r['feasible'] else '  (non faisable)'}")

    resultats.sort(key=lambda r: r["score"])

    print(f"\n{'rang':>4} {'w':>12} {'h':>6} {'C':>7} {'T (µs)':>8} {'M':>4} {'explored':>8} {'F':>7}  faisable")
    for rang, r in enumerate(resultats, start=1):
        statut = "oui" if r["feasible"] else "non : " + ", ".join(r["violated"])
        print(f"{rang:>4} {r['w']:>12g} {r['h']:>6} {r['C']:>7g} {r['T'] * 1e6:>8.1f} "
              f"{r['M']:>4} {r['explored']:>8} {r['F']:>7.3f}  {statut}")

    faisables = [r for r in resultats if r["feasible"]]
    print(f"\n{len(faisables)} tirages faisables sur {args.draws}")

    if faisables:
        best = faisables[0]
        print(f"Meilleur : w = {best['w']:g}, h = {best['h']}, F = {best['F']:.3f}, "
              f"C = {best['C']:g}, explored = {best['explored']}, M = {best['M']}")
        ws = sorted(r["w"] for r in faisables)
        print(f"w des tirages faisables : de {ws[0]:g} à {ws[-1]:g}")

        identiques = [r for r in faisables
                      if (r["C"], r["M"], r["explored"]) == (best["C"], best["M"], best["explored"])]
        if len(identiques) > 1:
            ws_id = sorted(r["w"] for r in identiques)
            print(f"Attention : {len(identiques)} tirages donnent exactement le même résultat "
                  f"(C, M, explored), pour w de {ws_id[0]:g} à {ws_id[-1]:g}.")
            print("Leur classement ne tient donc qu'à T : il n'y a pas un meilleur w "
                  "mais un intervalle équivalent.")
    else:
        print("Aucun tirage faisable : revoir les contraintes ou l'espace de recherche.")

    # les paliers : regroupe les tirages qui donnent le même (C, M, explored)
    paliers = {}
    for r in resultats:
        cle = (r["C"], r["M"], r["explored"])
        paliers.setdefault(cle, []).append(r["w"])
    print(f"\n{len(paliers)} comportements distincts sur {args.draws} tirages :")
    for (c, m, e), liste in sorted(paliers.items()):
        liste.sort()
        etendue = f"w = {liste[0]:g}" if len(liste) == 1 else f"w de {liste[0]:g} à {liste[-1]:g}"
        print(f"  C = {c:>7g}  M = {m:>3}  explored = {e:>3}   {etendue}  ({len(liste)} tirages)")

    print(f"\nRequêtes réseau au total : {client.appels_reseau}  "
          f"(servies par le cache : {client.appels_cache})")

    ecrire_csv(resultats, args.csv)
    print(f"Nuage complet écrit dans {args.csv}")


if __name__ == "__main__":
    main()
