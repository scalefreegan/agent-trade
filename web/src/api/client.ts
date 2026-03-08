// API client using fetch
const API_BASE = '/api/v1';
const DEFAULT_TIMEOUT_MS = 30_000;

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

interface RequestOptions {
  signal?: AbortSignal;
}

function buildSignal(caller?: AbortSignal): AbortSignal {
  const timeout = AbortSignal.timeout(DEFAULT_TIMEOUT_MS);
  if (!caller) return timeout;
  return AbortSignal.any([caller, timeout]);
}

function parseErrorDetail(err: unknown, fallback: string): string {
  console.error('API error: failed to parse error response', err);
  return fallback;
}

function isJsonResponse(response: Response): boolean {
  const ct = response.headers.get('content-type');
  return !!ct && ct.includes('application/json');
}

async function parseJsonBody<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  if (!isJsonResponse(response)) {
    const text = await response.text();
    throw new Error(
      `Expected JSON response but got ${response.headers.get('content-type') ?? 'no content-type'}: ${text.slice(0, 200)}`,
    );
  }
  return response.json();
}

export async function fetchApi<T>(endpoint: string, opts?: RequestOptions): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    signal: buildSignal(opts?.signal),
  });
  if (!response.ok) {
    const detail = await response.json().then((d) => d?.detail).catch((err) => parseErrorDetail(err, response.statusText));
    throw new ApiError(detail || `API error: ${response.status}`, response.status);
  }
  return parseJsonBody<T>(response);
}

export async function postApi<T>(endpoint: string, body?: unknown, opts?: RequestOptions): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: buildSignal(opts?.signal),
  });
  if (!response.ok) {
    const detail = await response.json().then((d) => d?.detail).catch((err) => parseErrorDetail(err, response.statusText));
    throw new ApiError(detail || `API error: ${response.status}`, response.status);
  }
  return parseJsonBody<T>(response);
}

export async function patchApi<T>(endpoint: string, body: unknown, opts?: RequestOptions): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: buildSignal(opts?.signal),
  });
  if (!response.ok) {
    const detail = await response.json().then((d) => d?.detail).catch((err) => parseErrorDetail(err, response.statusText));
    throw new ApiError(detail || `API error: ${response.status}`, response.status);
  }
  return parseJsonBody<T>(response);
}

export async function putApi<T>(endpoint: string, body: unknown, opts?: RequestOptions): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: buildSignal(opts?.signal),
  });
  if (!response.ok) {
    const detail = await response.json().then((d) => d?.detail).catch((err) => parseErrorDetail(err, response.statusText));
    throw new ApiError(detail || `API error: ${response.status}`, response.status);
  }
  return parseJsonBody<T>(response);
}

export async function deleteApi(endpoint: string, opts?: RequestOptions): Promise<void> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'DELETE',
    signal: buildSignal(opts?.signal),
  });
  if (!response.ok) {
    const detail = await response.json().then((d) => d?.detail).catch((err) => parseErrorDetail(err, response.statusText));
    throw new ApiError(detail || `API error: ${response.status}`, response.status);
  }
}
