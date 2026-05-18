import client from './client.js';

/**
 * API functions for the /projects resource.
 * All functions return the Axios response promise so callers (useApi, hooks)
 * can handle loading/error state themselves.
 */

/** GET /projects — returns ProjectRead[] newest first */
export function listProjects() {
  return client.get('/projects');
}

/** POST /projects — returns ProjectRead (201) */
export function createProject(data) {
  return client.post('/projects', data);
}

/** GET /projects/:id — returns ProjectRead (200) or throws 404 */
export function getProject(id) {
  return client.get(`/projects/${id}`);
}

/**
 * PUT /projects/:id — partial update, returns ProjectRead (200).
 * Send only the fields that changed.
 */
export function updateProject(id, data) {
  return client.put(`/projects/${id}`, data);
}

/** DELETE /projects/:id — returns 204 (no body) */
export function deleteProject(id) {
  return client.delete(`/projects/${id}`);
}
