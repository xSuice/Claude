#!/usr/bin/env python3
"""V10 isolation for self-generated code (Linux, no extra software, no root needed).

The command runs in fresh user + mount + network + PID namespaces (`unshare`):
  * whole filesystem read-only (recursive mount_setattr), only the work directory writable
  * configured secret paths (home dirs, ~/.ssh, ~/.claude, brain state/config, the real repo,
    the vault) hidden behind empty tmpfs mounts
  * no network at all (new netns, loopback down), own PID space, rlimits from runner
If the kernel does not allow this, `available()` is False and callers must fail closed.

V16: second backend `bwrap` (bubblewrap). Ubuntu >= 24.04 blocks unprivileged user namespaces
for ordinary programs via AppArmor (kernel.apparmor_restrict_unprivileged_userns=1), which made
the own jail unavailable on the real MA-Server. bubblewrap ships its own AppArmor profile and
builds the same jail (read-only /, hidden paths, only work writable, no net, own PID + /proc,
no capabilities, no_new_privs, no nested user namespaces). Order: own jail, then bwrap, else
none (fail closed). BRAIN_SANDBOX=unshare|bwrap|none forces one backend (tests; 'none' can
only switch isolation off for callers that then refuse to run, never bypass it).
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MS_RDONLY, MS_NOSUID, MS_NODEV, MS_NOEXEC, MS_BIND, MS_REC, MS_PRIVATE = 1, 2, 4, 8, 4096, 16384, 1 << 18
MOUNT_ATTR_RDONLY, AT_RECURSIVE, AT_FDCWD, SYS_mount_setattr = 0x1, 0x8000, -100, 442
DEFAULT_HIDE = ['/root', '/home', '/etc/ssh', '/etc/shadow', '/etc/sudoers.d', '/var/lib/docker',
                '/run/docker.sock', '/var/run/docker.sock', '/run/user']
_libc = None


def _c():
    global _libc
    if _libc is None:
        _libc = ctypes.CDLL(None, use_errno=True)
    return _libc


def _mount(src, dst, fstype, flags, data=None):
    r = _c().mount(src and src.encode(), dst.encode(), fstype and fstype.encode(), ctypes.c_ulong(flags),
                   data and data.encode())
    if r != 0:
        e = ctypes.get_errno()
        raise OSError(e, f'mount {dst}: {os.strerror(e)}')


class _MountAttr(ctypes.Structure):
    _fields_ = [('attr_set', ctypes.c_uint64), ('attr_clr', ctypes.c_uint64),
                ('propagation', ctypes.c_uint64), ('userns_fd', ctypes.c_uint64)]


def _setattr(path, set_=0, clr=0, recursive=False):
    a = _MountAttr(set_, clr, 0, 0)
    r = _c().syscall(SYS_mount_setattr, AT_FDCWD, path.encode(), AT_RECURSIVE if recursive else 0,
                     ctypes.byref(a), ctypes.sizeof(a))
    if r != 0:
        e = ctypes.get_errno()
        raise OSError(e, f'mount_setattr {path}: {os.strerror(e)}')


def _init(spec: dict):
    """Runs as PID 1 of the new namespaces. Builds the jail, then execs the command."""
    work = spec['work']
    fd = os.open(work, os.O_RDONLY | os.O_DIRECTORY)         # keeps the work dir reachable after hiding
    _mount(None, '/', None, MS_REC | MS_PRIVATE)
    for h in spec['hide']:
        if os.path.islink(h) or not os.path.exists(h):
            continue
        if os.path.realpath(h) == os.path.realpath(work):
            continue  # the work dir itself is meant to be visible (hiding it left it empty)
        if os.path.isdir(h):
            _mount('tmpfs', h, 'tmpfs', MS_NOSUID | MS_NODEV, 'size=1m,mode=755')
        else:
            _mount('/dev/null', h, None, MS_BIND)
    os.makedirs(work, exist_ok=True)                          # (re)create the path inside a hiding tmpfs
    _mount(f'/proc/self/fd/{fd}', work, None, MS_BIND | MS_REC)
    os.close(fd)
    # V10.1: a fresh /proc for our own PID namespace (host processes and their environ invisible)
    _mount('proc', '/proc', 'proc', MS_NOSUID | MS_NODEV | MS_NOEXEC)
    _setattr('/', set_=MOUNT_ATTR_RDONLY, recursive=True)    # everything read-only ...
    _setattr(work, clr=MOUNT_ATTR_RDONLY)                     # ... except the work directory
    _setattr('/proc', clr=MOUNT_ATTR_RDONLY)                  # needed once below for uid_map
    _drop_privileges()
    os.chdir(spec['cwd'])
    env = dict(spec['env'])
    env['TMPDIR'] = os.path.join(work, '.sandbox-tmp')
    os.makedirs(env['TMPDIR'], exist_ok=True)
    os.execvpe(spec['argv'][0], spec['argv'], env)


CLONE_NEWUSER, PR_SET_NO_NEW_PRIVS, SANDBOX_UID = 0x10000000, 38, 1000


def _drop_privileges():
    """V10.1: enter a second, nested user namespace as an unprivileged uid. The jail's mounts
    belong to the outer namespace, so they can no longer be unmounted, remounted or extended,
    and because the uid is not 0 the following execve() leaves no capabilities at all."""
    if _c().unshare(CLONE_NEWUSER) != 0:
        e = ctypes.get_errno(); raise OSError(e, f'unshare(NEWUSER): {os.strerror(e)}')
    with open('/proc/self/setgroups', 'w') as fh:
        fh.write('deny')
    with open('/proc/self/uid_map', 'w') as fh:
        fh.write(f'{SANDBOX_UID} 0 1')
    with open('/proc/self/gid_map', 'w') as fh:
        fh.write(f'{SANDBOX_UID} 0 1')
    os.setresgid(SANDBOX_UID, SANDBOX_UID, SANDBOX_UID)
    os.setresuid(SANDBOX_UID, SANDBOX_UID, SANDBOX_UID)
    if _c().prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        e = ctypes.get_errno(); raise OSError(e, f'prctl(NO_NEW_PRIVS): {os.strerror(e)}')


_BACKEND: list = []  # cached result of backend()


def _unshare_ok() -> bool:
    if sys.platform != 'linux' or not shutil.which('unshare'):
        return False
    try:
        p = subprocess.run(['unshare', '--user', '--map-root-user', '--mount', '--net', '--pid', '--fork',
                            sys.executable, '-I', str(Path(__file__).resolve()), '--init', json.dumps({
                                'argv': ['/bin/true' if os.path.exists('/bin/true') else sys.executable],
                                'work': tempfile.gettempdir(), 'cwd': tempfile.gettempdir(),
                                'env': {'PATH': '/usr/bin:/bin'}, 'hide': []})],
                           capture_output=True, timeout=20)
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _bwrap_ok() -> bool:
    exe = shutil.which('bwrap')
    if sys.platform != 'linux' or not exe:
        return False
    try:
        p = subprocess.run([exe, '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc', '--unshare-all',
                            '--unshare-user', '--disable-userns', '--die-with-parent', '--new-session', '--cap-drop', 'ALL',
                            '/bin/true' if os.path.exists('/bin/true') else sys.executable, *([] if os.path.exists('/bin/true') else ['-c', ''])],
                           capture_output=True, timeout=20)
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def backend() -> str | None:
    """'unshare' | 'bwrap' | None. Probed once per process."""
    if not _BACKEND:
        forced = os.environ.get('BRAIN_SANDBOX', '').strip().lower()
        if forced == 'none':
            _BACKEND.append(None)
        elif forced == 'unshare':
            _BACKEND.append('unshare' if _unshare_ok() else None)
        elif forced == 'bwrap':
            _BACKEND.append('bwrap' if _bwrap_ok() else None)
        else:
            _BACKEND.append('unshare' if _unshare_ok() else ('bwrap' if _bwrap_ok() else None))
    return _BACKEND[0]


def available() -> bool:
    return backend() is not None


def _hidden(paths: list[str], work: str) -> list[str]:
    """Existing, non-symlink paths to hide, minus the work dir itself and minus paths already
    covered by a hidden parent (the parent's empty tmpfs hides them anyway)."""
    out: list[str] = []
    real = {os.path.realpath(h) for h in paths if not os.path.islink(h) and os.path.exists(h)}  # /var/run -> /run
    for h in sorted(real, key=lambda p: (len(p), p)):
        if h == os.path.realpath(work):
            continue
        if any(h == o or h.startswith(o.rstrip('/') + '/') for o in out):
            continue
        out.append(h)
    return out


def _wrap_bwrap(argv: list[str], work: str, cwd: str, env: dict, hide: list[str]) -> list[str]:
    tmp = os.path.join(work, '.sandbox-tmp')
    os.makedirs(tmp, exist_ok=True)
    cmd = [shutil.which('bwrap') or 'bwrap', '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc']
    for h in _hidden(hide, work):
        cmd += ['--tmpfs', h] if os.path.isdir(h) else ['--ro-bind', '/dev/null', h]
    cmd += ['--bind', work, work, '--unshare-all', '--unshare-user', '--disable-userns', '--die-with-parent', '--new-session',
            '--cap-drop', 'ALL', '--clearenv']
    for k, v in {**env, 'TMPDIR': tmp}.items():
        cmd += ['--setenv', k, v]
    return cmd + ['--chdir', cwd, '--', *argv]


def wrap(argv: list[str], work: Path, cwd: Path, env: dict, hide: list[str]) -> list[str]:
    """Return an argv that runs `argv` inside the jail. The spec travels as one JSON argument."""
    spec = {'argv': argv, 'work': str(Path(work).resolve()), 'cwd': str(Path(cwd).resolve()), 'env': env,
            'hide': sorted(set(DEFAULT_HIDE) | {str(Path(h).expanduser()) for h in hide})}
    kind = backend()
    if kind == 'bwrap':
        return _wrap_bwrap(argv, spec['work'], spec['cwd'], env, spec['hide'])
    if kind is None:
        raise RuntimeError('no sandbox backend available: refusing to run unisolated')
    return ['unshare', '--user', '--map-root-user', '--mount', '--net', '--pid', '--fork', '--kill-child',
            sys.executable, '-I', str(Path(__file__).resolve()), '--init', json.dumps(spec)]


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--init':
        _init(json.loads(sys.argv[2]))
    print(json.dumps({'sandbox_available': available(), 'backend': backend()}))
