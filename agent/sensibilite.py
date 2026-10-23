"""
sensibilite.py : faire varier les contraintes et les poids, sans relancer de recherche.

L'idée
    Les recherches ont déjà mesuré C, E et M pour beaucoup de (w, h), et ces
    mesures ne dépendent pas des contraintes : l'A* pondéré trouve le même
    chemin quelle que soit la valeur de k ou du seuil. Une contrainte ne fait
    que décider quelles solutions sont faisables, et les poids ne font que
    changer la note F.
    On peut donc relire les CSV, recalculer la faisabilité et F pour chaque
    nouvelle valeur, et trouver le nouveau meilleur réglage, en une seconde.

La méthode : une seule variation à la fois
    On part du réglage de base (k = 2.5, seuil = 25, a = 0.5, b = c = 0.25)
    et on ne change qu'un paramètre à la fois. Sinon on ne sait pas quel
    changement a causé quel effet.

Ce qu'on fait varier
    k      : le coût maximal accepté, C <= k * C*
    seuil  : le seuil de la mission, C < seuil (imposé par la mission, on
             regarde seulement son effet)
    a      : le poids du coût dans F, avec b = c = (1 - a) / 2
    k avec a = 0.2 : une seule expérience croisée, parce qu'avec a = 0.5 le
             meilleur réglage garde déjà un coût presque optimal, donc k ne
             rejette presque rien ; avec a = 0.2 on voit quand k devient actif
    b avec a = 0.5 : le partage du reste entre l'effort (b) et la mémoire
             (c = 0.5 - b). Avec b = c on ne voit pas ce qui se passe quand
             l'effort et la mémoire tirent dans des sens opposés

Les données utilisées
    Pour chaque config, toutes les évaluations de toutes les méthodes (grid
    grossière, random, grid fine, hill climbing, tabou), sans doublon. La
    grid grossière et le random couvrent les grands w (jusqu'à 100 000), la
    grid fine couvre [1, 9] au pas de 0.1. La référence (A* classique,
    w = 1, L2) est dans la grid fine.

A savoir
    On ne voit que les (w, h) déjà évalués. Si le vrai meilleur réglage pour
    une nouvelle valeur est un w jamais testé, on ne le trouvera pas.
    Entre 1 et 9, la grid fine au pas de 0.1 rend ce risque faible.

Pour le lancer (pas besoin de la grid-api)
    python sensibilite.py
"""
import csv
import math
import os

ICI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(ICI, "resultats")

# config -> les CSV de toutes les recherches faites sur cette config
CONFIGS = {
    "default": ["etape1_grossier.csv", "etape2_random.csv", "etape3_fin.csv",
                "hc_default.csv", "tabou_default.csv"],
}
for nom in ["deux_murs", "deux_murs_con4", "obstacle_u", "obstacle_u_con4"]:
    CONFIGS[nom] = [os.path.join(nom, f) for f in
                    ["grossier.csv", "random.csv", "fin.csv", "hill_climbing.csv", "tabou.csv"]]

# le réglage de base
K, SEUIL, A, W_MAX = 2.5, 25, 0.5, 100

# les valeurs testées, un paramètre à la fois
VALEURS_K = [1.0, 1.1, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0]
VALEURS_SEUIL = [12, 15, 20, 22, 25, 30, 45]
VALEURS_A = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]
VALEURS_B = [0.5, 0.375, 0.25, 0.125, 0.0]     # avec a = 0.5, donc c = 0.5 - b


