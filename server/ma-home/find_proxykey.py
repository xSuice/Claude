"""SEC-001: find every file that contains the current portal proxy key (prints file names only, never the key)."""
import json, os, sys
key = json.load(open('/etc/ma-home/portal.json'))['proxy_key']
roots = ['/etc/ma-home', '/opt/ma-home', '/opt/jarvis', '/usr/local/lib', '/home/andrew/.config', '/home/andrew/.local/share/ma-jarvis/current',
         '/etc/systemd/system', '/home/andrew/MA-Server', '/srv/ma-home/caddy', '/etc/caddy']
skip = ('.git', 'node_modules', '__pycache__', 'releases', 'library')
hits = []
for r in roots:
    for d, ds, fs in os.walk(r):
        ds[:] = [x for x in ds if x not in skip]
        for f in fs:
            p = os.path.join(d, f)
            try:
                if os.path.getsize(p) > 5_000_000:
                    continue
                with open(p, 'rb') as fh:
                    if key.encode() in fh.read():
                        hits.append(p)
            except OSError:
                pass
print(len(key), 'chars;', len(hits), 'files')
for h in hits:
    print(h)
