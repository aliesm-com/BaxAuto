"""Upload backup artifacts to saved :class:`StorageDestination` rows."""

from __future__ import annotations

from ftplib import FTP, FTP_TLS, error_perm
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import StorageDestination


class StorageTransferError(RuntimeError):
    """Raised when a backup file cannot be written to a destination."""


def upload_backup_file(dest: StorageDestination, local_path: Path, remote_relative: str) -> str:
    """
    Copy ``local_path`` to ``dest`` under ``remote_relative``.

    ``remote_relative`` is joined under ``dest.remote_path`` (e.g.
    ``my-db/manual/dump.sql.gz``). Returns the remote key/path that was written.
    """
    if dest.kind == dest.Kind.S3:
        return _upload_s3(dest, local_path, remote_relative)
    if dest.kind == dest.Kind.SFTP:
        return _upload_sftp(dest, local_path, remote_relative)
    if dest.kind == dest.Kind.FTP:
        return _upload_ftp(dest, local_path, remote_relative)
    raise StorageTransferError(f'Unsupported storage kind: {dest.kind}')


def download_backup_file(dest: StorageDestination, remote_relative: str, local_path: Path) -> Path:
    """
    Download ``remote_relative`` from ``dest`` into ``local_path``.

    Parent directories of ``local_path`` are created as needed. Returns ``local_path``.
    """
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if dest.kind == dest.Kind.S3:
        _download_s3(dest, remote_relative, local_path)
    elif dest.kind == dest.Kind.SFTP:
        _download_sftp(dest, remote_relative, local_path)
    elif dest.kind == dest.Kind.FTP:
        _download_ftp(dest, remote_relative, local_path)
    else:
        raise StorageTransferError(f'Unsupported storage kind: {dest.kind}')
    return local_path


def delete_backup_file(dest: StorageDestination, remote_relative: str) -> None:
    """Remove a previously uploaded backup at ``remote_relative`` under ``dest``."""
    if dest.kind == dest.Kind.S3:
        _delete_s3(dest, remote_relative)
        return
    if dest.kind == dest.Kind.SFTP:
        _delete_sftp(dest, remote_relative)
        return
    if dest.kind == dest.Kind.FTP:
        _delete_ftp(dest, remote_relative)
        return
    raise StorageTransferError(f'Unsupported storage kind: {dest.kind}')


def _remote_key(dest: StorageDestination, remote_relative: str) -> str:
    prefix = (dest.remote_path or '').strip().replace('\\', '/').strip('/')
    rel = (remote_relative or '').strip().replace('\\', '/').strip('/')
    if not rel:
        raise StorageTransferError('Remote relative path is empty.')
    return f'{prefix}/{rel}' if prefix else rel


def _upload_s3(dest: StorageDestination, local_path: Path, remote_relative: str) -> str:
    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as e:
        raise StorageTransferError('boto3 is not installed on the API image.') from e

    bucket = (dest.bucket or '').strip()
    key_id = (dest.username or '').strip()
    secret = dest.secret or ''
    if not bucket or not key_id or not secret:
        raise StorageTransferError('S3 bucket, access key, and secret are required.')

    endpoint = (dest.endpoint_url or '').strip() or None
    region = (dest.region or '').strip() or None
    addressing = 'path' if endpoint else 'auto'
    cfg = Config(
        connect_timeout=30,
        read_timeout=1800,
        retries={'max_attempts': 3},
        s3={'addressing_style': addressing},
    )
    kw: dict = {
        'aws_access_key_id': key_id,
        'aws_secret_access_key': secret,
        'config': cfg,
    }
    if region:
        kw['region_name'] = region
    elif endpoint:
        kw['region_name'] = 'us-east-1'
    if endpoint:
        kw['endpoint_url'] = endpoint

    key = _remote_key(dest, remote_relative)
    client = boto3.client('s3', **kw)
    try:
        client.upload_file(str(local_path), bucket, key)
    except (BotoCoreError, ClientError, OSError) as e:
        raise StorageTransferError(f'S3 upload failed: {e}') from e
    return f's3://{bucket}/{key}'


