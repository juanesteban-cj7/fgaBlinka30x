import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { formatCurrency } from '../lib/utils'
import { Upload, Loader2, CheckCircle, Clock, CalendarClock, CalendarDays, Pencil, X } from 'lucide-react'
import type { Beneficiary, Invoice } from '../types'

type DateMode = 'due' | 'created'
type DateRange = '7' | '15' | '30' | 'all'

function parseInvoiceDate(value: string | null): Date | null {
  if (!value) return null
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  const date = new Date(year, month - 1, day)
  return Number.isNaN(date.getTime()) ? null : date
}

function parseCreatedDate(value: string | null): Date | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  date.setHours(0, 0, 0, 0)
  return date
}

function formatImportantDate(date: Date): string {
  return new Intl.DateTimeFormat('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

export default function Dashboard() {
  const [summary, setSummary] = useState<any>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [datesLoading, setDatesLoading] = useState(true)
  const [datesError, setDatesError] = useState<string | null>(null)
  const [dateMode, setDateMode] = useState<DateMode>('due')
  const [dateRange, setDateRange] = useState<DateRange>('30')
  const [editingBudget, setEditingBudget] = useState(false)
  const [budgetValue, setBudgetValue] = useState('')
  const [savingBudget, setSavingBudget] = useState(false)
  const [budgetError, setBudgetError] = useState<string | null>(null)

  useEffect(() => {
    api.dashboardSummary()
      .then(setSummary)
      .catch(() => setError('No se pudo cargar el resumen'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    Promise.all([api.listInvoices(), api.listBeneficiaries()])
      .then(([loadedInvoices, loadedBeneficiaries]) => {
        setInvoices(loadedInvoices)
        setBeneficiaries(loadedBeneficiaries)
      })
      .catch(() => setDatesError('No se pudieron cargar las fechas de las facturas'))
      .finally(() => setDatesLoading(false))
  }, [])

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const rangeDays = dateRange === 'all' ? null : Number(dateRange)
  const rangeLimit = new Date(today)
  if (rangeDays !== null) {
    rangeLimit.setDate(rangeLimit.getDate() + (dateMode === 'due' ? rangeDays : -rangeDays))
  }
  const importantDates = invoices
    .map((invoice) => ({
      invoice,
      date: dateMode === 'due' ? parseInvoiceDate(invoice.due_date) : parseCreatedDate(invoice.created_at),
    }))
    .filter((item): item is { invoice: Invoice; date: Date } => {
      if (!item.date) return false
      if (dateMode === 'due') return item.date >= today && (rangeDays === null || item.date <= rangeLimit)
      return item.date <= today && (rangeDays === null || item.date >= rangeLimit)
    })
    .sort((a, b) => dateMode === 'due'
      ? a.date.getTime() - b.date.getTime()
      : b.date.getTime() - a.date.getTime())
  const beneficiaryNames = new Map(beneficiaries.map((beneficiary) => [beneficiary.id, beneficiary.name]))
  const rangeLabel = dateRange === 'all' ? 'desde siempre' : `${dateRange} días`

  const startBudgetEdit = () => {
    setBudgetValue(String(summary?.budget_total ?? 0))
    setBudgetError(null)
    setEditingBudget(true)
  }

  const saveBudget = async (event: React.FormEvent) => {
    event.preventDefault()
    const periodBudget = Number(budgetValue)
    if (!Number.isFinite(periodBudget) || periodBudget < 0) {
      setBudgetError('Ingresa un presupuesto válido (igual o mayor que 0).')
      return
    }
    setSavingBudget(true)
    setBudgetError(null)
    try {
      const policy = await api.updateBudget({ period_budget: periodBudget })
      setSummary((current: any) => ({ ...current, budget_total: policy.period_budget }))
      setEditingBudget(false)
    } catch (err: any) {
      setBudgetError(err.detail || err.message || 'No se pudo actualizar el presupuesto.')
    } finally {
      setSavingBudget(false)
    }
  }

  if (loading) return <div className="center-panel"><Loader2 size={32} style={{ color: 'var(--color-text-muted)' }} /></div>
  if (error) return <div className="center-panel"><div className="alert alert-error">{error}</div></div>

  return (
    <div className="page">
      <div className="page-actions">
        <Link to="/upload" className="btn btn-primary">
          <Upload size={18} /> Cargar factura
        </Link>
      </div>

      <div className="metric-card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: '1rem' }}>
        <div>
          <div className="metric-label">Facturas totales</div>
          <div className="metric-value">{summary?.total ?? 0}</div>
        </div>
        <div>
          <div className="metric-label">Aptas para pago simulado</div>
          <div className="metric-value" style={{ color: 'var(--color-success)' }}>{summary?.ELIGIBLE_SIMULATED ?? 0}</div>
        </div>
        <div>
          <div className="metric-label">Canceladas</div>
          <div className="metric-value" style={{ color: 'var(--color-danger)' }}>{summary?.BLOCKED ?? 0}</div>
        </div>
        <div>
          <div className="metric-label">Requieren aprobación</div>
          <div className="metric-value" style={{ color: 'var(--color-warning)' }}>{summary?.NEEDS_HUMAN_APPROVAL ?? 0}</div>
        </div>
      </div>

      <div style={{ marginTop: '1.5rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: '1rem' }}>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', color: 'var(--color-success)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <CheckCircle size={24} /> <strong>Presupuesto</strong>
            </div>
            {!editingBudget && <button className="btn btn-sm btn-outline" onClick={startBudgetEdit}><Pencil size={15} /> Editar</button>}
          </div>
          <div className="metric-value" style={{ marginTop: '0.5rem', display: editingBudget ? 'none' : undefined }}>
            {summary?.budget_consumed != null ? formatCurrency(summary.budget_consumed) : '—'} / {summary?.budget_total != null ? formatCurrency(summary.budget_total) : '—'}
          </div>
          {editingBudget && (
            <form onSubmit={saveBudget} style={{ marginTop: '0.75rem' }}>
              <label className="metric-label" htmlFor="budget">Presupuesto en USD</label>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.35rem' }}>
                <input id="budget" className="form-control" type="number" min="0" step="0.01" value={budgetValue} onChange={(e) => setBudgetValue(e.target.value)} autoFocus disabled={savingBudget} />
                <button className="btn btn-primary" type="submit" disabled={savingBudget}>{savingBudget ? 'Guardando...' : 'Guardar'}</button>
                <button className="btn btn-outline btn-icon" type="button" aria-label="Cancelar edición" onClick={() => setEditingBudget(false)} disabled={savingBudget}><X size={18} /></button>
              </div>
              {budgetError && <div className="field-hint" style={{ color: 'var(--color-danger)' }}>{budgetError}</div>}
            </form>
          )}
        </div>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--color-text-muted)' }}>
            <Clock size={24} /> <strong>Última actualización</strong>
          </div>
          <div className="metric-value" style={{ marginTop: '0.5rem' }}>{new Date().toLocaleTimeString('es-CO')}</div>
        </div>
      </div>

      <section className="card" style={{ marginTop: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1rem' }}>Fechas importantes</h2>
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', marginTop: '0.2rem' }}>
              {dateMode === 'due' ? 'Vencimientos' : 'Facturas creadas'} · {rangeLabel}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <label className="important-date-filter">
              <span>Rango</span>
              <select className="form-control" value={dateRange} onChange={(event) => setDateRange(event.target.value as DateRange)} aria-label="Rango de fechas importantes">
                <option value="7">7 días</option>
                <option value="15">15 días</option>
                <option value="30">30 días</option>
                <option value="all">Desde Siempre</option>
              </select>
            </label>
            <label className="important-date-filter">
              <span>Fecha</span>
              <select className="form-control" value={dateMode} onChange={(event) => setDateMode(event.target.value as DateMode)} aria-label="Tipo de fecha importante">
                <option value="due">Por Vencimiento</option>
                <option value="created">Por Creación</option>
              </select>
            </label>
          </div>
        </div>

        {datesLoading ? (
          <div className="center-panel"><Loader2 size={24} /></div>
        ) : datesError ? (
          <div className="alert alert-error">{datesError}</div>
        ) : (
          <div>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.95rem', marginBottom: '0.5rem' }}>
              {dateMode === 'due' ? <CalendarClock size={18} /> : <CalendarDays size={18} />}
              {dateMode === 'due' ? 'Próximos vencimientos' : 'Creaciones recientes'}
            </h3>
            {importantDates.map(({ invoice, date }, index) => (
              <Link key={invoice.id} to={`/invoices/${invoice.id}`} className={`important-date-item${index === 0 ? ' nearest' : ''}`}>
                <span className="important-date-info">
                  <strong>{invoice.invoice_number || `Factura ${invoice.id}`}</strong>
                  <span className="important-date-meta">
                    <small>{beneficiaryNames.get(invoice.beneficiary_id ?? '') || 'Beneficiario no asignado'}</small>
                    <small>{formatCurrency(invoice.amount, invoice.currency || 'USD')}</small>
                  </span>
                </span>
                <span className="important-date-value">{formatImportantDate(date)}</span>
              </Link>
            ))}
            {importantDates.length === 0 && (
              <div className="empty-state" style={{ gridColumn: '1 / -1' }}>
                No hay facturas para este tipo de fecha y rango.
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
