import client from './client.js';

/**
 * API functions for the /projects/:id/tco resource.
 * All functions return the Axios response promise so callers can
 * handle loading/error state themselves.
 */

/**
 * POST /projects/:id/tco/preview
 * Computes a TCO scenario WITHOUT saving it.
 *
 * @param {string} projectId
 * @param {{ scenario_name: string, inputs: object }} body
 * @returns {Promise} TCOResult
 */
export function previewTco(projectId, body) {
  return client.post(`/projects/${projectId}/tco/preview`, body);
}

/**
 * POST /projects/:id/tco
 * Computes AND saves a TCO scenario.
 *
 * @param {string} projectId
 * @param {{ scenario_name: string, inputs: object }} body
 * @returns {Promise} TCOScenarioRead (= TCOResult + id, project_id, created_at)
 */
export function saveTcoScenario(projectId, body) {
  return client.post(`/projects/${projectId}/tco`, body);
}

/**
 * GET /projects/:id/tco
 * Returns all saved TCO scenarios for a project, newest first.
 *
 * @param {string} projectId
 * @returns {Promise} TCOScenarioRead[]
 */
export function listTcoScenarios(projectId) {
  return client.get(`/projects/${projectId}/tco`);
}
