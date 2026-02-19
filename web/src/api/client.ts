// API client using fetch
const API_BASE = '/api/v1';

function parseErrorDetail(err: unknown, fallback: string): string {
  console.error('API error: failed to parse error response', err);
  return fallback;
}

export async function fetchApi<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    const detail = await response.json().then((d) => d?.detail).catch((err) => parseErrorDetail(err, response.statusText));
    throw new Error(detail || `API error: ${response.status}`);
  }
  return response.json();
}

export async function postApi<T>(endpoint: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const detail = await response.json().then((d) => d?.detail).catch((err) => parseErrorDetail(err, response.statusText));
    throw new Error(detail || `API error: ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function patchApi<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.json().then((d) => d?.detail).catch((err) => parseErrorDetail(err, response.statusText));
    throw new Error(detail || `API error: ${response.status}`);
  }
  return response.json();
}

export async function putApi<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.json().then((d) => d?.detail).catch((err) => parseErrorDetail(err, response.statusText));
    throw new Error(detail || `API error: ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function deleteApi(endpoint: string): Promise<void> {
  const response = await fetch(`${API_BASE}${endpoint}`, { method: 'DELETE' });
  if (!response.ok) {
    const detail = await response.json().then((d) => d?.detail).catch((err) => parseErrorDetail(err, response.statusText));
    throw new Error(detail || `API error: ${response.status}`);
  }
}
