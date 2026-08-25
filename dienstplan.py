import argparse
import sys
from dataclasses import dataclass

# Windows-Konsolen laufen oft noch mit einer Legacy-Codepage statt UTF-8 —
# ohne das hier werden Umlaute (ü, ä, ö) als Kauderwelsch ausgegeben.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# Modell / Konstanten
TAGE = 7
SCHICHTEN = ["Frühdienst", "Spätdienst"]
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MAX_PERSONEN_PRO_SCHICHT = 2
SCHICHTEN_PRO_TAG = len(SCHICHTEN)
MAX_SCHICHTEN_PRO_WOCHE = 5
MIN_EXAMINIERTE_KRAFT_PRO_SCHICHT = 1

@dataclass
class Mitarbeiter:
    name: str
    ist_examiniert: bool

DATENSAETZE: dict[str, list[Mitarbeiter]] = {
    "A": [
        Mitarbeiter("Anna", True),
        Mitarbeiter("Ben", False),
        Mitarbeiter("Clara", True),
        Mitarbeiter("David", False),
        Mitarbeiter("Eva", True),
        Mitarbeiter("Felix", False),
    ],
    "B": [
        Mitarbeiter("Anna", True),
        Mitarbeiter("Ben", False),
        Mitarbeiter("Clara", True),
        Mitarbeiter("David", False),
        Mitarbeiter("Eva", True),
    ],
    "C": [
        Mitarbeiter("Anna", True),
        Mitarbeiter("Ben", False),
        Mitarbeiter("Clara", False),
        Mitarbeiter("David", False),
        Mitarbeiter("Eva", False),
        Mitarbeiter("Felix", False),
        Mitarbeiter("Greta", False),
    ]
}

# (Tag, Schicht-Index) -> Liste von genau 2 Mitarbeitern
Dienstplan = dict[tuple[int, int], list[Mitarbeiter]]

