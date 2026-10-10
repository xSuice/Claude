import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from router import classify


TESTS = [
    ("Liste die Dateien auf.", "haiku"),
    ("Liste die Dateien im aktuellen Projekt auf.", "haiku"),
    ("Was steht in README.md?", "haiku"),
    ("Suche nach der FileBrowser-Konfiguration.", "haiku"),
    ("Zeige mir den Status der Docker-Container.", "haiku"),
    ("docker ps", "haiku"),
    ("git status", "haiku"),

    (
        "Erstelle ein Bash-Skript, das den Status aller Docker-Container prüft.",
        "sonnet",
    ),
    (
        "Erstelle ein Bash-Skript für Docker-Healthchecks.",
        "sonnet",
    ),
    (
        "Ändere meine Docker-Compose-Konfiguration.",
        "sonnet",
    ),
    (
        "Repariere meine Docker-Compose-Datei.",
        "sonnet",
    ),
    (
        "Behebe diesen Python-Fehler.",
        "sonnet",
    ),
    (
        "Implementiere dieses Feature.",
        "sonnet",
    ),
    (
        "Implementiere eine REST API mit Authentifizierung.",
        "sonnet",
    ),
    (
        "Refactore dieses Python-Modul.",
        "sonnet",
    ),
    (
        "Warum funktioniert dieser Container nicht?",
        "sonnet",
    ),

    (
        "Entwirf eine sichere Architektur für meinen Home-Server.",
        "opus",
    ),
    (
        "Entwirf eine Zero-Trust-Sicherheitsarchitektur für meinen Server.",
        "opus",
    ),
    (
        "Analysiere dieses komplexe Netzwerkproblem.",
        "opus",
    ),
    (
        "Analysiere einen schwer reproduzierbaren Race Condition Bug.",
        "opus",
    ),
    (
        "Überprüfe diese Architektur auf schwerwiegende Sicherheitsprobleme.",
        "opus",
    ),
]


def main():
    passed = 0
    failed = []

    counts = {
        "haiku": {"correct": 0, "total": 0},
        "sonnet": {"correct": 0, "total": 0},
        "opus": {"correct": 0, "total": 0},
    }

    false_haiku = 0
    non_haiku_total = 0

    print()
    print("Claude Model Router Tests")
    print("=" * 70)

    for prompt, expected in TESTS:
        actual, reason = classify(prompt)

        counts[expected]["total"] += 1

        if expected != "haiku":
            non_haiku_total += 1
            if actual == "haiku":
                false_haiku += 1

        ok = actual == expected

        if ok:
            passed += 1
            counts[expected]["correct"] += 1
            status = "PASS"
        else:
            status = "FAIL"
            failed.append((prompt, expected, actual))

        print(
            f"{status:4} | expected={expected:6} "
            f"actual={actual:6} | {reason}"
        )
        print(f"       {prompt}")

    total = len(TESTS)

    print()
    print("=" * 70)
    print(f"Gesamt: {passed}/{total}")

    for model in ("haiku", "sonnet", "opus"):
        correct = counts[model]["correct"]
        amount = counts[model]["total"]

        rate = (correct / amount * 100) if amount else 0

        print(
            f"{model.capitalize():7}: "
            f"{correct}/{amount} ({rate:.1f}%)"
        )

    false_rate = (
        false_haiku / non_haiku_total * 100
        if non_haiku_total
        else 0
    )

    print(f"False-Haiku-Rate: {false_rate:.1f}%")

    if failed:
        print()
        print("Fehlgeschlagene Tests:")

        for prompt, expected, actual in failed:
            print(
                f"- {prompt}\n"
                f"  erwartet: {expected}, erhalten: {actual}"
            )

        return 1

    print()
    print("Alle Tests bestanden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
