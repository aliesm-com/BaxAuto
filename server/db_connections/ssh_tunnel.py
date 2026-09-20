"""On-demand SSH local port forwards for DatabaseConnection access."""

from __future__ import annotations

import base64
import hashlib
import select
import socket
import threading
from contextlib import contextmanager
from io import StringIO
from typing import Iterator

from dbs.base import BackupRestoreError

# Native / primary DB ports (remote side of the tunnel).
DEFAULT_ENGINE_PORTS: dict[str, int] = {
    'postgresql': 5432,
    'mysql': 3306,
    'mariadb': 3306,
    'redis': 6379,
    'mongodb': 27017,
    'rabbitmq': 5672,
    'sqlserver': 1433,
    'clickhouse': 9000,
}

# Secondary ports some engines also need (HTTP / management).
EXTRA_ENGINE_PORTS: dict[str, tuple[str, int]] = {
    'clickhouse': ('http_port', 8123),
    'rabbitmq': ('management_port', 15672),
}


def normalize_fingerprint(value: str) -> str:
    raw = (value or '').strip().replace(' ', '')
    if not raw:
        return ''
    if raw.upper().startswith('SHA256:'):
        return 'SHA256:' + raw.split(':', 1)[1]
    return f'SHA256:{raw}'


def openssh_sha256_fingerprint(key) -> str:
    """Match ``ssh-keygen -lf`` SHA256 fingerprints (unpadded base64)."""
    digest = hashlib.sha256(key.asbytes()).digest()
    return 'SHA256:' + base64.b64encode(digest).decode('ascii').rstrip('=')


def fingerprints_match(expected: str, actual: str) -> bool:
    return normalize_fingerprint(expected) == normalize_fingerprint(actual)


def load_private_key(pem: str, passphrase: str = ''):
    import paramiko

    raw = (pem or '').strip()
    if not raw:
        raise BackupRestoreError('SSH private key is empty.')
    buf = StringIO(raw)
    pwd = passphrase or None
    errors: list[str] = []
    for key_cls in (
        paramiko.Ed25519Key,
        paramiko.ECDSAKey,
        paramiko.RSAKey,
    ):
        buf.seek(0)
        try:
            return key_cls.from_private_key(buf, password=pwd)
        except Exception as e:  # noqa: BLE001 — try next key type
            errors.append(f'{key_cls.__name__}: {e}')
    raise BackupRestoreError(
        'Could not parse SSH private key (supported: Ed25519, ECDSA, RSA). '
        + '; '.join(errors[:2])
    )


def _handler(chan, sock: socket.socket) -> None:
    try:
        while True:
            r, _w, _x = select.select([sock, chan], [], [], 60)
            if sock in r:
                data = sock.recv(65536)
                if not data:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(65536)
                if not data:
                    break
                sock.send(data)
    except OSError:
        pass
    finally:
        try:
            chan.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            sock.close()
        except Exception:  # noqa: BLE001
            pass


class LocalPortForwarder:
    """Listen on 127.0.0.1:0 and forward via an open Paramiko transport."""

    def __init__(self, transport, remote_host: str, remote_port: int):
        self.transport = transport
        self.remote_host = remote_host
        self.remote_port = int(remote_port)
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.local_port = 0

    def start(self) -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', 0))
        sock.listen(64)
        sock.settimeout(1.0)
        self._sock = sock
        self.local_port = sock.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, name='ssh-fwd', daemon=True)
        self._thread.start()
        return self.local_port

    def _serve(self) -> None:
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                client_sock, _addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                chan = self.transport.open_channel(
                    'direct-tcpip',
                    (self.remote_host, self.remote_port),
                    client_sock.getpeername(),
                )
            except Exception:  # noqa: BLE001
                client_sock.close()
                continue
            if chan is None:
                client_sock.close()
                continue
            t = threading.Thread(target=_handler, args=(chan, client_sock), daemon=True)
            t.start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None


