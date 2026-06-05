import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';

const MIN_PASSWORD_LENGTH = 12;

/**
 * Registration page. Mirrors the backend Argon2id password policy.
 */
export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    setSubmitting(true);
    try {
      await register({ email, password });
      navigate('/', { replace: true });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Registration failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-bg text-text">
      <div className="w-full max-w-sm space-y-4 rounded border border-border bg-surface p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Create your NetPlanner account</h1>
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
              autoComplete="new-password"
              maxLength={128}
              minLength={MIN_PASSWORD_LENGTH}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded border border-border bg-bg p-2 text-text"
            />
            <span className="mt-1 block text-xs text-text-muted">
              At least {MIN_PASSWORD_LENGTH} characters.
            </span>
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
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>
        <p className="text-sm text-text-muted">
          Already have an account?{' '}
          <Link to="/login" className="text-amber-700 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
