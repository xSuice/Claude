import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "config.json"
LOG_FILE = ROOT / "router.log"


DEFAULT_CONFIG = {
    "default_model": "sonnet",
    "models": {
        "haiku": "haiku",
        "sonnet": "sonnet",
        "opus": "opus"
    },
    "logging": True
}


def load_config():
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG

    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    result = DEFAULT_CONFIG.copy()
    result.update(data)

    if "models" not in result:
        result["models"] = DEFAULT_CONFIG["models"]

    return result


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def contains_any(text, patterns):
    return any(re.search(pattern, text, re.I) for pattern in patterns)


# ------------------------------------------------------------
# Klassifizierung
# ------------------------------------------------------------

def classify(prompt):
    p = normalize(prompt)

    # --------------------------------------------------------
    # OPUS
    # Nur Aufgaben mit klar erhöhtem Reasoning-Bedarf.
    # --------------------------------------------------------

    opus_patterns = [
        r"\bzero[- ]trust\b",
        r"\bsicherheitsarchitektur\b",
        r"\bsecurity architecture\b",
        r"\bthreat model",
        r"\bbedrohungsmodell",
        r"\brace condition\b",
        r"\bdeadlock\b",
        r"\bschwer reproduzierbar",
        r"\bhard[- ]to[- ]reproduce",
        r"\bkomplex(?:e|es|en|er)? netzwerkproblem",
        r"\bcomplex network",
        r"\barchitektur.*sicherheit",
        r"\bsecurity.*architecture",
        r"\bschwerwiegend(?:e|en|er)? sicherheits",
        r"\bdeep architectural",
        r"\bgrundlegend(?:e|en|er)? architektur",
    ]

    if contains_any(p, opus_patterns):
        return "opus", "high_reasoning"

    # Kombinationen können ebenfalls Opus rechtfertigen.

    architecture = contains_any(
        p,
        [
            r"\barchitektur",
            r"\barchitecture",
            r"\bsystem design\b",
            r"\bdesign.*system",
        ],
    )

    security = contains_any(
        p,
        [
            r"\bsicherheit",
            r"\bsecurity",
            r"\bauthentication",
            r"\bauthorization",
            r"\bzero trust",
        ],
    )

    complexity = contains_any(
        p,
        [
            r"\bkomplex",
            r"\bcomplex",
            r"\bumfangreich",
            r"\bdetailliert analys",
            r"\btiefgehend",
            r"\bdeep analysis",
        ],
    )

    if architecture and security:
        return "opus", "security_architecture"

    if architecture and complexity:
        return "opus", "complex_architecture"

    # --------------------------------------------------------
    # SONNET
    # Schreibende / implementierende / reparierende Aufgaben.
    # Sonnet ist bewusst der Default.
    # --------------------------------------------------------

    write_patterns = [
        r"\berstell(?:e|en)\b",
        r"\bschreib(?:e|en)\b",
        r"\bimplementier",
        r"\bänder(?:e|n)\b",
        r"\bmodifizier",
        r"\breparier",
        r"\bbeheb",
        r"\bfix(?:e|en)?\b",
        r"\brefactor",
        r"\brefaktor",
        r"\bfüge .* hinzu",
        r"\bentfern(?:e|en)\b",
        r"\bkonfigurier",
        r"\binstallier",
        r"\bmigrier",
        r"\boptimiere",
        r"\boptimize",
        r"\bcreate\b",
        r"\bwrite\b",
        r"\bimplement\b",
        r"\bmodify\b",
        r"\brepair\b",
    ]

    debugging_patterns = [
        r"\bdebug",
        r"\bfehler beheben",
        r"\bbug\b",
        r"\bexception\b",
        r"\btraceback\b",
        r"\bwarum funktioniert",
        r"\bwarum geht",
        r"\bursache.*fehler",
    ]

    if contains_any(p, write_patterns):
        return "sonnet", "write_or_modify"

    if contains_any(p, debugging_patterns):
        return "sonnet", "debugging"

    # --------------------------------------------------------
    # HAIKU
    # Sehr konservativ.
    # Nur klar einfache / read-only Aufgaben.
    # --------------------------------------------------------

    simple_patterns = [
        r"^liste (?:mir )?(?:die )?dateien",
        r"^zeige (?:mir )?(?:die )?dateien",
        r"^welche dateien",
        r"^suche (?:nach )?",
        r"^finde (?:die |den |das )?.*(?:datei|config|konfiguration)",
        r"^was steht in .+",
        r"^lies .+(?:datei|readme)",
        r"^zeige .*status",
        r"^status (?:von|der|aller)",
        r"^docker ps",
        r"^git status",
        r"^git branch",
        r"^zeige .*docker-container",
        r"^liste .*docker-container",
    ]

    dangerous_for_haiku = [
        r"\berstell",
        r"\bschreib",
        r"\bänder",
        r"\bimplement",
        r"\brepar",
        r"\bbeheb",
        r"\bdebug",
        r"\barchitektur",
        r"\barchitecture",
        r"\bsicherheit",
        r"\bsecurity",
        r"\bkomplex",
        r"\bcomplex",
        r"\brefactor",
        r"\boptimi",
        r"\bmigrier",
    ]

    if (
        contains_any(p, simple_patterns)
        and not contains_any(p, dangerous_for_haiku)
        and len(p) <= 300
    ):
        return "haiku", "clearly_simple_read_only"

    # --------------------------------------------------------
    # FAIL SAFE
    # --------------------------------------------------------

    return "sonnet", "default"


def log_decision(model, reason):
    config = load_config()

    if not config.get("logging", True):
        return

    line = (
        f"{datetime.now().isoformat(timespec='seconds')}\t"
        f"{model}\t{reason}\n"
    )

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)


def choose_model(prompt):
    model, reason = classify(prompt)
    log_decision(model, reason)
    return model, reason


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print()
        print("Claude Local Model Router")
        print()
        print('Verwendung:')
        print('  cr "Liste die Dateien auf."')
        print()
        print('Nur testen:')
        print('  cr --route "Liste die Dateien auf."')
        print()
        return 1

    route_only = False

    args = sys.argv[1:]

    if args[0] == "--route":
        route_only = True
        args = args[1:]

    if not args:
        print("Kein Prompt angegeben.")
        return 1

    prompt = " ".join(args)

    model, reason = choose_model(prompt)

    print()
    print("-----------------------------------------")
    print(f" Router: {model.upper()}")
    print(f" Grund : {reason}")
    print("-----------------------------------------")
    print()

    if route_only:
        return 0

    config = load_config()

    actual_model = config["models"].get(model, model)

    command = [
        "claude",
        "--model",
        actual_model,
        prompt,
    ]

    try:
        return subprocess.call(command)
    except FileNotFoundError:
        print("Claude Code wurde nicht gefunden.")
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
