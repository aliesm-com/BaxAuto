import type { BackupRecord, BackupStorageUpload } from '@/api/resources'

export type BackupSource =
  | { kind: 'local'; label: string }
  | { kind: 'storage'; id: number; label: string; storageKind: string }

/** Local MEDIA (if present) plus successful remote uploads. */
export function backupSources(b: BackupRecord): BackupSource[] {
  const out: BackupSource[] = []
  if (b.local_available) {
    out.push({ kind: 'local', label: 'Local filesystem' })
  }
  const uploads = (b.storage_uploads ?? []).filter((u: BackupStorageUpload) => u.ok)
  for (const u of uploads) {
    out.push({
      kind: 'storage',
      id: u.id,
      label: `${u.name} (${u.kind})`,
      storageKind: u.kind,
    })
  }
  return out
}

export function downloadPathForSource(backupId: number, source: BackupSource): string {
  if (source.kind === 'local') {
    return `/api/backup-records/${backupId}/download/`
  }
  return `/api/backup-records/${backupId}/download/?storage_id=${source.id}`
}