def _s3_client(dest: StorageDestination):
    try:
        import boto3
        from botocore.config import Config
    except ImportError as e:
        raise StorageTransferError('boto3 is not installed on the API image.') from e

    bucket = (dest.bucket or '').strip()
    key_id = (dest.username or '').strip()
    secret = dest.secret or ''
    if not bucket or not key_id or not secret:
        raise StorageTransferError('S3 bucket, access key, and secret are required.')

    endpoint = (dest.endpoint_url or '').strip() or None
    region = (dest.region or '').strip() or None
    addressing = 'path' if endpoint else 'auto'
    cfg = Config(
        connect_timeout=30,
        read_timeout=1800,
        retries={'max_attempts': 3},
        s3={'addressing_style': addressing},
    )
    kw: dict = {
        'aws_access_key_id': key_id,
        'aws_secret_access_key': secret,
        'config': cfg,
    }
    if region:
        kw['region_name'] = region
    elif endpoint:
        kw['region_name'] = 'us-east-1'
    if endpoint:
        kw['endpoint_url'] = endpoint
    return boto3.client('s3', **kw), bucket


def _delete_s3(dest: StorageDestination, remote_relative: str) -> None:
    try:
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as e:
        raise StorageTransferError('boto3 is not installed on the API image.') from e

    client, bucket = _s3_client(dest)
    key = _remote_key(dest, remote_relative)
    try:
        client.delete_object(Bucket=bucket, Key=key)
    except (BotoCoreError, ClientError, OSError) as e:
        raise StorageTransferError(f'S3 delete failed: {e}') from e


def _download_s3(dest: StorageDestination, remote_relative: str, local_path: Path) -> None:
    try:
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as e:
        raise StorageTransferError('boto3 is not installed on the API image.') from e

    client, bucket = _s3_client(dest)
    key = _remote_key(dest, remote_relative)
    try:
        client.download_file(bucket, key, str(local_path))
    except (BotoCoreError, ClientError, OSError) as e:
        raise StorageTransferError(f'S3 download failed: {e}') from e


def _sftp_makedirs(sftp, remote_dir: str) -> None:
    remote_dir = remote_dir.replace('\\', '/').rstrip('/')
    if not remote_dir or remote_dir == '.':
        return
    acc = ''
    absolute = remote_dir.startswith('/')
    parts = [p for p in remote_dir.split('/') if p]
    if absolute:
        acc = ''
    for part in parts:
        acc = f'{acc}/{part}' if acc or absolute else part
        if absolute and not acc.startswith('/'):
            acc = f'/{acc}'
        try:
            sftp.stat(acc)
        except OSError:
            sftp.mkdir(acc)


def _upload_sftp(dest: StorageDestination, local_path: Path, remote_relative: str) -> str:
    try:
        import paramiko
    except ImportError as e:
        raise StorageTransferError('paramiko is not installed on the API image.') from e

    host = (dest.host or '').strip()
    user = (dest.username or '').strip()
    if not host or not user:
        raise StorageTransferError('Host and username are required for SFTP.')
    remote = _remote_key(dest, remote_relative)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=int(dest.port or 22),
            username=user,
            password=dest.secret or None,
            timeout=30,
            allow_agent=False,
            look_for_keys=False,
        )
        sftp = client.open_sftp()
        try:
            parent = remote.rsplit('/', 1)[0] if '/' in remote else ''
            if parent:
                _sftp_makedirs(sftp, parent)
            sftp.put(str(local_path), remote)
        finally:
            sftp.close()
    except Exception as e:
        raise StorageTransferError(f'SFTP upload failed: {e}') from e
    finally:
        client.close()
    return remote


def _delete_sftp(dest: StorageDestination, remote_relative: str) -> None:
    try:
        import paramiko
    except ImportError as e:
        raise StorageTransferError('paramiko is not installed on the API image.') from e

    host = (dest.host or '').strip()
    user = (dest.username or '').strip()
    if not host or not user:
        raise StorageTransferError('Host and username are required for SFTP.')
    remote = _remote_key(dest, remote_relative)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=int(dest.port or 22),
            username=user,
            password=dest.secret or None,
            timeout=30,
            allow_agent=False,
            look_for_keys=False,
        )
        sftp = client.open_sftp()
        try:
            sftp.remove(remote)
        finally:
            sftp.close()
    except Exception as e:
        raise StorageTransferError(f'SFTP delete failed: {e}') from e
    finally:
        client.close()