def charger(nom):
    """Toutes les évaluations d'une config, sans doublon, et la référence."""
    points = {}
    for fichier in CONFIGS[nom]:
        with open(os.path.join(RES, fichier), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                cle = (round(float(r["w"]), 2), r["h"])
                if cle not in points:
                    points[cle] = {"w": cle[0], "h": cle[1], "C": float(r["C"]),
                                   "E": int(float(r["explored"])), "M": int(float(r["M"]))}
    ref = points[(1.0, "L2")]
    return list(points.values()), ref


def meilleur(points, ref, k=K, seuil=SEUIL, a=A, b=None):
    """Le meilleur réglage faisable pour ces valeurs, et le palier qui va avec.

    Sans b, le reste se partage à égalité : b = c = (1 - a) / 2.
    Avec b, la mémoire prend ce qui reste : c = 1 - a - b.
    """
    if b is None:
        b = c = (1 - a) / 2
    else:
        c = 1 - a - b
    faisables = []
    for p in points:
        if p["w"] > W_MAX or p["C"] > k * ref["C"] or p["C"] >= seuil:
            continue
        F = a * p["C"] / ref["C"] + b * p["E"] / ref["E"] + c * p["M"] / ref["M"]
        faisables.append(dict(p, F=F))
    if not faisables:
        return None
    best = min(faisables, key=lambda p: (p["F"], p["w"]))
    meme = [p["w"] for p in faisables
            if (p["h"], p["C"], p["E"], p["M"]) == (best["h"], best["C"], best["E"], best["M"])]
    best["w_min"], best["w_max"] = min(meme), max(meme)
    best["n_faisables"] = len(faisables)
    return best


def cellule(best):
    if best is None:
        return "aucun faisable"
    palier = f"{best['w_min']:g}" if best["w_min"] == best["w_max"] else f"{best['w_min']:g}–{best['w_max']:g}"
    return f"{best['F']:.3f} · {best['h']} · w {palier} · C {best['C']:g}"


def experience(titre, parametre, valeurs, donnees, lignes_csv, **fixes):
    base = {"k": K, "seuil": SEUIL, "a": A, **fixes}
    autres = ", ".join(f"{n} = {v:g}" for n, v in base.items() if n != parametre)
    print(f"\n=== {titre}  (autres paramètres : {autres})")
    noms = list(donnees)
    print(f"{parametre:>6} | " + " | ".join(f"{n:<40}" for n in noms))
    for v in valeurs:
        cells = []
        for n in noms:
            points, ref = donnees[n]
            best = meilleur(points, ref, **{**fixes, parametre: v})
            cells.append(f"{cellule(best):<40}")
            lignes_csv.append({"parametre": parametre + "".join(f" ({n_}={v_:g})" for n_, v_ in fixes.items()),
                               "valeur": v, "config": n,
                               **({k_: best[k_] for k_ in ["F", "h", "w_min", "w_max", "C", "E", "M", "n_faisables"]}
                                  if best else {"F": "", "h": "aucun faisable"})})
        print(f"{v:>6g} | " + " | ".join(cells))


def main():
    donnees = {nom: charger(nom) for nom in CONFIGS}
    print("Références (A* classique, w = 1, L2) :")
    for nom, (points, ref) in donnees.items():
        print(f"  {nom:<16} C* = {ref['C']:<5g} E* = {ref['E']:<3} M* = {ref['M']:<3} ({len(points)} réglages évalués)")

    lignes = []
    experience("Variation de k (coût maximal C <= k * C*)", "k", VALEURS_K, donnees, lignes)
    experience("Variation du seuil de la mission (C < seuil)", "seuil", VALEURS_SEUIL, donnees, lignes)
    experience("Variation du poids du coût a (b = c = (1 - a) / 2)", "a", VALEURS_A, donnees, lignes)
    # k ne compte que si le coût pèse peu : on le refait varier avec a = 0.2
    experience("Variation de k quand le coût pèse peu", "k", VALEURS_K, donnees, lignes, a=0.2)
    # avec b = c on ne voit pas l'effet de l'effort contre la mémoire : on les sépare
    experience("Partage entre effort b et mémoire c = 0.5 - b", "b", VALEURS_B, donnees, lignes, a=0.5)

    chemin = os.path.join(RES, "sensibilite.csv")
    colonnes = ["parametre", "valeur", "config", "F", "h", "w_min", "w_max", "C", "E", "M", "n_faisables"]
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)
    print(f"\nRésultats écrits dans {chemin}")


if __name__ == "__main__":
    main()
