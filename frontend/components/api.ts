export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

function errorMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(item => {
      if (!item || typeof item !== 'object') return 'Invalid request';
      const field = Array.isArray(item.loc) ? item.loc.filter((part: unknown) => part !== 'body').join(' / ').replaceAll('_', ' ') : '';
      return `${field ? field + ': ' : ''}${item.msg || 'Invalid value'}`;
    }).join('. ');
  }
  return '';
}

export async function api<T = any>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (options?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch('/api/v1' + path, { ...options, headers });
  if (!response.ok) {
    let message = '';
    try { message = errorMessage((await response.json()).detail); } catch { /* An unavailable proxy may return an HTML error page. */ }
    throw new ApiError(message || response.statusText || 'Request failed', response.status);
  }
  return response.json();
}

export const num = (v: number) => v.toLocaleString('en-US');
export const decimal = (v: number | null, d = 3) => v === null || !Number.isFinite(v) ? 'Not available' : v.toFixed(d);
export const artifact = (id: string, name: string) => `/api/v1/analyses/${id}/artifacts/${name}`;
