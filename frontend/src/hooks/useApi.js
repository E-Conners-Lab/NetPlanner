import { useState, useCallback } from 'react';
import client from '../api/client.js';

/**
 * Thin wrapper around the Axios client that tracks loading / error state.
 *
 * Usage:
 *   const { data, error, loading, execute } = useApi();
 *   await execute(() => client.get('/projects'));
 *
 * Returns:
 *   data    — the response payload (null until the call succeeds)
 *   error   — Error object or null
 *   loading — boolean
 *   execute — call this with a function that returns an Axios promise
 */
export default function useApi() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const execute = useCallback(async (requestFn) => {
    setLoading(true);
    setError(null);

    try {
      const response = await requestFn(client);
      setData(response.data);
      return response.data;
    } catch (err) {
      const errorMessage =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'An unexpected error occurred';

      const wrappedError = new Error(errorMessage);
      wrappedError.status = err.response?.status ?? null;
      setError(wrappedError);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { data, error, loading, execute, reset };
}
