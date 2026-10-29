from pathlib import Path
import re
bad, kimi = [], []
for p in sorted((Path.home() / '.hermes/profiles').iterdir()):
    if not (p.name.startswith('jarvis-') or p.name == 'kimi-supervisor'):
        continue
    s = (p / 'config.yaml').read_text()
    head = s.split('\nagent:')[0]
    prov = re.search(r'provider:\s*(\w+)', head).group(1)
    fb = s.split('fallback_providers:')[1].split('\nmoa:')[0] if 'fallback_providers:' in s else ''
    if p.name == 'kimi-supervisor':
        if prov != 'kimi':
            bad.append(p.name)
    else:
        if prov != 'nexum':
            bad.append((p.name, prov))
        if 'kimi' in fb:
            kimi.append(p.name)
print('falsch:', bad, '| Kimi im Ausweich:', kimi)
