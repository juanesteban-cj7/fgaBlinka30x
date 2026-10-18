/* Tipos del dominio compartidos con la API del backend (Fases 2-4). */

export type InvoiceOutcome =
  | 'ELIGIBLE_SIMULATED'
  | 'NEEDS_HUMAN_APPROVAL'
  | 'BLOCKED'
  | 'PENDING'
  | 'APPROVED'
  | 'HUMAN_APPROVED'
  | 'REJECTED'

export type InvoiceSource = 'pdf' | 'image' | 'manual' | 'email_text' | 'history'
export type InvoiceFieldSource = 'pdf' | 'image' | 'ocr' | 'manual'

export interface AppUser {
  id: string
  username: string
  full_name: string
  is_active: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: AppUser
}

export interface InvoiceExtractedFields {
  beneficiary_name?: string | null
  invoice_number?: string | null
  amount?: string | null
  currency?: string | null
  issue_date?: string | null
  due_date?: string | null
  description?: string | null
  _field_sources?: Record<string, InvoiceFieldSource>
}

export interface Invoice {
  id: string
  company_id: string
  beneficiary_id: string | null
  invoice_number: string | null
  amount: number | null
  currency: string | null
  issue_date: string | null
  due_date: string | null
  description: string | null
  source_type: InvoiceSource
  file_name: string | null
  file_hash: string | null
  file_path: string | null
  extraction_confidence: number | null
  raw_text: string | null
  extracted: InvoiceExtractedFields | null
  status: InvoiceOutcome
  created_at: string | null
  last_policy_version?: number | null
}

export interface InvoiceCreate {
  id?: string
  company_id: string
  beneficiary_id?: string | null
  invoice_number?: string | null
  amount?: number | null
  currency?: string | null
  issue_date?: string | null
  due_date?: string | null
  description?: string | null
  source_type: InvoiceSource
  file_name?: string | null
  file_hash?: string | null
  extraction_confidence?: number | null
  raw_text?: string | null
  extracted?: InvoiceExtractedFields | null
}

export interface InvoiceUpdate {
  standardize_number?: boolean
  beneficiary_id?: string | null
  beneficiary_name?: string | null
  invoice_number?: string | null
  amount?: number | null
  currency?: string | null
  issue_date?: string | null
  due_date?: string | null
  description?: string | null
}

export interface Beneficiary {
  id: string
  company_id: string
  name: string
  normalized_name: string
  allowed: boolean
  reference_code: string | null
  category: string | null
}

export interface BeneficiaryCreate {
  id: string
  company_id: string
  name: string
  normalized_name: string
  allowed?: boolean
  reference_code?: string | null
  category?: string | null
}

export interface BeneficiaryUpdate {
  name?: string
  allowed?: boolean
  reference_code?: string | null
  category?: string | null
}

export interface PolicyRuleAction {
  code: string
  action: RuleActionName
}

export type RuleActionName = 'BLOCKED' | 'NEEDS_HUMAN_APPROVAL'

export interface PaymentPolicy {
  id: string
  company_id: string
  version: number
  active: boolean
  currency: string
  max_invoice_amount: number
  approval_threshold: number
  period_budget: number
  period_type: string
  period_basis: string
  amount_tolerance_pct: number
  min_extraction_confidence: number
  name_similarity_threshold: number
  possible_duplicate_date_window_days: number
  created_at: string | null
  rule_actions: PolicyRuleAction[]
}

export interface RuleCatalogItem {
  code: string
  rule: string
  label: string
  description: string
  allowed_actions: RuleActionName[]
  default_action: RuleActionName
}

export interface PolicyMutation {
  company_id: string
  version: number
  currency: string
  max_invoice_amount: number
  approval_threshold: number
  period_budget: number
  period_type: string
  period_basis: string
  amount_tolerance_pct: number
  min_extraction_confidence: number
  name_similarity_threshold: number
  possible_duplicate_date_window_days: number
  rule_actions: PolicyRuleAction[]
  change_reason: string
  activate: boolean
}

export interface PolicyDraft {
  version: number
  currency: string
  max_invoice_amount: string
  approval_threshold: string
  period_budget: string
  period_type: string
  period_basis: string
  amount_tolerance_pct: string
  min_extraction_confidence: string
  name_similarity_threshold: string
  possible_duplicate_date_window_days: string
  rule_actions: PolicyRuleAction[]
  change_reason: string
  activate: boolean
}

export interface DecisionRecord {
  id: string
  invoice_id: string
  policy_version: number
  outcome: InvoiceOutcome
  reason_codes: string[]
  explanation: string | null
  rules_evaluated: string[]
  created_at: string | null
}

export type AuditAction =
  | 'POLICY_CREATED'
  | 'POLICY_ACTIVATED'
  | 'POLICY_BUDGET_UPDATED'
  | 'BENEFICIARY_CREATED'
  | 'BENEFICIARY_UPDATED'
  | 'BENEFICIARY_DELETED'
  | 'INVOICE_UPLOADED'
  | 'INVOICE_APPROVED'
  | 'INVOICE_REJECTED'
  | 'INVOICE_EVALUATED'

export interface AuditLogEntry {
  id: string
  created_at: string
  actor_type: 'user' | 'system'
  actor_id: string | null
  actor_name: string
  action: AuditAction
  entity_type: 'policy' | 'beneficiary' | 'invoice'
  entity_id: string
  entity_label: string
  company_id: string | null
  summary: string
  changes: Record<string, { before: unknown; after: unknown }> | null
  metadata: Record<string, unknown> | null
}

export interface AuditLogPage {
  items: AuditLogEntry[]
  total: number
}

export interface DashboardSummary {
  total: number
  ELIGIBLE_SIMULATED: number
  BLOCKED: number
  NEEDS_HUMAN_APPROVAL: number
  PENDING: number
  budget_consumed: number
  budget_total: number
}

export interface BudgetUpdate {
  period_budget: number
}

export interface ApiValidationIssue {
  loc?: Array<string | number>
  msg?: string
  type?: string
}