def connect_ssh_client(
    *,
    ssh_host: str,
    ssh_port: int,
    ssh_username: str,
    ssh_password: str = '',
    ssh_private_key: str = '',
    ssh_private_key_passphrase: str = '',
    host_key_fingerprint: str,
):
    import paramiko

    class FingerprintPolicy(paramiko.MissingHostKeyPolicy):
        def __init__(self, expected: str):
            self.expected = normalize_fingerprint(expected)

        def missing_host_key(self, client, hostname, key):  # noqa: ANN001
            actual = openssh_sha256_fingerprint(key)
            if not fingerprints_match(self.expected, actual):
                raise BackupRestoreError(
                    f'SSH host key mismatch for {hostname}: got {actual}, '
                    f'expected {self.expected}. '
                    'Verify with: ssh-keyscan -t ed25519,rsa HOST | ssh-keygen -lf -'
                )
            client.get_host_keys().add(hostname, key.get_name(), key)

    host = (ssh_host or '').strip()
    user = (ssh_username or '').strip()
    fp = normalize_fingerprint(host_key_fingerprint)
    if not host or not user:
        raise BackupRestoreError('SSH host and username are required when the tunnel is enabled.')
    if not fp:
        raise BackupRestoreError(
            'SSH host key fingerprint is required (SHA256:…). '
            'Get it with: ssh-keyscan -t ed25519,rsa HOST | ssh-keygen -lf -'
        )

    pkey = None
    pem = (ssh_private_key or '').strip()
    if pem:
        pkey = load_private_key(pem, ssh_private_key_passphrase or '')
    password = (ssh_password or '') or None
    if pkey is None and not password:
        raise BackupRestoreError('Provide an SSH private key or SSH password for the tunnel.')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(FingerprintPolicy(fp))
    try:
        client.connect(
            hostname=host,
            port=int(ssh_port or 22),
            username=user,
            password=password,
            pkey=pkey,
            timeout=20,
            allow_agent=False,
            look_for_keys=False,
            banner_timeout=20,
            auth_timeout=20,
        )
    except BackupRestoreError:
        client.close()
        raise
    except Exception as e:
        client.close()
        raise BackupRestoreError(f'SSH tunnel connect failed: {e}') from e
    return client


@contextmanager
def ssh_local_forwards(
    *,
    ssh_host: str,
    ssh_port: int,
    ssh_username: str,
    ssh_password: str = '',
    ssh_private_key: str = '',
    ssh_private_key_passphrase: str = '',
    host_key_fingerprint: str,
    remotes: list[tuple[str, int]],
) -> Iterator[list[int]]:
    """
    Open SSH and forward each ``(remote_host, remote_port)`` to a local ephemeral port.

    Yields a list of local ports in the same order as ``remotes``.
    """
    if not remotes:
        raise BackupRestoreError('SSH tunnel requires at least one remote port to forward.')

    client = connect_ssh_client(
        ssh_host=ssh_host,
        ssh_port=ssh_port,
        ssh_username=ssh_username,
        ssh_password=ssh_password,
        ssh_private_key=ssh_private_key,
        ssh_private_key_passphrase=ssh_private_key_passphrase,
        host_key_fingerprint=host_key_fingerprint,
    )
    transport = client.get_transport()
    if transport is None:
        client.close()
        raise BackupRestoreError('SSH transport is not available.')

    forwarders: list[LocalPortForwarder] = []
    try:
        local_ports: list[int] = []
        for remote_host, remote_port in remotes:
            fwd = LocalPortForwarder(transport, remote_host, remote_port)
            local_ports.append(fwd.start())
            forwarders.append(fwd)
        yield local_ports
    finally:
        for fwd in forwarders:
            fwd.stop()
        client.close()


def default_remote_db_port(engine: str, port: int | None) -> int:
    if port:
        return int(port)
    return int(DEFAULT_ENGINE_PORTS.get(engine, 5432))
