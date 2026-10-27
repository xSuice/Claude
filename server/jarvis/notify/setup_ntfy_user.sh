#!/bin/bash
# N-01: dedicated write-only ntfy user for JARVIS notifications. Run as root. Idempotent-ish: aborts if user exists.
set -euo pipefail
C=ma-home-ntfy-1
if docker exec "$C" ntfy user list 2>/dev/null | grep -q '^user jarvis-notify'; then echo "user exists - abort"; exit 3; fi
PW=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')
export NTFY_PASSWORD="$PW"
docker exec -e NTFY_PASSWORD "$C" ntfy user add --role=user jarvis-notify
docker exec "$C" ntfy access jarvis-notify andrew-jarvis write-only
umask 077
install -d -m 700 -o andrew -g andrew /home/andrew/.config/ma-jarvis
printf 'jarvis-notify:%s' "$PW" > /home/andrew/.config/ma-jarvis/ntfy-notify.cred
chown andrew:andrew /home/andrew/.config/ma-jarvis/ntfy-notify.cred; chmod 600 /home/andrew/.config/ma-jarvis/ntfy-notify.cred
unset PW NTFY_PASSWORD
echo "created user jarvis-notify (write-only on andrew-jarvis); credential file written (0600)"
docker exec "$C" ntfy access jarvis-notify
