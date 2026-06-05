import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';

/**
 * Login page. Submits to /auth/login, which sets the httpOnly session cookie.
 * On success we return to wherever the user was originally headed.
 */
export default function Login() {
  const { user, login } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const from = location.state?.from?.pathname || '/';

  if (user) return <Navigate to={from} replace />;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      navigate(from, { replace: true });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Login failed. Check your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-bg text-text">
      <div className="w-full max-w-sm space-y-4 rounded border border-border bg-surface p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Sign in to NetPlanner</h1>
        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block text-sm">
            <span className="mb-1 block text-text-muted">Email</span>
            <input
              type="email"
              required
              value={email}
              autoComplete="email"
              maxLength={254}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded border border-border bg-bg p-2 text-text"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-text-muted">Password</span>
            <input
              type="password"
              required
              value={password}
              autoComplete="current-password"
              maxLength={128}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded border border-border bg-bg p-2 text-text"
            />
          </label>
          {error ? (
            <div className="rounded border border-red-300 bg-red-50 p-2 text-sm text-red-700">
              {error}
            </div>
          ) : null}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded bg-amber-500 px-3 py-2 font-medium text-white disabled:opacity-60"
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="text-sm text-text-muted">
          No account yet?{' '}
          <Link to="/register" className="text-amber-700 hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
