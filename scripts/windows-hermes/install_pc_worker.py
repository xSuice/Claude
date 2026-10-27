"""Install the PC worker client locally (no admin): Temurin 21 JDK (checksum-verified, user-local),
jarvis.py + patched winsandbox.py, local capability allow-list for java.build (no network)."""
import hashlib, json, os, pathlib, shutil, subprocess, sys, urllib.request, zipfile

LOCAL = pathlib.Path(os.environ['LOCALAPPDATA']) / 'ma-jarvis'
CLIENT = LOCAL / 'client'
JDK_DIR = LOCAL / 'jdk-21'
HERE = pathlib.Path(__file__).resolve().parent

def jdk():
    if (JDK_DIR / 'bin' / 'javac.exe').exists():
        print('JDK vorhanden', JDK_DIR); return
    UA = {'User-Agent': 'MA-HOME-installer/1.0'}
    meta = json.load(urllib.request.urlopen(urllib.request.Request('https://api.adoptium.net/v3/assets/latest/21/hotspot?architecture=x64&image_type=jdk&os=windows&vendor=eclipse', headers=UA), timeout=60))
    pkg = meta[0]['binary']['package']
    assert pkg['name'].endswith('.zip'), pkg['name']
    LOCAL.mkdir(parents=True, exist_ok=True)
    z = LOCAL / pkg['name']
    with urllib.request.urlopen(urllib.request.Request(pkg['link'], headers=UA), timeout=600) as r, open(z, 'wb') as f:
        shutil.copyfileobj(r, f)
    h = hashlib.sha256(z.read_bytes()).hexdigest()
    assert h == pkg['checksum'], 'Checksumme falsch'
    print('VERIFIED', pkg['name'], h)
    tmp = LOCAL / 'jdk-extract'
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(z) as zf:
        zf.extractall(tmp)
    inner = next(tmp.iterdir())
    shutil.move(str(inner), str(JDK_DIR))
    shutil.rmtree(tmp, ignore_errors=True); z.unlink()
    print('JDK installiert', JDK_DIR)

def client():
    CLIENT.mkdir(parents=True, exist_ok=True)
    for f in ('jarvis.py', 'winsandbox.py', 'test_winsandbox.py'):
        shutil.copy2(HERE / f, CLIENT / f)
    state = pathlib.Path.home() / '.claude' / 'state'
    state.mkdir(parents=True, exist_ok=True)
    cfg = state / 'jarvis-pc.json'
    data = {'allowed': ['java.build'], 'java_home': str(JDK_DIR),
            'note': 'Freigabe Owner 27.10.2026: PC-Worker nur java.build, ohne Netz, isoliert (AppContainer).'}
    cfg.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Freigabe', cfg, data['allowed'])

if __name__ == '__main__':
    jdk(); client()
