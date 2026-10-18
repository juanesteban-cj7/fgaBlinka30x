import { AppUser, Invoice, InvoiceCreate, InvoiceUpdate, Beneficiary, BeneficiaryCreate, BeneficiaryUpdate, LoginResponse, PaymentPolicy, DecisionRecord, DashboardSummary, InvoiceOutcome, BudgetUpdate, RuleCatalogItem, PolicyMutation, ApiValidationIssue } from '../types/index'

const API_BASE = '/api/v1'
export const DEMO_COMPANY_ID = 'co_demo_001'

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
    this.name = 'ApiError'
  }
}

function formatApiDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((issue: ApiValidationIssue | string) => {
      if (typeof issue === 'string') return issue
      const location = issue.loc?.filter((part) => part !== 'body' && part !== 'query' && part !== 'path').join('.')
      return [location, issue.msg].filter(Boolean).join(': ')
    }).filter(Boolean)
    return messages.length ? messages.join(' · ') : 'Los datos enviados no son válidos.'
  }
  if (detail && typeof detail === 'object') return JSON.stringify(detail)
  return ''
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let res: Response
  try {
    const headers = new Headers(options.headers)
    if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }
    const token = localStorage.getItem('access_token')
    if (token) headers.set('Authorization', `Bearer ${token}`)
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    })
  } catch (error) {
    if (error instanceof TypeError) {
      throw new ApiError(
        0,
        `No se pudo conectar con la API en ${API_BASE}${path}. Comprueba que el backend esté activo y que el proxy /api esté disponible desde la dirección de la aplicación.`,
      )
    }
    throw error
  }
  if (!res.ok) {
    if (res.status === 401 && path !== '/auth/login') redirectToLogin()
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = formatApiDetail((body as { detail?: unknown }).detail) || detail
    } catch {
      // ignorar si no es JSON
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as unknown as T
  return res.json()
}

function redirectToLogin() {
  localStorage.removeItem('access_token')
  if (window.location.pathname !== '/login') window.location.assign('/login')
}

function createInvoiceId(): string {
  const timestamp = Date.now().toString(36)
  const randomPart = Math.random().toString(36).slice(2, 14).padEnd(12, '0')
  return `inv_${timestamp}_${randomPart}`
}

