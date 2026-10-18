import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { api } from '../services/api'
import { actionClass, actionLabel, outcomeClass, outcomeLabel } from '../lib/utils'
import { AuditAction, AuditLogEntry, Invoice } from '../types'

const AUDIT_ACTIONS: AuditAction[] = [
  'POLICY_CREATED',
  'POLICY_ACTIVATED',
  'POLICY_BUDGET_UPDATED',
  'BENEFICIARY_CREATED',
  'BENEFICIARY_UPDATED',
  'BENEFICIARY_DELETED',
  'INVOICE_UPLOADED',
  'INVOICE_APPROVED',
  'INVOICE_REJECTED',
  'INVOICE_EVALUATED',
]

const PAGE_SIZE = 50

interface AuditFilters {
  action: AuditAction | ''
  actor_id: string
  date_from: string
  date_to: string
  q: string
}

const EMPTY_FILTERS: AuditFilters = {
  action: '',
  actor_id: '',
  date_from: '',
  date_to: '',
  q: '',
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Ocurrió un error inesperado.'
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function formatChangeValue(value: unknown): string {
  if (value == null) return '—'
  if (typeof value === 'string') return value
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function entityPath(entry: AuditLogEntry): string | null {
  if (entry.entity_type === 'invoice') return `/invoices/${encodeURIComponent(entry.entity_id)}`
  if (entry.entity_type === 'policy') return '/rules'
  if (entry.entity_type === 'beneficiary' && entry.action !== 'BENEFICIARY_DELETED') {
    return '/beneficiaries'
  }
  return null
}

function ActivityTab() {
  const [draft, setDraft] = useState<AuditFilters>(EMPTY_FILTERS)
  const [filters, setFilters] = useState<AuditFilters>(EMPTY_FILTERS)
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [actorOptions, setActorOptions] = useState<Array<{ id: string; name: string }>>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let current = true
    setLoading(true)
    setError('')
    api.listAuditLog({
      action: filters.action || undefined,
      actor_id: filters.actor_id || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      q: filters.q.trim() || undefined,
      limit: PAGE_SIZE,
      offset: 0,
    })
      .then((page) => {
        if (!current) return
        setEntries(page.items)
        setTotal(page.total)
        setActorOptions((previous) => {
          const options = new Map(previous.map((actor) => [actor.id, actor]))
          page.items.forEach((entry) => {
            if (entry.actor_id) options.set(entry.actor_id, { id: entry.actor_id, name: entry.actor_name })
          })
          return [...options.values()].sort((a, b) => a.name.localeCompare(b.name, 'es'))
        })
      })
      .catch((loadError: unknown) => {
        if (current) setError(errorMessage(loadError))
      })
      .finally(() => {
        if (current) setLoading(false)
      })
    return () => { current = false }
  }, [filters])

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFilters({ ...draft })
  }

  async function loadMore() {
    setLoadingMore(true)
    setError('')
    try {
      const page = await api.listAuditLog({
        action: filters.action || undefined,
        actor_id: filters.actor_id || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        q: filters.q.trim() || undefined,
        limit: PAGE_SIZE,
        offset: entries.length,
      })
      setEntries((current) => [...current, ...page.items])
      setTotal(page.total)
      setActorOptions((previous) => {
        const options = new Map(previous.map((actor) => [actor.id, actor]))
        page.items.forEach((entry) => {
          if (entry.actor_id) options.set(entry.actor_id, { id: entry.actor_id, name: entry.actor_name })
        })
        return [...options.values()].sort((a, b) => a.name.localeCompare(b.name, 'es'))
      })
    } catch (loadError) {
      setError(errorMessage(loadError))
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <>
      <form className="card" onSubmit={applyFilters} style={{ marginBottom: '1rem' }}>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="audit-action">Acción</label>
            <select
              id="audit-action"
              className="form-control"
              value={draft.action}
              onChange={(event) => setDraft({ ...draft, action: event.target.value as AuditAction | '' })}
            >
              <option value="">Todas las acciones</option>
              {AUDIT_ACTIONS.map((action) => (
                <option key={action} value={action}>{actionLabel(action)}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="audit-actor">Usuario</label>
            <select
              id="audit-actor"
              className="form-control"
              value={draft.actor_id}
              onChange={(event) => setDraft({ ...draft, actor_id: event.target.value })}
            >
              <option value="">Todos los usuarios</option>
              {actorOptions.map((actor) => (
                <option key={actor.id} value={actor.id}>{actor.name}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="audit-date-from">Desde</label>
            <input
              id="audit-date-from"
              className="form-control"
              type="date"
              value={draft.date_from}
              onChange={(event) => setDraft({ ...draft, date_from: event.target.value })}
            />
          </div>
          <div className="form-group">
            <label htmlFor="audit-date-to">Hasta</label>
            <input
              id="audit-date-to"
              className="form-control"
              type="date"
              value={draft.date_to}
              onChange={(event) => setDraft({ ...draft, date_to: event.target.value })}
            />
          </div>
          <div className="form-group">
            <label htmlFor="audit-search">Buscar en el detalle</label>
            <input
              id="audit-search"
              className="form-control"
              type="search"
              value={draft.q}
              onChange={(event) => setDraft({ ...draft, q: event.target.value })}
              placeholder="Texto del detalle"
            />
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-primary" type="submit">Filtrar</button>
          <button
            className="btn btn-outline"
            type="button"
            onClick={() => {
              setDraft(EMPTY_FILTERS)
              setFilters(EMPTY_FILTERS)
            }}
          >
            Limpiar
          </button>
        </div>
      </form>

      {error && <div className="alert alert-error">{error}</div>}
      {loading ? (
        <div className="center-panel"><Loader2 size={32} className="spin" /></div>
      ) : entries.length === 0 ? (
        <div className="center-panel"><div className="empty-state">No hay actividad que coincida con los filtros.</div></div>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fecha y hora</th>
                  <th>Usuario</th>
                  <th>Acción</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => {
                  const path = entityPath(entry)
                  const reason = entry.metadata?.reason ?? entry.metadata?.change_reason
                  const hasDetails = Boolean(entry.changes && Object.keys(entry.changes).length) || reason != null
                  return (
                    <tr key={entry.id}>
                      <td>{formatDateTime(entry.created_at)}</td>
                      <td>
                        {entry.actor_type === 'system'
                          ? <span className="badge badge-pending">Sistema</span>
                          : entry.actor_name}
                      </td>
                      <td><span className={`badge ${actionClass(entry.action)}`}>{actionLabel(entry.action)}</span></td>
                      <td>
                        <div>{entry.summary}</div>
                        {path && <Link to={path} className="btn btn-sm btn-outline" style={{ marginTop: '0.4rem' }}>Ver entidad</Link>}
                        {hasDetails && (
                          <details style={{ marginTop: '0.5rem' }}>
                            <summary style={{ cursor: 'pointer', color: 'var(--color-primary)' }}>
                              Ver cambios y justificación
                            </summary>
                            {entry.changes && Object.keys(entry.changes).length > 0 && (
                              <ul>
                                {Object.entries(entry.changes).map(([field, change]) => (
                                  <li key={field}>
                                    <strong>{field}:</strong> {formatChangeValue(change.before)} → {formatChangeValue(change.after)}
                                  </li>
                                ))}
                              </ul>
                            )}
                            {reason != null && (
                              <p><strong>Justificación:</strong> {formatChangeValue(reason)}</p>
                            )}
                          </details>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
            Mostrando {entries.length} de {total} registros.
          </p>
          {entries.length < total && (
            <button className="btn btn-outline" type="button" onClick={loadMore} disabled={loadingMore}>
              {loadingMore ? <><Loader2 size={16} className="spin" /> Cargando…</> : 'Cargar más'}
            </button>
          )}
        </>
      )}
    </>
  )
}

function DecisionsTab() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let current = true
    api.listInvoices()
      .then((result) => {
        if (current) setInvoices(result)
      })
      .catch((loadError: unknown) => {
        if (current) setError(errorMessage(loadError))
      })
      .finally(() => {
        if (current) setLoading(false)
      })
    return () => { current = false }
  }, [])

  if (loading) return <div className="center-panel"><Loader2 size={32} className="spin" /></div>
  if (error) return <div className="alert alert-error">{error}</div>
  if (invoices.length === 0) {
    return <div className="center-panel"><div className="empty-state">Sin facturas en el historial.</div></div>
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Factura</th>
            <th>Resultado</th>
            <th>Versión política</th>
            <th>Ver detalle</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((invoice) => (
            <tr key={invoice.id}>
              <td>{invoice.invoice_number || invoice.id}</td>
              <td><span className={`badge ${outcomeClass(invoice.status)}`}>{outcomeLabel(invoice.status)}</span></td>
              <td>{invoice.last_policy_version == null ? '—' : `v${invoice.last_policy_version}`}</td>
              <td><Link to={`/invoices/${invoice.id}`} className="btn btn-sm btn-outline">Ver</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function History() {
  const [activeTab, setActiveTab] = useState<'activity' | 'decisions'>('activity')

  return (
    <div className="page">
      <div className="card" style={{ marginBottom: '1rem' }}>
        <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', margin: 0 }}>
          Consulta la actividad del sistema y las decisiones registradas para cada factura.
        </p>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }} role="tablist" aria-label="Secciones del historial">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'activity'}
          className={`btn ${activeTab === 'activity' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setActiveTab('activity')}
        >
          Actividad
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'decisions'}
          className={`btn ${activeTab === 'decisions' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setActiveTab('decisions')}
        >
          Decisiones por factura
        </button>
      </div>
      {activeTab === 'activity' ? <ActivityTab /> : <DecisionsTab />}
    </div>
  )
}
