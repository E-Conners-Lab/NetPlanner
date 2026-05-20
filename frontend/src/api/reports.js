import client from './client.js';

/**
 * API functions for the /projects/:id/conversations and /projects/:id/reports resources.
 * All functions return the Axios response promise so callers can handle loading/error state.
 */

/**
 * GET /projects/:id/conversations
 * Returns all advisor conversations for a project, newest first.
 *
 * @param {string} projectId
 * @returns {Promise} ConversationSummary[]
 */
export function listConversations(projectId) {
  return client.get(`/projects/${projectId}/conversations`);
}

/**
 * GET /projects/:id/conversations/:conversationId/messages
 * Returns the chronological message history for one conversation.
 * Used by the Advisor UI to re-hydrate a previous conversation.
 *
 * @param {string} projectId
 * @param {string} conversationId
 * @returns {Promise} MessageRead[]
 */
export function getConversationMessages(projectId, conversationId) {
  return client.get(
    `/projects/${projectId}/conversations/${conversationId}/messages`,
  );
}

/**
 * POST /projects/:id/reports
 * Generates a PDF report from the selected artifacts.
 * The response is a binary PDF blob — pass `{ responseType: 'blob' }` via axios config.
 *
 * @param {string} projectId
 * @param {{ title: string, artifacts: Array<{ kind: string, ref_id: string }> }} body
 * @returns {Promise} Axios response with blob data
 */
export function generateReport(projectId, body) {
  return client.post(`/projects/${projectId}/reports`, body, {
    responseType: 'blob',
    timeout: 120_000,
  });
}

/**
 * GET /projects/:id/reports
 * Returns the export history for a project, newest first.
 *
 * @param {string} projectId
 * @returns {Promise} ReportRead[]
 */
export function listReports(projectId) {
  return client.get(`/projects/${projectId}/reports`);
}

/**
 * GET /projects/:id/reports/:reportId/pdf
 * Re-renders a previously-generated report and returns it as a PDF blob.
 * Pass `{ responseType: 'blob' }` is already applied — callers feed the
 * response to the same `triggerPdfDownload` helper as `generateReport`.
 *
 * @param {string} projectId
 * @param {string} reportId
 * @returns {Promise} Axios response with blob data
 */
export function downloadReportPdf(projectId, reportId) {
  return client.get(`/projects/${projectId}/reports/${reportId}/pdf`, {
    responseType: 'blob',
    timeout: 120_000,
  });
}
