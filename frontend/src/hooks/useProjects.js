import { useState, useEffect, useCallback } from 'react';
import { listProjects } from '../api/projects.js';

/**
 * Fetches and manages the project list.
 *
 * @returns {{ projects, loading, error, reload }}
 *
 * projects — ProjectRead[] (newest first) or empty array
 * loading  — boolean
 * error    — Error | null
 * reload   — function to re-fetch
 */
export default function useProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await listProjects();
      setProjects(response.data);
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Failed to load projects';
      const wrapped = new Error(message);
      wrapped.status = err.response?.status ?? null;
      setError(wrapped);
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { projects, loading, error, reload: fetch };
}
