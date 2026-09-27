import { API_BASE } from './api';

async function request(path: string, init?: RequestInit) {
  const r = await fetch(`${API_BASE}${path}`, init);
  if (!r.ok) {
    const body = await r.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(body.detail || 'Request failed');
  }
  return r.json();
}

export const getPortfolio = (id: string) => request(`/portfolio/${id}`);
export const getMonitor = (id: string) => request(`/monitor/${id}`);
export const startInterview = (id: string, mode = 'Project Defense') =>
  request(`/interview/${id}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
export const answerInterview = (session: string, question_index: number, answer: string) =>
  request(`/interview/sessions/${session}/answers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_index, answer }),
  });
export const getPassport = (id: string) => request(`/passport/${id}`);
export const verifyPassport = (id: string) =>
  request(`/passport/${id}/verify`, { method: 'POST' });
