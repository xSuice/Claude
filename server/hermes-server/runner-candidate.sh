#!/usr/bin/env bash
# jarvis-server in bubblewrap. Ergebnis der Abschottung (test_sandbox.sh):
#  - schreiben nur im Auftragsordner + Hermes-Laufzeit (~/.hermes: Gateway, Sitzungen, Logs, Speicher)
#  - sudo technisch unmöglich (no_new_privs, keine Capabilities), kein neuer User-Namespace
#  - Schlüssel/SSH/Claude-Login/Portal-Schlüssel unsichtbar; Schlüssel nur als Umgebungsvariable
#  - alles, was Code ausführt oder Verhalten steuert (Hermes-Code, Werkzeuge, Hooks, Plugins, Konfiguration,
#    SOUL), read-only; Programmordner installs/ mit Wegwerf-Schicht. Netz bleibt (Nexum/Kimi).
# Aufruf: jarvis-server-run.sh <arbeitsordner> -- <hermes-argumente...>
set -euo pipefail
WORK=$(realpath -e "$1"); shift; [ "${1:-}" = "--" ] && shift
H=/home/andrew
R=$H/.hermes
P=$R/profiles/jarvis-server
KEYS=$H/.config/ma-jarvis/keys
NEXUM=$(tr -d '\n' < "$KEYS/nexum.key"); KIMI=$(tr -d '\n' < "$KEYS/kimi.key")
case "$WORK" in /|/etc*|/usr*|/bin*|/sbin*|/boot*|/opt*|/var*|$H|$R*|$H/.config*|$H/.ssh*|$H/.local*) echo "Arbeitsordner nicht erlaubt: $WORK" >&2; exit 2;; esac
LEER=$R/leer; [ -f "$LEER" ] || install -m 444 /dev/null "$LEER"

HIDE=()
for d in "$KEYS" "$H/.ssh" "$H/.claude" "$H/.config/ma-github" "$H/.config/ma-jarvis" /etc/ma-home /root /run/ma-home /run/dbus /run/docker /run/containerd; do
  [ -d "$d" ] && HIDE+=(--tmpfs "$d")
done
for f in "$H/.claude.json" "$H/.netrc" "$H/.git-credentials"; do
  [ -f "$f" ] && HIDE+=(--ro-bind "$LEER" "$f")
done

RO=()
for x in hermes-agent tools hooks plugins platforms config.yaml SOUL.md \
         profiles/jarvis-server/config.yaml profiles/jarvis-server/SOUL.md profiles/jarvis-server/.env profiles/jarvis-server/hooks profiles/jarvis-server/plugins; do
  [ -e "$R/$x" ] && RO+=(--ro-bind "$R/$x" "$R/$x")
done
for f in "$R/.env"; do
  [ -f "$f" ] && RO+=(--ro-bind "$LEER" "$f")
done

exec bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  "${HIDE[@]}" \
  --bind "$R" "$R" \
  --overlay-src "$R/installs" --tmp-overlay "$R/installs" \
  "${RO[@]}" \
  --bind "$WORK" "$WORK" \
  --unshare-user --unshare-pid --unshare-ipc --unshare-uts --unshare-cgroup-try --share-net --disable-userns \
  --die-with-parent --new-session --cap-drop ALL --clearenv \
  --setenv HOME "$H" --setenv USER andrew --setenv LANG C.UTF-8 --setenv TERM dumb \
  --setenv PATH "$H/.local/bin:/usr/local/bin:/usr/bin:/bin" \
  --setenv NEXUM_API_KEY "$NEXUM" --setenv KIMI_API_KEY "$KIMI" \
  --chdir "$WORK" \
  "$H/.local/bin/hermes" -p jarvis-server "$@"
