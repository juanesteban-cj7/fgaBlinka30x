import { AuditAction } from '../types'

export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}

export function formatCurrency(value: number | null | undefined, currency = 'USD'): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('es-CO', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

export function outcomeLabel(outcome: string): string {
  switch (outcome) {
    case 'ELIGIBLE_SIMULATED': return 'Apta para pago simulado'
    case 'BLOCKED': return 'Frenada'
    case 'NEEDS_HUMAN_APPROVAL': return 'Requiere aprobación'
    case 'PENDING': return 'Pendiente'
    case 'APPROVED': return 'Aprobada por revisión humana'
    case 'HUMAN_APPROVED': return 'Aprobada por revisión humana'
    case 'REJECTED': return 'Rechazada por revisión humana'
    default: return outcome
  }
}

export function outcomeClass(outcome: string): string {
  switch (outcome) {
    case 'ELIGIBLE_SIMULATED': return 'badge-eligible'
    case 'BLOCKED': return 'badge-blocked'
    case 'NEEDS_HUMAN_APPROVAL': return 'badge-approval'
    case 'PENDING': return 'badge-pending'
    case 'APPROVED': return 'badge-eligible'
    case 'HUMAN_APPROVED': return 'badge-eligible'
    case 'REJECTED': return 'badge-blocked'
    default: return 'badge-pending'
  }
}

export function actionLabel(action: AuditAction): string {
  switch (action) {
    case 'POLICY_CREATED': return 'Política editada'
    case 'POLICY_ACTIVATED': return 'Política activada'
    case 'POLICY_BUDGET_UPDATED': return 'Presupuesto actualizado'
    case 'BENEFICIARY_CREATED': return 'Beneficiario añadido'
    case 'BENEFICIARY_UPDATED': return 'Beneficiario editado'
    case 'BENEFICIARY_DELETED': return 'Beneficiario eliminado'
    case 'INVOICE_UPLOADED': return 'Factura cargada'
    case 'INVOICE_APPROVED': return 'Factura aprobada'
    case 'INVOICE_REJECTED': return 'Factura rechazada'
    case 'INVOICE_EVALUATED': return 'Factura evaluada'
  }
}

export function actionClass(action: AuditAction): string {
  switch (action) {
    case 'POLICY_ACTIVATED':
    case 'INVOICE_APPROVED':
      return 'badge-eligible'
    case 'BENEFICIARY_DELETED':
    case 'INVOICE_REJECTED':
      return 'badge-blocked'
    case 'POLICY_BUDGET_UPDATED':
    case 'INVOICE_UPLOADED':
    case 'INVOICE_EVALUATED':
      return 'badge-approval'
    case 'POLICY_CREATED':
    case 'BENEFICIARY_CREATED':
    case 'BENEFICIARY_UPDATED':
      return 'badge-pending'
  }
}

export function reasonChipClass(code: string): string {
  if (code.includes('BLOCKED') || code === 'DUPLICATE_CONFIRMED' || code === 'BENEFICIARY_NOT_ALLOWED' || code === 'BENEFICIARY_UNKNOWN' || code === 'ABOVE_MAX_INVOICE' || code === 'BUDGET_EXCEEDED') return 'chip-blocked'
  if (code.includes('APPROVAL') || code === 'AGREEMENT_AMOUNT_MISMATCH' || code === 'AGREEMENT_EXPIRED' || code === 'CURRENCY_MISMATCH' || code === 'BENEFICIARY_NAME_AMBIGUOUS' || code === 'POSSIBLE_DUPLICATE') return 'chip-approval'
  if (code === 'MISSING_REQUIRED_FIELDS' || code === 'LOW_EXTRACTION_CONFIDENCE' || code === 'INVALID_FIELD') return 'chip-info'
  return 'chip-ok'
}
