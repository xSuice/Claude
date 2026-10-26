#!/usr/bin/env python3
"""vault-pg am PC: reicht die Argumente (mit Leerzeichen korrekt gequotet) per SSH an vault-pg.py auf dem Server weiter."""
import shlex
import subprocess
import sys

cmd = 'python3 ~/MA-Server/scripts/vault-pg.py ' + ' '.join(shlex.quote(a) for a in sys.argv[1:])
sys.exit(subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'ma-server', cmd]).returncode)
