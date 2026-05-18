import { useState, useEffect, useCallback } from 'react';
import { getProject } from '../api/projects.js';

/**
 * Fetches and manages a single project by ID.
 *
 * @param {string|undefined} projectId — from useParams()
 * @returns {{ project, loading, error, reload }}
 *
 * project shape (mirrors ProjectRead API contract):
 * {
 *   id: string,
 *   name: string,
 *   company: string,
 *   description: string,
 *   existing_infra: string,
 *   budget_ceiling: number | null,
 *   created_at: string,   // ISO date
 *   updated_at: string,
 * }
 */
export default function useProject(projectId) {
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await getProject(projectId);
      setProject(response.data);
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Failed to load project';
      const wrapped = new Error(message);
      wrapped.status = err.response?.status ?? null;
      setError(wrapped);
      setProject(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { project, loading, error, reload: fetch };
}
