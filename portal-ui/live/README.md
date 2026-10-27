# Live-Stand ma-server (Spiegel, Stand 2026-10-27)
Kopien der produktiven Dateien (Quelle der Wahrheit ist weiterhin der Server):
portal.py, agent.py, chat_bus_*.py -> /opt/ma-home/ · db_adapter.py, jarvis_portal_bridge.py, heartbeat_report.py -> /opt/jarvis/council/ · rollback-cutover.sh -> /opt/ma-home/
Neue Oberflaeche (JARVIS HQ): portal-ui/hq/ (liegt live unter /opt/ma-home/web/staging/, Route / und /staging/). Klassisch: /classic/ (portal-ui/web/).
Rollback Portal: sudo bash /opt/ma-home/rollback-cutover.sh. Doku: docs/jarvis/v3/. Windows-Hilfsdienste: scripts/windows-hermes/.
