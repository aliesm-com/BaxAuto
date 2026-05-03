import { Navigate, Route, Routes, useParams } from 'react-router-dom'

import { ProtectedRoute } from '@/auth/ProtectedRoute'
import { AppShell } from '@/components/layout/AppShell'
import { BackupRecordsPage } from '@/pages/BackupRecordsPage'
import { ConnectionDetailPage } from '@/pages/ConnectionDetailPage'
import { ConnectionsPage } from '@/pages/ConnectionsPage'
import { ActivityLogsPage } from '@/pages/ActivityLogsPage'
import { AlertsPage } from '@/pages/AlertsPage'
import { LoginPage } from '@/pages/LoginPage'
import { OverviewPage } from '@/pages/OverviewPage'
import { RestorePage } from '@/pages/RestorePage'
import { ScheduleDetailPage } from '@/pages/ScheduleDetailPage'
import { SchedulesPage } from '@/pages/SchedulesPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { StoragePage } from '@/pages/StoragePage'
import { UsersPage } from '@/pages/UsersPage'

function RedirectDatabaseNew() {
  return <Navigate to="/databases?new=1" replace />
}

function RedirectDatabaseEdit() {
  const { id } = useParams<{ id: string }>()
  return id ? <Navigate to={`/databases?edit=${id}`} replace /> : <Navigate to="/databases" replace />
}

function RedirectScheduleNew() {
  return <Navigate to="/schedules?new=1" replace />
}

function RedirectScheduleEdit() {
  const { id } = useParams<{ id: string }>()
  return id ? <Navigate to={`/schedules?edit=${id}`} replace /> : <Navigate to="/schedules" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<OverviewPage />} />
        <Route path="backups" element={<BackupRecordsPage />} />
        <Route path="databases/new" element={<RedirectDatabaseNew />} />
        <Route path="databases/:id/edit" element={<RedirectDatabaseEdit />} />
        <Route path="databases/:id" element={<ConnectionDetailPage />} />
        <Route path="databases" element={<ConnectionsPage />} />
        <Route path="schedules/new" element={<RedirectScheduleNew />} />
        <Route path="schedules/:id/edit" element={<RedirectScheduleEdit />} />
        <Route path="schedules/:id" element={<ScheduleDetailPage />} />
        <Route path="schedules" element={<SchedulesPage />} />
        <Route path="storage" element={<StoragePage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="logs" element={<ActivityLogsPage />} />
        <Route path="restore" element={<RestorePage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
