import client from './client.js';

/**
 * API functions for the /projects/:id/comparison resource.
 * All functions return the Axios response promise so callers can
 * handle loading/error state themselves.
 *
 * NOTE: generateComparison triggers live web research + AI synthesis —
 * expect 30-60 seconds of latency. The axios client timeout is overridden
 * to 120s for this call.
 */

/**
 * POST /projects/:id/comparison
 * Runs live web research and AI synthesis for the given vendors + criteria.
 *
 * @param {string} projectId
 * @param {{ vendors: string[], criteria: string[] }} body
 * @returns {Promise} VendorComparisonRead (201)
 */
export function generateComparison(projectId, body) {
  return client.post(`/projects/${projectId}/comparison`, body, {
    timeout: 120_000,
  });
}

/**
 * GET /projects/:id/comparison
 * Returns all saved comparisons for a project, newest first.
 *
 * @param {string} projectId
 * @returns {Promise} VendorComparisonRead[]
 */
export function listComparisons(projectId) {
  return client.get(`/projects/${projectId}/comparison`);
}
