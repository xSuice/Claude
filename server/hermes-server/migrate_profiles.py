"""Create server-side JARVIS roles using the official Hermes CLI. No live routing switch."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path.home() / '.hermes/profiles'
STAGE = Path.home() / 'hermes-qualification/profile-souls'
HERMES = str(Path.home() / '.local/bin/hermes')
RESULT = Path.home() / 'hermes-qualification/profile-migration.json'


def run(args):
    p = subprocess.run([HERMES, *args], capture_output=True, text=True, timeout=90)
    if p.returncode:
        raise RuntimeError('Hermes CLI failed: ' + ' '.join(args[:5]) + ' rc=' + str(p.returncode))


def main():
    names = sorted(p.name for p in STAGE.iterdir() if p.is_dir())
    results = []
    for name in names:
        if not (name.startswith('jarvis-') or name == 'kimi-supervisor'):
            raise ValueError('unexpected profile')
        dest = ROOT / name
        # Existing profiles are not overwritten on a resumed run.
        marker = dest / '.server-migration-complete'
        if not marker.exists():
            if not dest.exists():
                run(['profile', 'create', name, '--clone-from', 'jarvis-server', '--no-alias'])
            for key, value in [
                ('model.provider', 'kimi' if name == 'kimi-supervisor' else 'nexum'),
                ('model.default', 'kimi-for-coding' if name == 'kimi-supervisor' else 'qwen-3.8-omni-flash'),
                ('platform_toolsets.cli', '[web, skills, memory, session_search]'),
                ('agent.max_turns', '8'),
                ('agent.run_budget_seconds', '120'),
            ]:
                run(['-p', name, 'config', 'set', key, value])
            soul = STAGE / name / 'SOUL.md'
            if soul.exists():
                current = dest / 'SOUL.md'
                if current.exists() and not (dest / 'SOUL.md.before-server-role').exists():
                    (dest / 'SOUL.md.before-server-role').write_bytes(current.read_bytes())
                current.write_bytes(soul.read_bytes())
            os.chmod(dest / '.env', 0o600)
            marker.write_text('Prepared on server; not proof of live routing.\n')
        results.append({'profile': name, 'prepared': marker.exists(), 'secret_mode': oct((dest / '.env').stat().st_mode & 0o777)})
        RESULT.write_text(json.dumps(results, indent=2))
        print(name + ': prepared', flush=True)
    print('COUNT=' + str(len(results)), flush=True)


if __name__ == '__main__':
    main()
