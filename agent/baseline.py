"""
baseline.py : calcule F pour Dijkstra, A* et Greedy, pour servir de référence.

Pourquoi passer par weighted_astar
    dijkstra.py et astar.py ne renvoient qu'un chemin, et greedy.py ne relève
    pas le pic du tas : aucun des trois ne fournit de quoi calculer F.

    On utilise donc l'A* pondéré, qui les contient tous les trois — c'est le
    « un seul programme, cinq algorithmes » du cours, où seule la définition
    de f change :

        w = 0        f = g            Dijkstra
        w = 1        f = g + h        A*
        w très grand f ~ h            Greedy

    Même code, même instrumentation, donc des mesures strictement comparables
    entre elles et avec celles des recherches de paramètres.

    Nuance à connaître : Greedy obtenu par un grand w n'est pas rigoureusement
    identique à greedy.py. Les deux trient par h, mais greedy.py ne reconsidère
    jamais une case déjà vue, alors que l'A* pondéré peut améliorer son g. Sur
    les grilles testées ils donnent le même chemin, mais ce n'est pas garanti
    en général.

Le rôle de h selon l'algorithme
    Dijkstra n'utilise pas h du tout : une seule ligne suffit, la métrique
    n'a aucun effet. A* et Greedy s'en servent, donc on teste chaque métrique
    admissible pour eux.

Les contraintes
    On applique celles qui ont un sens pour une référence : admissibilité de
    h, coût sous k fois l'optimum, coût sous le seuil de mission, temps sous
    T_MAX. On n'applique pas la borne sur w : les baselines sont des points de
    repère, pas des solutions candidates de l'espace de recherche.

Pour le lancer
    python baseline.py configs/default.json
"""
import argparse
import csv
import math
import os

import evaluate
from cached_client import CachedGridClient, prechauffer
from client import GridClient

K_REPETITIONS = 11      # impair : la médiane est un run réel
W_GREEDY = 1e6          # assez grand pour que g ne pèse plus rien devant w * h
CSV_PATH = "baseline.csv"


def metriques_admissibles(connectivity):
    """Les heuristiques utilisables pour cette connectivité."""
    return [h for h in evaluate.HEURISTICS if evaluate.admissible(h, connectivity)]


def run_median(fonction, k=K_REPETITIONS):
    """Lance `fonction` k fois et renvoie le run dont le T est médian."""
    runs = [fonction() for _ in range(k)]
    runs.sort(key=lambda r: r["T"])
    return runs[len(runs) // 2]


def evaluer_baseline(client, start, target, w, h, ref, connectivity, threshold):
    """Mesure une baseline et calcule son F, avec les contraintes qui la concernent.

    Même formule que evaluate.evaluate(), mais sans la contrainte sur les
    bornes de w : une baseline est un point de repère, pas une solution
    candidate de l'espace de recherche.
    """
    r = run_median(lambda: evaluate.run(client, start, target, w, h))
    a, b, c = evaluate.WEIGHTS

    r["F"] = (a * r["C"] / ref["C"]
              + b * r["explored"] / ref["explored"]
              + c * r["M"] / ref["M"])

    violated = []
    if not evaluate.admissible(h, connectivity):
        violated.append(f"{h} non admissible en connectivité {connectivity}")
    if r["C"] > evaluate.K * ref["C"]:
        violated.append(f"coût {r['C']:g} > {evaluate.K} x {ref['C']:g}")
    if r["C"] >= threshold:
        violated.append(f"coût {r['C']:g} >= seuil {threshold:g} (mission échouée)")
    if r["T"] > evaluate.T_MAX:
        violated.append(f"temps {r['T']:.2f} s > {evaluate.T_MAX} s")

    r["feasible"] = not violated
    r["violated"] = violated
    r["score"] = r["F"] if r["feasible"] else math.inf
    return r


def ecrire_csv(resultats, chemin):
    """Une ligne par baseline."""
    colonnes = ["algo", "w", "h", "C", "T", "M", "explored", "steps", "F", "feasible", "violated"]
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, extrasaction="ignore")
        w.writeheader()
        for r in resultats:
            ligne = dict(r)
            ligne["violated"] = " ; ".join(r["violated"])
            w.writerow(ligne)


def main():
    p = argparse.ArgumentParser(description="Baselines Dijkstra / A* / Greedy.")
    p.add_argument("config", nargs="?", default="configs/default.json")
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
    a, b, c = evaluate.WEIGHTS
    print(f"Référence A* (w = 1, L2) : C* = {ref['C']:g}  E* = {ref['explored']}  M* = {ref['M']}")
    print(f"F = {a:g} x C/C* + {b:g} x E/E* + {c:g} x M/M*,  k = {evaluate.K:g}, "
          f"seuil de mission = {threshold:g}\n")

    # Dijkstra n'utilise pas h : une seule ligne suffit.
    plan = [("Dijkstra", 0.0, [metriques[0]])]
    plan += [("A*", 1.0, metriques)]
    plan += [("Greedy", W_GREEDY, metriques)]

    resultats = []
    for nom, w, hs in plan:
        for h in hs:
            r = evaluer_baseline(client, start, target, w, h, ref, connectivity, threshold)
            r["algo"] = nom
            resultats.append(r)

    print(f"{'algo':<9} {'w':>8} {'h':>6} {'C':>7} {'explored':>8} {'M':>4} {'T (µs)':>8} {'F':>7}  faisable")
    for r in resultats:
        statut = "oui" if r["feasible"] else "non : " + ", ".join(r["violated"])
        print(f"{r['algo']:<9} {r['w']:>8g} {r['h']:>6} {r['C']:>7g} {r['explored']:>8} "
              f"{r['M']:>4} {r['T'] * 1e6:>8.1f} {r['F']:>7.3f}  {statut}")

    faisables = [r for r in resultats if r["feasible"]]
    if faisables:
        best = min(faisables, key=lambda r: r["F"])
        print(f"\nMeilleure baseline : {best['algo']} (w = {best['w']:g}, h = {best['h']}), "
              f"F = {best['F']:.3f}")
        print("C'est le F à battre par la recherche de paramètres.")
    else:
        print("\nAucune baseline faisable.")

    ecrire_csv(resultats, args.csv)
    print(f"Résultats écrits dans {args.csv}")


if __name__ == "__main__":
    main()
