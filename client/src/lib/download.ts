import { apiFetch } from '@/api/client'

export async function downloadAuthenticated(path: string, filename: string): Promise<void> {
  const res = await apiFetch(path)
  if (!res.ok) {
    throw new Error(await res.text())
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