async function postInvoiceFile(form: FormData): Promise<Invoice> {
  let res: Response
  try {
    const token = localStorage.getItem('access_token')
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined
    res = await fetch(`${API_BASE}/invoices/upload`, { method: 'POST', body: form, headers })
  } catch (error) {
    if (error instanceof TypeError) {
      throw new ApiError(
        0,
        `No se pudo conectar con la API en ${API_BASE}/invoices/upload. Comprueba que el backend esté activo y que el proxy /api esté disponible desde la dirección de la aplicación.`,
      )
    }
    throw error
  }
  if (!res.ok) {
    if (res.status === 401) redirectToLogin()
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = formatApiDetail((body as { detail?: unknown }).detail) || detail
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<Invoice>
}

export const api = {
  login: async (username: string, password: string) => {
    const result = await request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    localStorage.setItem('access_token', result.access_token)
    return result
  },
  getCurrentUser: () => request<AppUser>('/auth/me'),
  logout: () => localStorage.removeItem('access_token'),

  health: () => request<{ status: string }>('/health'),

  getPolicy: () => request<PaymentPolicy>('/policy/'),
  getPolicyCatalog: () => request<RuleCatalogItem[]>('/policy/catalog'),
  listPolicyVersions: () => request<PaymentPolicy[]>('/policy/versions'),
  createPolicy: (body: PolicyMutation) => request<PaymentPolicy>('/policy/', {
    method: 'PUT',
    body: JSON.stringify(body),
  }),
  updateBudget: (body: BudgetUpdate) => request<PaymentPolicy>('/policy/budget', {
    method: 'PATCH',
    body: JSON.stringify(body),
  }),
  activatePolicy: (policyId: string) => request<{ policy_id: string; active: boolean }>('/policy/activate', {
    method: 'POST',
    body: JSON.stringify({ policy_id: policyId }),
  }),

  listBeneficiaries: (companyId?: string) => {
    const qs = companyId ? `?company_id=${encodeURIComponent(companyId)}` : ''
    return request<Beneficiary[]>(`/beneficiaries${qs}`)
  },
  createBeneficiary: (body: BeneficiaryCreate) => request<Beneficiary>('/beneficiaries', {
    method: 'POST',
    body: JSON.stringify(body),
  }),
  updateBeneficiary: (id: string, body: BeneficiaryUpdate) => request<Beneficiary>(`/beneficiaries/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  }),

  listInvoices: (params?: { company_id?: string; status?: string; beneficiary_id?: string }) => {
    const qs = new URLSearchParams()
    if (params?.company_id) qs.set('company_id', params.company_id)
    if (params?.status) qs.set('status', params.status)
    if (params?.beneficiary_id) qs.set('beneficiary_id', params.beneficiary_id)
    return request<Invoice[]>(`/invoices?${qs.toString()}`)
  },
  createInvoice: (body: InvoiceCreate) => request<Invoice>('/invoices', {
    method: 'POST',
    body: JSON.stringify({ ...body, id: body.id ?? createInvoiceId() }),
  }),
  getInvoice: (id: string) => request<Invoice>(`/invoices/${id}`),
  updateInvoice: (id: string, body: InvoiceUpdate) => request<Invoice>(`/invoices/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  }),

  uploadInvoiceFile: (file: File): Promise<Invoice> => {
    const form = new FormData()
    form.append('file', file)
    form.append('company_id', DEMO_COMPANY_ID)
    return postInvoiceFile(form)
  },

  uploadInvoice: async (
    file: File | null,
    details: {
      beneficiaryId: string
      companyId: string
      invoiceNumber?: string
      amount: number
      currency: string
      issueDate: string
      dueDate: string
      description?: string
    },
  ): Promise<Invoice> => {
    const invoiceDetails = {
      beneficiary_id: details.beneficiaryId,
      amount: details.amount,
      currency: details.currency,
      issue_date: details.issueDate,
      due_date: details.dueDate,
      description: details.description,
    }
    if (!file) {
      return api.createInvoice({
        id: createInvoiceId(),
        company_id: details.companyId,
        invoice_number: details.invoiceNumber ?? null,
        ...invoiceDetails,
        source_type: 'manual',
      })
    }

    const form = new FormData()
    form.append('file', file)
    form.append('beneficiary_id', details.beneficiaryId)
    if (details.invoiceNumber) form.append('invoice_number', details.invoiceNumber)
    form.append('amount', String(details.amount))
    form.append('currency', details.currency)
    form.append('issue_date', details.issueDate)
    form.append('due_date', details.dueDate)
    if (details.description) form.append('description', details.description)
    return postInvoiceFile(form)
  },
  reextractInvoice: (id: string) => request<{ invoice_id: string; raw_text: string; extraction_confidence: number | null }>(`/invoices/${id}/extract`, {
    method: 'POST',
  }),

  evaluateInvoice: (id: string) => request<{
    invoice_id: string
    outcome: InvoiceOutcome
    reason_codes: string[]
    explanation: string | null
    reserved_budget: boolean
    linked_invoice_id: string | null
    policy_version: number | null
    rules_evaluated: string[]
    decision_id: string
  }>(`/invoices/${id}/evaluate`, { method: 'POST' }),
  listDecisions: (id: string) => request<DecisionRecord[]>(`/invoices/${id}/decisions`),
  reviewInvoice: (id: string, action: 'approve' | 'reject', reason: string) => request<{ invoice_id: string; status: InvoiceOutcome }>(`/invoices/${id}/review`, {
    method: 'POST',
    body: JSON.stringify({ action, reason }),
  }),

  dashboardSummary: (companyId?: string) => {
    const qs = companyId ? `?company_id=${encodeURIComponent(companyId)}` : ''
    return request<DashboardSummary>(`/dashboard/summary${qs}`)
  },
}
