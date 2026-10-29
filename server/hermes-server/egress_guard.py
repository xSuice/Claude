"""Strict CONNECT destination policy for sandbox provider egress."""
import ipaddress


def public_addresses(ips):
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError('non-public DNS result')
    return list(dict.fromkeys(ips))


import socket
import socketserver
import select
import threading


def relay(a, b):
    while True:
        ready, _, _ = select.select([a, b], [], [], 90)
        if not ready:
            return
        for source in ready:
            data = source.recv(65536)
            if not data:
                return
            (b if source is a else a).sendall(data)


class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        client = self.request
        client.settimeout(15)
        connected = False
        try:
            header = b''
            while not header.endswith(b'\r\n\r\n'):
                chunk = client.recv(1)
                if not chunk or len(header) >= 8192:
                    raise ValueError('invalid header')
                header += chunk
            host = authority(header.split(b'\r\n', 1)[0].decode('ascii'))
            addresses = public_addresses([r[4][0] for r in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)])
            # Connect to the validated numeric address: do not resolve hostname again.
            with socket.create_connection((addresses[0], 443), timeout=15) as upstream:
                client.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
                connected = True
                client.settimeout(90)
                upstream.settimeout(90)
                relay(client, upstream)
        except (OSError, ValueError, UnicodeError):
            if not connected:
                try:
                    client.sendall(b'HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
                except OSError:
                    pass


def start_proxy(path):
    class Server(socketserver.ThreadingUnixStreamServer):
        daemon_threads = True
    server = Server(path, ProxyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


ALLOWED = frozenset(('dialagram.me', 'api.kimi.ai'))

def authority(line):
    parts = line.split(' ')
    if len(parts) != 3 or parts[0] != 'CONNECT' or parts[2] not in ('HTTP/1.0', 'HTTP/1.1'):
        raise ValueError('CONNECT only')
    target = parts[1]
    if target not in {host + ':443' for host in ALLOWED}:
        raise ValueError('destination denied')
    return target[:-4]
