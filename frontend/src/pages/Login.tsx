import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, Eye, EyeOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { UseAuthReturn } from '@/hooks/useAuth'

interface LoginProps {
  auth: UseAuthReturn
}

export function Login({ auth }: LoginProps) {
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // If already authenticated, redirect to dashboard
  useEffect(() => {
    if (auth.isAuthenticated) {
      void navigate('/', { replace: true })
    }
  }, [auth.isAuthenticated, navigate])

  // Try auto-login with empty password on mount (no-auth mode)
  useEffect(() => {
    let cancelled = false

    async function tryAutoLogin() {
      try {
        await auth.login('')
        if (!cancelled) {
          void navigate('/', { replace: true })
        }
      } catch {
        // Password is required — show the login form
      }
    }

    void tryAutoLogin()

    return () => {
      cancelled = true
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      await auth.login(password)
      void navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        <div className="rounded-lg border border-border bg-card p-6 shadow-lg">
          <div className="mb-6 text-center">
            <h1 className="text-xl font-semibold text-foreground">StreaMonitor</h1>
            <p className="mt-1 text-sm text-muted-foreground">Sign in to continue</p>
          </div>

          <form onSubmit={(e) => void handleSubmit(e)}>
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="password" className="text-sm font-medium text-foreground">
                  Password
                </label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value)
                      setError(null)
                    }}
                    autoFocus
                    autoComplete="current-password"
                    className="pr-10"
                    aria-describedby={error ? 'login-error' : undefined}
                    aria-invalid={error !== null}
                  />
                  <button
                    type="button"
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                {error && (
                  <p id="login-error" className="text-xs text-destructive-foreground bg-destructive/20 px-2 py-1 rounded" role="alert">
                    {error}
                  </p>
                )}
              </div>

              <Button type="submit" disabled={isLoading} className="w-full">
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
