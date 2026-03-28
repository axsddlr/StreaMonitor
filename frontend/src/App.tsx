import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Dashboard } from '@/pages/Dashboard'
import { Recordings } from '@/pages/Recordings'
import { Login } from '@/pages/Login'

function ProtectedRoute({
  auth,
  children,
}: {
  auth: ReturnType<typeof useAuth>
  children: React.ReactNode
}) {
  if (!auth.isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function App() {
  const auth = useAuth()

  return (
    <Routes>
      <Route path="/login" element={<Login auth={auth} />} />
      <Route
        path="/"
        element={
          <ProtectedRoute auth={auth}>
            <Dashboard token={auth.token} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/recordings/:username/:site"
        element={
          <ProtectedRoute auth={auth}>
            <Recordings />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
