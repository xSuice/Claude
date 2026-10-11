"""Tests fuer router_core (Aufruf: python scripts/router/test_router_core.py). Rueckgabe 0 = alles bestanden."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from router_core import choose, classify, suggest_access  # noqa: E402

MODEL_CASES = [  # (Prompt, erwartetes Modell)  -- uebernommen aus dem alten Router-Test, plus Bruecke/Council
    ("Liste die Dateien auf.", "haiku"), ("Liste die Dateien im aktuellen Projekt auf.", "haiku"),
    ("Was steht in README.md?", "haiku"), ("Suche nach der FileBrowser-Konfiguration.", "haiku"),
    ("Zeige mir den Status der Docker-Container.", "haiku"), ("docker ps", "haiku"), ("git status", "haiku"),
    ("Wie spät ist es auf dem Server?", "haiku"),
    ("Erstelle ein Bash-Skript, das den Status aller Docker-Container prüft.", "sonnet"),
    ("Ändere meine Docker-Compose-Konfiguration.", "sonnet"), ("Repariere meine Docker-Compose-Datei.", "sonnet"),
    ("Behebe diesen Python-Fehler.", "sonnet"), ("Implementiere dieses Feature.", "sonnet"),
    ("Implementiere eine REST API mit Authentifizierung.", "sonnet"), ("Refactore dieses Python-Modul.", "sonnet"),
    ("Warum funktioniert dieser Container nicht?", "sonnet"),
    ("Schreib mir eine Mail an die Fahrschule", "sonnet"),
    ("Entwirf eine sichere Architektur für meinen Home-Server.", "opus"),
    ("Entwirf eine Zero-Trust-Sicherheitsarchitektur für meinen Server.", "opus"),
    ("Analysiere dieses komplexe Netzwerkproblem.", "opus"),
    ("Analysiere einen schwer reproduzierbaren Race Condition Bug.", "opus"),
    ("Überprüfe diese Architektur auf schwerwiegende Sicherheitsprobleme.", "opus"),
    ("AI-Council: Prüfe diese Idee aus fünf Rollen und bewerte jede Rolle mit zwei bis vier Sätzen. " * 4 + "Idee: Soll ich den Server als einzige Umgebung nutzen?", "sonnet"),
]
ACCESS_CASES = [  # (Prompt, erwarteter Modus, erwarteter Ordner, Bestaetigung)
    ("Was steht in meinen Notizen zur Fahrschule?", "lesen", "notizen", False),
    ("Speichere das als Notiz", "notizen", "notizen", False),
    ("Wie viel Platz ist auf dem Server frei?", "lesen", "server", False),
    ("Starte den Docker-Dienst neu", "voll", "server", True),
    ("Ändere das Skript im Repo", "voll", "maserver", True),
    ("Zeig mir den Portal-Code", "lesen", "maserver", False),
]


def main():
    bad = 0
    for prompt, want in MODEL_CASES:
        got, reason = classify(prompt, mode="lesen")
        ok = got == want
        bad += not ok
        print(("PASS" if ok else "FAIL"), f"{want:6} {got:6} {reason:24} {prompt}")
    for prompt, mode, folder, confirm in ACCESS_CASES:
        got = suggest_access(prompt)
        ok = got == (mode, folder, confirm)
        bad += not ok
        print(("PASS" if ok else "FAIL"), got, "<-", prompt)
    # feste Regeln
    checks = [
        ("manuell hat Vorrang", choose("Liste die Dateien auf.", manual="opus")[0] == "opus"),
        ("Fable gesperrt", choose("Liste die Dateien auf.", manual="fable")[0] in ("haiku", "sonnet", "opus") and choose("x", manual="fable")[2] != "manual"),
        ("Bilder nie Haiku", classify("Was ist das?", "lesen", True)[0] != "haiku"),
        ("voll_senden nie vorgeschlagen", all(suggest_access(p)[0] != "voll_senden" for p, *_ in ACCESS_CASES + [("Sende die Mail ab und lösche den Entwurf", 0, 0, 0)])),
        ("Aufwand: opus hoch, haiku niedrig", choose("Liste die Dateien auf.")[1] == "low" and choose("Entwirf eine Zero-Trust-Sicherheitsarchitektur")[1] == "high"),
    ]
    for name, ok in checks:
        bad += not ok
        print(("PASS" if ok else "FAIL"), name)
    total = len(MODEL_CASES) + len(ACCESS_CASES) + len(checks)
    print(f"\n{total - bad}/{total} bestanden")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