def _download_sftp(dest: StorageDestination, remote_relative: str, local_path: Path) -> None:
    try:
        import paramiko
    except ImportError as e:
        raise StorageTransferError('paramiko is not installed on the API image.') from e

    host = (dest.host or '').strip()
    user = (dest.username or '').strip()
    if not host or not user:
        raise StorageTransferError('Host and username are required for SFTP.')
    remote = _remote_key(dest, remote_relative)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=int(dest.port or 22),
            username=user,
            password=dest.secret or None,
            timeout=60,
            allow_agent=False,
            look_for_keys=False,
        )
        sftp = client.open_sftp()
        try:
            sftp.get(remote, str(local_path))
        finally:
            sftp.close()
    except Exception as e:
        raise StorageTransferError(f'SFTP download failed: {e}') from e
    finally:
        client.close()


def _ftp_makedirs(ftp: FTP, remote_dir: str) -> None:
    remote_dir = remote_dir.replace('\\', '/').strip('/')
    if not remote_dir:
        return
    acc = ''
    for part in remote_dir.split('/'):
        acc = f'{acc}/{part}' if acc else part
        try:
            ftp.mkd(acc)
        except error_perm:
            pass


def _upload_ftp(dest: StorageDestination, local_path: Path, remote_relative: str) -> str:
    host = (dest.host or '').strip()
    user = (dest.username or '').strip()
    if not host or not user:
        raise StorageTransferError('Host and username are required for FTP.')
    remote = _remote_key(dest, remote_relative)
    timeout = 1800
    ftp: FTP
    try:
        if dest.ftp_use_tls:
            ftp = FTP_TLS()
            ftp.connect(host, int(dest.port or 21), timeout=timeout)
            ftp.login(user, dest.secret or '')
            ftp.prot_p()
        else:
            ftp = FTP()
            ftp.connect(host, int(dest.port or 21), timeout=timeout)
            ftp.login(user, dest.secret or '')
        if dest.ftp_passive:
            ftp.set_pasv(True)
        parent = remote.rsplit('/', 1)[0] if '/' in remote else ''
        name = remote.rsplit('/', 1)[-1]
        if parent:
            _ftp_makedirs(ftp, parent)
            try:
                ftp.cwd(parent)
            except error_perm:
                pass
        with local_path.open('rb') as fh:
            ftp.storbinary(f'STOR {name}', fh)
        ftp.quit()
    except Exception as e:
        raise StorageTransferError(f'FTP upload failed: {e}') from e
    return remote


def _delete_ftp(dest: StorageDestination, remote_relative: str) -> None:
    host = (dest.host or '').strip()
    user = (dest.username or '').strip()
    if not host or not user:
        raise StorageTransferError('Host and username are required for FTP.')
    remote = _remote_key(dest, remote_relative)
    timeout = 120
    ftp: FTP
    try:
        if dest.ftp_use_tls:
            ftp = FTP_TLS()
            ftp.connect(host, int(dest.port or 21), timeout=timeout)
            ftp.login(user, dest.secret or '')
            ftp.prot_p()
        else:
            ftp = FTP()
            ftp.connect(host, int(dest.port or 21), timeout=timeout)
            ftp.login(user, dest.secret or '')
        if dest.ftp_passive:
            ftp.set_pasv(True)
        ftp.delete(remote)
        ftp.quit()
    except Exception as e:
        raise StorageTransferError(f'FTP delete failed: {e}') from e


def _download_ftp(dest: StorageDestination, remote_relative: str, local_path: Path) -> None:
    host = (dest.host or '').strip()
    user = (dest.username or '').strip()
    if not host or not user:
        raise StorageTransferError('Host and username are required for FTP.')
    remote = _remote_key(dest, remote_relative)
    timeout = 1800
    ftp: FTP
    try:
        if dest.ftp_use_tls:
            ftp = FTP_TLS()
            ftp.connect(host, int(dest.port or 21), timeout=timeout)
            ftp.login(user, dest.secret or '')
            ftp.prot_p()
        else:
            ftp = FTP()
            ftp.connect(host, int(dest.port or 21), timeout=timeout)
            ftp.login(user, dest.secret or '')
        if dest.ftp_passive:
            ftp.set_pasv(True)
        with local_path.open('wb') as fh:
            ftp.retrbinary(f'RETR {remote}', fh.write)
        ftp.quit()
    except Exception as e:
        raise StorageTransferError(f'FTP download failed: {e}') from e
