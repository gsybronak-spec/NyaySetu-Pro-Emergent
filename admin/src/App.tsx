import { Routes, Route, Navigate } from 'react-router-dom'
import Users from './pages/Users'
import AuditLogs from './pages/AuditLogs'
import Cases from './pages/Cases'
import { AuthProvider, useAdminAuth } from './lib/auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import AdminLayout from './layouts/AdminLayout'
import Templates from './pages/Templates'
import TemplateEditor from './pages/TemplateEditor'
import CaseFormBuilder from './pages/CaseFormBuilder'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { admin, ready } = useAdminAuth();
  if (!ready) return <div className="loading-screen">Loading...</div>;
  if (!admin) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function LoginGuard({ children }: { children: React.ReactNode }) {
  const { admin, ready } = useAdminAuth();
  if (!ready) return <div className="loading-screen">Loading...</div>;
  if (admin) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginGuard><Login /></LoginGuard>} />
        <Route path="/" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="templates" element={<Templates />} />
          <Route path="templates/new" element={<TemplateEditor />} />
          <Route path="templates/:id/edit" element={<TemplateEditor />} />
          <Route path="case-forms" element={<CaseFormBuilder />} />
          <Route path="users" element={<Users />} />
          <Route path="cases" element={<Cases />} />
          <Route path="audit-logs" element={<AuditLogs />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
