import { apiFetch, apiJson } from '@/api/client'

export type StorageKind = 's3' | 'sftp' | 'ftp'

export const STORAGE_KINDS: { value: StorageKind; label: string }[] = [
  { value: 's3', label: 'S3 / compatible (AWS, MinIO, …)' },
  { value: 'sftp', label: 'SFTP' },
  { value: 'ftp', label: 'FTP' },
]

export interface StorageDestinationDTO {
  id: number
  user: number
  name: string
  kind: StorageKind
  host: string
  port: number | null
  username: string
  bucket: string
  region: string
  endpoint_url: string
  remote_path: string
  ftp_passive: boolean
  ftp_use_tls: boolean
  created_at?: string
  updated_at?: string
}

export interface StorageDestinationWritePayload {
  name: string
  kind: StorageKind
  host?: string
  port?: number | null
  username?: string
  secret?: string
  bucket?: string
  region?: string
  endpoint_url?: string
  remote_path?: string
  ftp_passive?: boolean
  ftp_use_tls?: boolean
}

export async function listStorageDestinations(): Promise<StorageDestinationDTO[]> {
  return apiJson<StorageDestinationDTO[]>('/api/storage-destinations/')
}

export async function getStorageDestination(id: number): Promise<StorageDestinationDTO> {
  return apiJson<StorageDestinationDTO>(`/api/storage-destinations/${id}/`)
}

export async function createStorageDestination(body: StorageDestinationWritePayload): Promise<StorageDestinationDTO> {
  return apiJson<StorageDestinationDTO>('/api/storage-destinations/', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateStorageDestination(
  id: number,
  body: Partial<StorageDestinationWritePayload>,
): Promise<StorageDestinationDTO> {
  return apiJson<StorageDestinationDTO>(`/api/storage-destinations/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function deleteStorageDestination(id: number): Promise<void> {
  const res = await apiFetch(`/api/storage-destinations/${id}/`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
}

export async function testStorageDestination(id: number): Promise<{ ok: boolean; detail?: string }> {
  return apiJson<{ ok: boolean; detail?: string }>(`/api/storage-destinations/${id}/test/`, { method: 'POST' })
}