def machbarkeit_analyse(team: list[Mitarbeiter]) -> list[str]:
    """Analysiert die Machbarkeit des Dienstplans für das gegebene Team und gibt eine Liste von Problemen zurück, falls vorhanden.
    """
    team_groesse = len(team)
    examiniert = [mitarbeiter for mitarbeiter in team if mitarbeiter.ist_examiniert]
    schichten_pro_tag = len(SCHICHTEN) # 2
    schichten_gesamt = TAGE * schichten_pro_tag # 14
    team_bedarf = schichten_gesamt * MAX_PERSONEN_PRO_SCHICHT # 28
    team_kapazitaet = team_groesse * MAX_SCHICHTEN_PRO_WOCHE
    examiniert_bedarf = schichten_gesamt * MIN_EXAMINIERTE_KRAFT_PRO_SCHICHT  # 14
    examiniert_kapazitaet = len(examiniert) * MAX_SCHICHTEN_PRO_WOCHE

    probleme: list[str] = []

    # siehe Modellierung.pdf
    # Personenbedarf pro Tag
    personen_pro_tag_bedarf = schichten_pro_tag * MAX_PERSONEN_PRO_SCHICHT # 4
    if team_groesse < personen_pro_tag_bedarf:
        fehlend = personen_pro_tag_bedarf - team_groesse
        probleme.append(
            f"Nur {team_groesse} Person(en) im Team, aber jeden Tag laufen "
            f"{schichten_pro_tag} Schichten parallel mit je {MAX_PERSONEN_PRO_SCHICHT} "
            f"Personen, die alle verschieden sein müssen (niemand darf 2 "
            f"Schichten am selben Tag übernehmen). Benötigt: mindestens "
            f"{personen_pro_tag_bedarf} Personen im Team. Fehlend: {fehlend}."
        )

    # Examinierte Kräfte pro Tag
    if len(examiniert) < schichten_pro_tag:
        fehlend = schichten_pro_tag - len(examiniert)
        namen = ", ".join(m.name for m in examiniert) or "keine"
        probleme.append(
            f"Nur {len(examiniert)} examinierte Kraft/Kräfte im Team ({namen}), "
            f"aber jeden Tag laufen {schichten_pro_tag} Schichten parallel, die "
            f"je eine EIGENE examinierte Kraft brauchen (niemand darf 2 Schichten "
            f"am selben Tag übernehmen). Fehlend: {fehlend} examinierte Kraft/Kräfte."
        )

    # Gesamtkapazität über das Team
    if team_kapazitaet < team_bedarf:
        luecke = team_bedarf - team_kapazitaet
        zusatz = -(-luecke // MAX_SCHICHTEN_PRO_WOCHE)
        probleme.append(
            f"Das Team kann wegen der {MAX_SCHICHTEN_PRO_WOCHE}-Schichten-Grenze "
            f"insgesamt höchstens {team_kapazitaet} "
            f"Personenschichten/Woche leisten ({team_groesse} × {MAX_SCHICHTEN_PRO_WOCHE}), "
            f"benötigt werden aber {team_bedarf} (2 Personen × "
            f"{schichten_gesamt} Schichten). Lücke: {luecke} Personenschichten — "
            f"es fehlen also mindestens {zusatz} weitere Person(en) im Team."
        )

    # Kapazität examinierte Kräfte über die Woche.
    if examiniert_kapazitaet < examiniert_bedarf:
        luecke = examiniert_bedarf - examiniert_kapazitaet
        zusatz = -(-luecke // MAX_SCHICHTEN_PRO_WOCHE) 
        probleme.append(
            f"Examinierte Kräfte können wegen der {MAX_SCHICHTEN_PRO_WOCHE}-"
            f"Schichten-Grenze zusammen höchstens {examiniert_kapazitaet} "
            f"Schichten/Woche abdecken ({len(examiniert)} × "
            f"{MAX_SCHICHTEN_PRO_WOCHE}), benötigt werden aber mindestens "
            f"{examiniert_bedarf} (1 pro Schicht × {schichten_gesamt} Schichten). "
            f"Lücke: {luecke} Schichten — es fehlen also mindestens {zusatz} "
            f"weitere examinierte Kraft/Kräfte."
        )

    return probleme

def solve(team: list[Mitarbeiter]) -> tuple[Dienstplan, dict[str, int]] | None:
    slots = [(tag, schicht_index) for tag in range(TAGE) for schicht_index in range(len(SCHICHTEN))]
    last: dict[str, int] = {mitarbeiter.name: 0 for mitarbeiter in team}
    dienstplan: Dienstplan = {}
    def get_kandidaten(tag: int, schicht_index: int) -> list[Mitarbeiter]:
        kandidaten = []
        heute_besetzt = []
        if schicht_index == 1:
            heute_besetzt = dienstplan.get((tag, 0), [])
        for mitarbeiter in team:
            if last[mitarbeiter.name] >= MAX_SCHICHTEN_PRO_WOCHE:
                continue
            if mitarbeiter in heute_besetzt:
                continue
            kandidaten.append(mitarbeiter)

        # Faire Verteilung: Greedy
        kandidaten.sort(key=lambda m: last[m.name])
        return kandidaten

    def rest_noch_moeglich(slot_index: int) -> bool:
        rest_slots = slots[slot_index:]
        rest_team_bedarf = len(rest_slots) * MAX_PERSONEN_PRO_SCHICHT
        rest_examiniert_bedarf = len(rest_slots) * MIN_EXAMINIERTE_KRAFT_PRO_SCHICHT
        rest_team_kapazitaet = 0
        rest_examiniert_kapazitaet = 0
        for mitarbeiter in team:
            rest_team_kapazitaet += MAX_SCHICHTEN_PRO_WOCHE - last[mitarbeiter.name]
            if mitarbeiter.ist_examiniert:
                rest_examiniert_kapazitaet += MAX_SCHICHTEN_PRO_WOCHE - last[mitarbeiter.name]
        return rest_team_kapazitaet >= rest_team_bedarf and rest_examiniert_kapazitaet >= rest_examiniert_bedarf

    def backtrack(slot_index: int) -> bool:
        if slot_index == len(slots):
            return True
        tag, schicht_index = slots[slot_index]
        kandidaten = get_kandidaten(tag, schicht_index)
        for index, person1 in enumerate(kandidaten):
            for person2 in kandidaten[index + 1:]:
                if person1 == person2:
                    continue
                if not (person1.ist_examiniert or person2.ist_examiniert):
                    continue
                dienstplan[(tag, schicht_index)] = [person1, person2]
                last[person1.name] += 1
                last[person2.name] += 1
                if rest_noch_moeglich(slot_index + 1) and backtrack(slot_index + 1):
                    return True
                last[person1.name] -= 1
                last[person2.name] -= 1
                del dienstplan[(tag, schicht_index)]
        return False
    if backtrack(0):
        return dienstplan, last
    return None

# Ruhezeit-Regel 
def solve_ruhezeit(team: list[Mitarbeiter]) -> tuple[Dienstplan, dict[str, int]] | None:
    slots = [(tag, schicht_index) for tag in range(TAGE) for schicht_index in range(len(SCHICHTEN))]
    dienstplan: Dienstplan = {}
    last = {mitarbeiter.name: 0 for mitarbeiter in team}

    def get_kandidaten(tag: int, schicht_index: int) -> list[Mitarbeiter]:
        kandidaten = []
        heute_besetzt = []
        if schicht_index == 1:
            heute_besetzt = dienstplan.get((tag, 0), [])
        gesetern_spaet = []
        if tag > 0:
            gesetern_spaet = dienstplan.get((tag - 1, 1), [])
        for mitarbeiter in team:
            if last[mitarbeiter.name] >= MAX_SCHICHTEN_PRO_WOCHE:
                continue
            if mitarbeiter in heute_besetzt:
                continue
            if schicht_index == 0 and mitarbeiter in gesetern_spaet:
                continue
            kandidaten.append(mitarbeiter)
        # Faire Verteilung: Greedy
        kandidaten.sort(key=lambda m: last[m.name])
        return kandidaten

    def rest_noch_moeglich(slot_index: int) -> bool:
        rest_slots = slots[slot_index:]
        rest_team_bedarf = len(rest_slots) * MAX_PERSONEN_PRO_SCHICHT
        rest_examiniert_bedarf = len(rest_slots) * MIN_EXAMINIERTE_KRAFT_PRO_SCHICHT
        rest_team_kapazitaet = 0
        rest_examiniert_kapazitaet = 0
        for mitarbeiter in team:
            rest_team_kapazitaet += MAX_SCHICHTEN_PRO_WOCHE - last[mitarbeiter.name]
            if mitarbeiter.ist_examiniert:
                rest_examiniert_kapazitaet += MAX_SCHICHTEN_PRO_WOCHE - last[mitarbeiter.name]
        return rest_team_kapazitaet >= rest_team_bedarf and rest_examiniert_kapazitaet >= rest_examiniert_bedarf

    def backtrack(slot_index: int) -> bool:
        if slot_index == len(slots):
            return True
        tag, schicht_index = slots[slot_index]
        kandidaten = get_kandidaten(tag, schicht_index)
        for index, person1 in enumerate(kandidaten):
            for person2 in kandidaten[index + 1:]:
                if person1 == person2:
                    continue
                if not (person1.ist_examiniert or person2.ist_examiniert):
                    continue
                dienstplan[(tag, schicht_index)] = [person1, person2]
                last[person1.name] += 1
                last[person2.name] += 1
                if rest_noch_moeglich(slot_index + 1) and backtrack(slot_index + 1):
                    return True
                last[person1.name] -= 1
                last[person2.name] -= 1
                del dienstplan[(tag, schicht_index)]
        return False

    if backtrack(0):
        return dienstplan, last
    return None


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def print_team(team: list[Mitarbeiter]) -> None:
    for mitarbeiter in team:
        rolle = "examiniert" if mitarbeiter.ist_examiniert else "Hilfskraft"
        print(f"    - {mitarbeiter.name} ({rolle})")


def print_infeasible(name: str, team: list[Mitarbeiter], probleme: list[str]) -> None:
    print(f"\n=== Datensatz {name}: KEINE gültige Lösung ===")
    print_team(team)
    print(f"\n  Warum unlösbar ({len(probleme)} Grund/Gründe):")
    for index, problem in enumerate(probleme, 1):
        print(f"  {index}. {problem}")


def zaehle_ruhezeit_verstoesse(dienstplan: Dienstplan) -> int:
    """Zählt, wie oft jemand im Spätdienst eines Tages UND im Frühdienst
    des Folgetags eingeteilt ist — unabhängig davon, ob solve() oder
    solve_ruhezeit() den Plan erzeugt hat."""
    verstoesse = 0
    for tag in range(TAGE - 1):
        heute_spaet = {m.name for m in dienstplan.get((tag, 1), [])}
        morgen_frueh = {m.name for m in dienstplan.get((tag + 1, 0), [])}
        verstoesse += len(heute_spaet & morgen_frueh)
    return verstoesse


def print_dienstplan(name: str, team: list[Mitarbeiter], dienstplan: Dienstplan,
                      last: dict[str, int], ruhezeit_aktiv: bool) -> None:
    print(f"\n=== Datensatz {name}: gültiger Wochendienstplan ===")
    print_team(team)
    print()
    for tag in range(TAGE):
        zeile = f"  {WOCHENTAGE[tag]}: "
        teile = []
        for schicht_index, label in enumerate(SCHICHTEN):
            besetzung = dienstplan[(tag, schicht_index)]
            namen = " + ".join(
                f"{m.name}{'*' if m.ist_examiniert else ''}" for m in besetzung
            )
            teile.append(f"{label}: {namen}")
        print(zeile + "  |  ".join(teile))

    print("\n  Schichten pro Person (Woche):")
    for mitarbeiter in sorted(team, key=lambda m: -last[m.name]):
        print(f"    - {mitarbeiter.name}: {last[mitarbeiter.name]} / {MAX_SCHICHTEN_PRO_WOCHE}")
    spanne = max(last.values()) - min(last.values())
    print(f"  Fairness-Spanne (max - min): {spanne}")

    verstoesse = zaehle_ruhezeit_verstoesse(dienstplan)
    if ruhezeit_aktiv:
        print(
            f"  Ruhezeit-Regel aktiv (--ruhezeit): Spätdienst -> nächster Tag "
            f"kein Frühdienst. Verstöße im Plan: {verstoesse}."
        )
    else:
        print(
            f"  Ruhezeit-Regel NICHT aktiv (--ruhezeit nicht gesetzt). "
            f"Tatsächliche Verstöße im Plan: {verstoesse}."
        )
    print("  (* = examinierte Pflegekraft)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dienstplan-Optimierung für die Teams A, B und C."
    )
    parser.add_argument(
        "--ruhezeit",
        action="store_true",
        help=(
            "Ruhezeit-Regel als harte Zusatzregel durchsetzen (kein "
            "Frühdienst direkt nach Spätdienst). Ohne dieses Flag wird "
            "solve() ohne diese Zusatzregel verwendet."
        ),
    )
    args = parser.parse_args()

    modus = "MIT Ruhezeit-Regel (--ruhezeit)" if args.ruhezeit else "OHNE Ruhezeit-Regel"
    print(f"Dienstplan-Optimierung — {modus}")
    print("=" * 60)

    loeser = solve_ruhezeit if args.ruhezeit else solve

    for name, team in DATENSAETZE.items():
        probleme = machbarkeit_analyse(team)
        if probleme:
            print_infeasible(name, team, probleme)
            continue

        ergebnis = loeser(team)
        if ergebnis is None:
            print(f"\n=== Datensatz {name}: KEINE gültige Lösung MIT --ruhezeit ===")
            print_team(team)
            print(
                "\n  Die Kapazitäts-Checks halten das Team für rechnerisch "
                "lösbar, aber der Solver findet mit der Ruhezeit-Zusatzregel "
                "keine Zuordnung. Versuchen Sie es ohne --ruhezeit."
            )
            continue

        dienstplan, last = ergebnis
        print_dienstplan(name, team, dienstplan, last, ruhezeit_aktiv=args.ruhezeit)
    print()


if __name__ == "__main__":
    main()