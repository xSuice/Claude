"""Candidate network isolation layered over the existing filesystem runner.
No services or host firewall changes. Only TLS to two provider hosts can leave.
Usage: python3 network_runner.py WORK -- COMMAND ARGS...
"""
import os
from pathlib import Path
import shlex
import signal
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
from egress_guard import relay, start_proxy


def inside(argv):
    class Forward(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                with socket.socket(socket.AF_UNIX) as upstream:
                    upstream.connect('/run/provider-egress.sock')
                    self.request.settimeout(90)
                    upstream.settimeout(90)
                    relay(self.request, upstream)
            except OSError:
                pass
    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True
    with Server(('127.0.0.1', 0), Forward) as server:
        proxy = 'http://127.0.0.1:' + str(server.server_address[1])
        for key in ('HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy'):
            os.environ[key] = proxy
        os.environ['NO_PROXY'] = os.environ['no_proxy'] = 'localhost,127.0.0.1,::1'
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            return subprocess.call(argv)
        finally:
            server.shutdown()


def outside(work, argv):
    base = Path(__file__).resolve().parent
    source = (base / 'runner-candidate.sh').read_text()
    tail = '"$H/.local/bin/hermes" -p jarvis-server "$@"'
    assert source.count(tail) == 1
    assert source.count('--share-net') == 1
    source = source.replace('--share-net', '--unshare-net')
    # Ephemeral root runtime metadata prevents attaching to an existing host gateway.
    source = source.replace('--bind "$R" "$R"', '--overlay-src "$R" --tmp-overlay "$R"')
    source = source.replace(tail, '/usr/bin/python3 ' + shlex.quote(str(Path(__file__).resolve())) + ' --inside "$@"')
    with tempfile.TemporaryDirectory(prefix='egress-', dir=base) as td:
        sock = str(Path(td) / 'proxy.sock')
        server = start_proxy(sock)
        os.chmod(sock, 0o600)
        anchor = '  --bind "$WORK" "$WORK"'
        assert source.count(anchor) == 1
        source = source.replace(anchor, '  --tmpfs /run --tmpfs /var/snap --ro-bind ' + shlex.quote(sock) + ' /run/provider-egress.sock \\\n' + anchor)
        script = Path(td) / 'run.sh'
        script.write_text(source)
        proc = None
        def stop(signum, frame):
            if proc is not None and proc.poll() is None:
                proc.kill()  # bwrap namespace init dies: kernel kills every member, including detached gateway.
            raise SystemExit(128 + signum)
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, stop)
        try:
            proc = subprocess.Popen(['/bin/bash', str(script), work, '--', *argv], start_new_session=True)
            try:
                # Terminal-Sitzung (Mensch am Server): kein Limit. Hintergrundauftrag: hartes Limit, überschreibbar.
                limit = None if os.isatty(0) else float(os.environ.get('MA_RUNNER_TIMEOUT') or 300)
                return proc.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                return 124
        finally:
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait()
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    if sys.argv[1] == '--inside':
        sys.exit(inside(sys.argv[2:]))
    assert sys.argv[2] == '--'
    sys.exit(outside(sys.argv[1], sys.argv[3:]))
