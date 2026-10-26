"""T12 check: python3 check.py RESULT_DIR
Statische Prüfung des Ergebnisses (läuft überall). Der echte Build-Nachweis (`gradle build` grün, JAR vorhanden) kommt vom
PC-Worker und gehört in das JARVIS-Protokoll; ohne ihn bleibt das Kriterium 'build-am-pc' ausdrücklich unbelegt (nicht bestanden)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import Check  # noqa: E402


def main():
    c = Check('T12', sys.argv[1])
    bg = c.file('build.gradle') if c.file('build.gradle').is_file() else c.file('build.gradle.kts')
    c.ok('build-datei', bg.is_file())
    txt = bg.read_text(encoding='utf-8', errors='replace') if bg.is_file() else ''
    c.ok('java-plugin', "'java'" in txt or '"java"' in txt or 'java' in txt.lower())
    c.ok('junit5', 'junit-jupiter' in txt or 'useJUnitPlatform' in txt)
    mains = list(c.work.glob('src/main/java/**/Main.java'))
    c.ok('main-klasse', bool(mains) and 'quadrat' in mains[0].read_text(encoding='utf-8', errors='replace') and 'package app' in mains[0].read_text(encoding='utf-8', errors='replace'))
    tests = list(c.work.glob('src/test/java/**/*.java'))
    c.ok('test-vorhanden', bool(tests) and '@Test' in tests[0].read_text(encoding='utf-8', errors='replace'))
    c.ok('readme-build', c.file('README.md').is_file() and 'gradle' in c.file('README.md').read_text(encoding='utf-8', errors='replace').lower())
    jars = list(c.work.glob('build/libs/*.jar'))
    c.ok('build-am-pc', bool(jars), 'kein build/libs/*.jar im Ergebnis (PC-Build nicht belegt)' if not jars else jars[0].name)
    c.done()


if __name__ == '__main__':
    main()
