# jarvis-portal.service — Deployment-Dokumentation

## Unit-Pfad
- Systemd-Unit: /etc/systemd/system/jarvis-portal.service
- Source im Repo: server/jarvis/portal/systemd/jarvis-portal.service
- Secrets-Template: server/jarvis/portal/systemd/portal.env.template

## Dependencies
- After: network-online.target, postgresql.service, jarvis-core.target
- Requires: postgresql.service
- PartOf: jarvis-core.target
- WantedBy: multi-user.target (enabled)

## Runtime
- User=ma-web, Group=ma-web
- WorkingDirectory: /opt/jarvis/portal
- ReadWritePaths: /opt/jarvis/portal/var, /var/log/jarvis/portal
- EnvironmentFile: /etc/jarvis/portal.env (0640 root:ma-web)

## Sandbox
- ProtectSystem=strict, ProtectHome=read-only, PrivateTmp=true
- NoNewPrivileges=true, MemoryDenyWriteExecute=true
- RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX

## Secrets-Handling
- KEINE Secrets inline, alle via /etc/jarvis/portal.env
- Template: JARVIS_DB_DSN, JARVIS_SECRET_KEY, JARVIS_BIND_HOST, JARVIS_BIND_PORT, JARVIS_LOG_LEVEL
- Bis zur Befüllung: fail-hard

## Status
- Phase 2 AP-9: deployed 2026-10-26 07:12 UTC, enabled
- KEIN systemctl start bis Secrets befördert

## Governance
- Kein merge in main/master ohne Planner-Review
- Secrets niemals ins Repo (nur .template)
