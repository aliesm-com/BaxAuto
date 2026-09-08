"""Reachability probes for saved :class:`StorageDestination` rows."""

from __future__ import annotations

from ftplib import FTP, FTP_TLS, error_perm
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import StorageDestination


class StorageProbeError(RuntimeError):
    """Raised when a storage destination cannot be reached or authenticated."""


def test_destination(dest: StorageDestination) -> None:
    kind = dest.kind
    if kind == dest.Kind.S3:
        _test_s3(dest)
    elif kind == dest.Kind.SFTP:
        _test_sftp(dest)
    elif kind == dest.Kind.FTP:
        _test_ftp(dest)
    else:
        raise StorageProbeError(f'Unsupported storage kind: {kind}')


def _test_s3(dest: StorageDestination) -> None:
    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as e:
        raise StorageProbeError('boto3 is not installed on the API image; rebuild after pip install.') from e

    bucket = (dest.bucket or '').strip()
    if not bucket:
        raise StorageProbeError('Bucket is required for S3.')
    key_id = (dest.username or '').strip()
    secret = dest.secret or ''
    if not key_id or not secret:
        raise StorageProbeError('Access key ID and secret key are required for S3.')

    endpoint = (dest.endpoint_url or '').strip() or None
    region = (dest.region or '').strip() or None
    addressing = 'path' if endpoint else 'auto'
    cfg = Config(
        connect_timeout=12,
        read_timeout=20,
        retries={'max_attempts': 2},
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

    client = boto3.client('s3', **kw)
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as e:
        resp = e.response or {}
        http = int((resp.get('ResponseMetadata') or {}).get('HTTPStatusCode') or 0)
        code = str((resp.get('Error') or {}).get('Code', ''))
        if http == 403 or code in {'403', 'AccessDenied', 'Forbidden'}:
            try:
                client.list_objects_v2(Bucket=bucket, MaxKeys=1)
                return
            except Exception as inner:
                raise StorageProbeError(f'S3 access denied for bucket "{bucket}": {inner}') from inner
        raise StorageProbeError(f'S3 probe failed: {e}') from e
    except BotoCoreError as e:
        raise StorageProbeError(f'S3 probe failed: {e}') from e


def _test_sftp(dest: StorageDestination) -> None:
    try:
        import paramiko
    except ImportError as e:
        raise StorageProbeError('paramiko is not installed on the API image; rebuild after pip install.') from e

    host = (dest.host or '').strip()
    user = (dest.username or '').strip()
    if not host or not user:
        raise StorageProbeError('Host and username are required for SFTP.')
    port = int(dest.port or 22)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=port,
            username=user,
            password=dest.secret or None,
            timeout=12,
            allow_agent=False,
            look_for_keys=False,
        )
        sftp = client.open_sftp()
        try:
            sftp.listdir((dest.remote_path or '').strip() or '.')
        finally:
            sftp.close()
    except Exception as e:
        raise StorageProbeError(f'SFTP probe failed: {e}') from e
    finally:
        client.close()


def _test_ftp(dest: StorageDestination) -> None:
    host = (dest.host or '').strip()
    user = (dest.username or '').strip()
    if not host or not user:
        raise StorageProbeError('Host and username are required for FTP.')
    port = int(dest.port or 21)
    timeout = 12
    ftp: FTP
    try:
        if dest.ftp_use_tls:
            ftp = FTP_TLS()
            ftp.connect(host, port, timeout=timeout)
            ftp.login(user, dest.secret or '')
            ftp.prot_p()
        else:
            ftp = FTP()
            ftp.connect(host, port, timeout=timeout)
            ftp.login(user, dest.secret or '')
        if dest.ftp_passive:
            ftp.set_pasv(True)
        path = (dest.remote_path or '').strip()
        if path:
            ftp.cwd(path)
        ftp.nlst()
        ftp.quit()
    except error_perm as e:
        raise StorageProbeError(f'FTP probe failed: {e}') from e
    except OSError as e:
        raise StorageProbeError(f'FTP probe failed: {e}') from e
