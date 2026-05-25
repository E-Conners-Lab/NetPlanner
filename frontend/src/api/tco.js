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
 * If `body.parent_scenario_id` is set, the save joins that scenario's lineage
 * as the next version (PID amendment 1.5). Otherwise a new lineage starts at
 * v1 with `lineage_id = own id`.
 *
 * @param {string} projectId
 * @param {{ scenario_name: string, inputs: object, parent_scenario_id?: string }} body
 * @returns {Promise} TCOScenarioRead (= TCOResult + id, project_id, created_at, lineage_id, version)
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

/**
 * GET /projects/:id/tco/lineages/:lineageId
 * Returns every version in a lineage for a project, oldest first
 * (PID amendment 1.5).
 *
 * @param {string} projectId
 * @param {string} lineageId
 * @returns {Promise} TCOScenarioRead[]
 */
export function listTcoLineageVersions(projectId, lineageId) {
  return client.get(`/projects/${projectId}/tco/lineages/${lineageId}`);
}
