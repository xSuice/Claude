# Erweiterungsauftrag: echte neuronale Forschungsmodelle für mein Claude Code

Verwende `Claude-Code-Gehirn-Masterauftrag.md` als primären Auftrag. Ergänzend gilt:

1. Erfasse mit Belegen den tatsächlichen Setup-Stand. Keine impliziten Installationsannahmen. Sichere vor Änderungen.
2. Prüfe meine verfügbaren Ressourcen. Installiere **nicht** standardmäßig alle Gehirnmodelle; es handelt sich um Forschungssoftware, nicht um zusätzliche trainierte Claude-Kompetenzen.
3. Führe die offline lauffähigen Tests von `scientific-brains/` aus. Der beigefügte OpenWorm-Ausschnitt ist echt, aber nur ein kleiner Teil der biologischen Verbindungen. Verwende bei vertretbarem Ressourcenbudget die Original-CSV aus dem Upstream-Repository und protokolliere SHA-256/Version. Netzwerkdownload ist separat.
4. Teste `nengo_action_selection.py` nach Kompatibilitäts-/Sicherheitsprüfung in isolierter Umgebung, falls Ressourcen und Berechtigung vorhanden sind. Berichte auch negative Ergebnisse. Das tatsächliche NengoSPA-Modul muss ausgeführt werden, bloß `max()` umbenennen zählt nicht.
5. Prüfe optional Forschungssoftware für Drosophila (`eonsystemspbc/fly-brain`) und menschliche Makronetzwerke (`the-virtual-brain/tvb-root`), ohne sie ohne Nutzenbeleg in den Startpfad zu laden. Upstream-Lizenzen, RAM, GPU und Import-/Integrationskosten dokumentieren.
6. Vergleiche jede Integration mit der bestehenden lokalen Regel-/DB-/RAG-Lösung bei **gleichen Qualitätskriterien**. Die genannten Experimente sind keine Tests für Textverständnis, Serverfehler oder Claude-Codingqualität. Keine unbewiesenen Versprechen zu intelligenterem Claude, weniger Pro-Limit oder menschlichem Bewusstsein.
7. Nur bei **nachweislicher** Verbesserung, nachvollziehbarer Semantik der neuronalen Ein-/Ausgänge und sicherem Rollback: behutsame optional aktivierbare CLI-Schnittstelle im vorhandenen Gateway. Niemals eine neuronale Ausgabe als Authentifizierungs-, Zugriffs- oder Sicherheitsfreigabe verwenden.
8. Im V5-Wirkungsregister nachprüfbar festhalten, was aus echten Forschungsmodellen stammt, was selbst geschrieben wurde, was lokal nur technisch geprüft wurde und was in realen Claude-Aufgaben besser wurde.

Vorrang: Qualität, Sicherheit und geringer Gesamtverbrauch vor der Anzahl installierter Gehirnsimulationen. Weiterentwicklung und Humanizer aus V2 bleiben aktiv, sofern vorhanden.
