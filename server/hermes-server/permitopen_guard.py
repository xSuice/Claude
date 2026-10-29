"""authorized_keys: Schlüssel hermes-mahome darf Port-Weiterleitungen nur noch zu 18765 (Portal) und 18790 (Sprache) öffnen.
Damit kann das PC-Gateway den Signal-Dienst (18769) nicht mehr erreichen; Shell-Zugang und -R-Tunnel bleiben unberührt.
Sicherheitsnetz: Ohne Bestätigungsdatei ~/.ssh/permitopen-ok stellt der Server nach 180 s die Sicherung selbst wieder her.
Aufruf: permitopen_guard.py apply | confirm | revert"""
import os
import shutil
import sys
import time
from pathlib import Path

AK = Path.home() / '.ssh/authorized_keys'
BAK = Path.home() / '.ssh/authorized_keys.bak-vor-permitopen-20261029'
OK = Path.home() / '.ssh/permitopen-ok'
OPTS = 'permitopen="127.0.0.1:18765",permitopen="127.0.0.1:18790"'


def write(text):
    tmp = AK.with_name('authorized_keys.tmp')
    tmp.write_text(text, encoding='utf-8')
    os.chmod(tmp, 0o600)
    os.replace(tmp, AK)


def apply():
    if not BAK.exists():
        shutil.copy2(AK, BAK)
    OK.unlink(missing_ok=True)
    lines = AK.read_text(encoding='utf-8').splitlines()
    out, hit = [], 0
    for l in lines:
        if l.startswith('ssh-ed25519 ') and l.rstrip().endswith(' hermes-mahome'):
            l = OPTS + ' ' + l
            hit += 1
        out.append(l)
    assert hit == 1, 'Schlüssel hermes-mahome nicht eindeutig gefunden: %d' % hit
    write('\n'.join(out) + '\n')
    print('gesetzt; Rückbau in 180 s ohne Bestätigung', flush=True)
    # Wächter: läuft im Hintergrund weiter (nohup), stellt ohne Bestätigung zurück
    pid = os.fork()
    if pid:
        return
    os.setsid()
    time.sleep(180)
    if not OK.exists():
        shutil.copy2(BAK, AK)
        os.chmod(AK, 0o600)


def confirm():
    OK.write_text('ok')
    print('bestätigt')


def revert():
    shutil.copy2(BAK, AK)
    os.chmod(AK, 0o600)
    print('zurückgestellt')


if __name__ == '__main__':
    {'apply': apply, 'confirm': confirm, 'revert': revert}[sys.argv[1]]()
