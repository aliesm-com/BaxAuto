import { type FormEvent, useEffect, useState } from 'react'

import { getAppSettings, patchAppSettings } from '@/api/appSettingsApi'
import { changePassword, patchProfile } from '@/api/profileApi'
import { useAuth } from '@/auth/AuthContext'
import { canManageUsers } from '@/auth/access'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'

export function SettingsPage() {
  const { user, refreshUser } = useAuth()
  const isAdmin = canManageUsers(user)

  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [phone, setPhone] = useState('')
  const [countryCode, setCountryCode] = useState('')
  const [profileMsg, setProfileMsg] = useState<string | null>(null)
  const [profileSaving, setProfileSaving] = useState(false)

  const [oldPass, setOldPass] = useState('')
  const [newPass, setNewPass] = useState('')
  const [newPass2, setNewPass2] = useState('')
  const [passMsg, setPassMsg] = useState<string | null>(null)
  const [passSaving, setPassSaving] = useState(false)

  const [keepLocal, setKeepLocal] = useState(true)
  const [keepLocalLoaded, setKeepLocalLoaded] = useState(false)
  const [storageMsg, setStorageMsg] = useState<string | null>(null)
  const [storageSaving, setStorageSaving] = useState(false)

  useEffect(() => {
    if (!user) return
    setEmail(user.email ?? '')
    setFirstName(user.first_name ?? '')
    setLastName(user.last_name ?? '')
    setPhone(user.phone_number ?? '')
    setCountryCode(user.country_code ?? '')
  }, [user])

  useEffect(() => {
    getAppSettings()
      .then((s) => {
        setKeepLocal(s.keep_local_backups)
        setKeepLocalLoaded(true)
      })
      .catch((err) => {
        setStorageMsg(err instanceof Error ? err.message : 'Failed to load storage settings')
      })
  }, [])

  async function onProfileSubmit(e: FormEvent) {
    e.preventDefault()
    setProfileMsg(null)
    setProfileSaving(true)
    try {
      await patchProfile({
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        phone_number: phone.trim() || null,
        country_code: countryCode.trim() || null,
      })
      await refreshUser()
      setProfileMsg('Profile saved.')
    } catch (err) {
      setProfileMsg(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setProfileSaving(false)
    }
  }

  async function onPasswordSubmit(e: FormEvent) {
    e.preventDefault()
    setPassMsg(null)
    if (newPass.length < 8) {
      setPassMsg('New password must be at least 8 characters.')
      return
    }
    if (newPass !== newPass2) {
      setPassMsg('New passwords do not match.')
      return
    }
    setPassSaving(true)
    try {
      await changePassword(oldPass, newPass)
      setOldPass('')
      setNewPass('')
      setNewPass2('')
      setPassMsg('Password updated.')
    } catch (err) {
      setPassMsg(err instanceof Error ? err.message : 'Change failed')
    } finally {
      setPassSaving(false)
    }
  }

  async function onStorageSubmit(e: FormEvent) {
    e.preventDefault()
    if (!isAdmin) return
    setStorageMsg(null)
    setStorageSaving(true)
    try {
      const s = await patchAppSettings({ keep_local_backups: keepLocal })
      setKeepLocal(s.keep_local_backups)
      setStorageMsg('Storage settings saved.')
    } catch (err) {
      setStorageMsg(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setStorageSaving(false)
    }
  }

  if (!user) {
    return (
      <div className="p-6 lg:p-8">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl space-y-8 p-6 lg:p-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Signed in as {user.username}
          <span className="mt-1 block font-mono text-xs text-muted-foreground">Your user ID: {user.id}</span>
          <span className="mt-0.5 block text-xs text-muted-foreground">
            Share database connections with teammates using this ID (owners only).
          </span>
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>Updates apply to your account only.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onProfileSubmit} className="space-y-4">
            {profileMsg ? (
              <p className={`text-sm ${profileMsg.includes('failed') || profileMsg.includes('Error') ? 'text-red-600' : 'text-emerald-700 dark:text-emerald-400'}`}>
                {profileMsg}
              </p>
            ) : null}
            <div className="space-y-2">
              <Label htmlFor="set-email">Email</Label>
              <Input id="set-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="set-fn">First name</Label>
                <Input id="set-fn" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="set-ln">Last name</Label>
                <Input id="set-ln" value={lastName} onChange={(e) => setLastName(e.target.value)} />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="set-phone">Phone</Label>
                <Input id="set-phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="set-cc">Country code</Label>
                <Input id="set-cc" value={countryCode} onChange={(e) => setCountryCode(e.target.value)} placeholder="+98" />
              </div>
            </div>
            <Button type="submit" disabled={profileSaving}>
              {profileSaving ? 'Saving…' : 'Save profile'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Password</CardTitle>
          <CardDescription>You will stay logged in after changing your password.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onPasswordSubmit} className="space-y-4">
            {passMsg ? (
              <p className={`text-sm ${passMsg.includes('failed') || passMsg.includes('match') || passMsg.includes('characters') ? 'text-red-600' : 'text-emerald-700 dark:text-emerald-400'}`}>
                {passMsg}
              </p>
            ) : null}
            <div className="space-y-2">
              <Label htmlFor="set-old">Current password</Label>
              <Input id="set-old" type="password" value={oldPass} onChange={(e) => setOldPass(e.target.value)} autoComplete="current-password" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="set-new">New password</Label>
              <Input id="set-new" type="password" value={newPass} onChange={(e) => setNewPass(e.target.value)} autoComplete="new-password" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="set-new2">Confirm new password</Label>
              <Input id="set-new2" type="password" value={newPass2} onChange={(e) => setNewPass2(e.target.value)} autoComplete="new-password" />
            </div>
            <Button type="submit" disabled={passSaving}>
              {passSaving ? 'Updating…' : 'Change password'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Backup storage</CardTitle>
          <CardDescription>
            When remote destinations (S3/SFTP/FTP) receive a successful upload, you can drop the copy on this server to
            save disk. Download and restore then pick a remote source (or local if still present).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onStorageSubmit} className="space-y-4">
            {storageMsg ? (
              <p
                className={`text-sm ${
                  storageMsg.toLowerCase().includes('fail') ||
                  storageMsg.toLowerCase().includes('error') ||
                  storageMsg.toLowerCase().includes('required')
                    ? 'text-red-600'
                    : 'text-emerald-700 dark:text-emerald-400'
                }`}
              >
                {storageMsg}
              </p>
            ) : null}
            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-0.5 size-4 rounded"
                checked={keepLocal}
                disabled={!keepLocalLoaded || !isAdmin}
                onChange={(e) => setKeepLocal(e.target.checked)}
              />
              <span>
                <span className="font-medium">Keep local backups on this server</span>
                <span className="mt-0.5 block text-muted-foreground">
                  Uncheck to delete the local file after at least one remote upload succeeds. If no remote upload
                  succeeds, the local copy is always kept.
                </span>
              </span>
            </label>
            {isAdmin ? (
              <Button type="submit" disabled={storageSaving || !keepLocalLoaded}>
                {storageSaving ? 'Saving…' : 'Save storage settings'}
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground">Only admins can change this setting.</p>
            )}
          </form>
        </CardContent>
      </Card>

      <Separator />
      <p className="text-xs text-muted-foreground">
        Role changes (admin, staff, etc.) are handled under Users if you have permission.
      </p>
    </div>
  )
}
