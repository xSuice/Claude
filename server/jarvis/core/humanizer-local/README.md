# Humanizer für Claude Code – ohne unnötigen Tokenverbrauch

## Was enthalten ist

- `style_lint.py`: rein lokale, lesende Stilhinweise zu deutsch- und englischsprachigen Textdateien; **keine Modellaufrufe**.
- `test_style_lint.py`: Funktionstests für Erkennung und Schutz von Codeblöcken.
- Der eigentliche **blader/humanizer**-Skill ist ein separat zu prüfendes Drittanbieterprojekt; er ist **nicht** in dieser ZIP enthalten oder installiert. Quelle: https://github.com/blader/humanizer

## Verwendung

```powershell
python -m unittest -v test_style_lint.py
python style_lint.py ..\docs\mein-text.md
```

Nur wenn Claude Code noch keinen äquivalenten Humanizer hat, die Installation nach Versions- und Sicherheitsprüfung in Claude Code erwägen:

```text
/plugin marketplace add blader/humanizer
/plugin install humanizer@humanizer
```

Upstream weist auf die notwendige kompatible Claude-Code-Version hin. Die Alternative ist `npx skills add blader/humanizer --agent claude-code` in einer normalen Shell. Nicht beides parallel installieren.

## Qualität vor Stil

Ein lokaler Textcheck kann Auffälligkeiten markieren, aber nicht zuverlässig zwischen menschlichen und KI-generierten Texten unterscheiden oder hochwertigen Stil garantieren. Der Drittanbieter-Skill ruft bei seiner Textüberarbeitung Claude auf, was **zusätzliche Tokens** benötigt; deshalb bevorzugt natürlich beim ersten Entwurf schreiben, gezielt überarbeiten und Fakten/Links/Zahlen kontrollieren. Keine laufenden Claude-Hooks zum pauschalen Umschreiben.
