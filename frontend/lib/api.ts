import type {
  AnalysisResponse,
  ConfigurationCreate,
  ConfigurationResponse,
  TokenResponse,
  UserResponse,
} from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> ?? {}),
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 204) return undefined as T
  const body = await res.json().catch(() => ({ detail: 'Request failed' }))
  if (!res.ok) throw new ApiError(res.status, (body as { detail?: string }).detail ?? 'Request failed')
  return body as T
}

export const register = (email: string, password: string) =>
  request<UserResponse>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })

export const login = (email: string, password: string) =>
  request<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })

export const getMe = () => request<UserResponse>('/api/v1/auth/me')

export const createConfiguration = (data: ConfigurationCreate) =>
  request<ConfigurationResponse>('/api/v1/configurations/', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const listConfigurations = () =>
  request<ConfigurationResponse[]>('/api/v1/configurations/')

export const getConfiguration = (id: string) =>
  request<ConfigurationResponse>(`/api/v1/configurations/${id}`)

export const deleteConfiguration = (id: string) =>
  request<void>(`/api/v1/configurations/${id}`, { method: 'DELETE' })

export const analyzeConfiguration = (id: string) =>
  request<AnalysisResponse>(`/api/v1/configurations/${id}/analyze`, { method: 'POST' })

export const listAnalyses = () =>
  request<AnalysisResponse[]>('/api/v1/analyses/')

export const getAnalysis = (id: string) =>
  request<AnalysisResponse>(`/api/v1/analyses/${id}`)

export async function downloadSarif(analysisId: string): Promise<void> {
  const token = getToken()
  const res = await fetch(`${API_BASE}/api/v1/analyses/${analysisId}/sarif`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new ApiError(res.status, 'SARIF export failed')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `analysis-${analysisId}.sarif`
  a.click()
  URL.revokeObjectURL(url)
}
