export type ConfigurationType = 'dockerfile' | 'docker_compose' | 'github_actions' | 'kubernetes' | 'terraform' | 'helm'
export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low'
export type FindingCategory = 'security' | 'reliability' | 'performance' | 'maintainability'
export type FindingSource = 'deterministic' | 'ai'

export interface ChatMessage {
  id: string
  finding_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface UserResponse {
  id: string
  email: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface ConfigurationCreate {
  name: string
  configuration_type: ConfigurationType
  original_content: string
}

export interface ConfigurationResponse {
  id: string
  user_id: string
  name: string
  configuration_type: ConfigurationType
  created_at: string
  updated_at: string
}

export interface FindingResponse {
  id: string
  rule_id: string | null
  category: FindingCategory
  severity: FindingSeverity
  title: string
  description: string
  recommendation: string
  line_number: number | null
  evidence: string
  source: FindingSource
  confidence: number | null
  fix_suggestion: string | null
}

export interface AnalysisResponse {
  id: string
  configuration_id: string
  status: string
  overall_score: number | null
  rule_version: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
  findings: FindingResponse[]
}
