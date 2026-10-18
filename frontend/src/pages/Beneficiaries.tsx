import { useEffect, useState } from 'react'
import { api, DEMO_COMPANY_ID } from '../services/api'
import type { Beneficiary } from '../types'
import { Loader2, Pencil, Trash2, UserRoundPlus, X } from 'lucide-react'

type BeneficiaryDialogMode = 'create' | 'edit' | null

interface BeneficiaryDraft {
  name: string
  category: string
  referenceCode: string
  allowed: boolean
}

const emptyDraft: BeneficiaryDraft = {
  name: '',
  category: '',
  referenceCode: '',
  allowed: true,
}

function normalizeBeneficiaryName(name: string): string {
  return name.normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\./g, '')
    .replace(/[^a-z0-9 ]/g, ' ')
    .trim()
    .replace(/\s+/g, ' ')
}

export default function Beneficiaries() {
  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [dialog, setDialog] = useState<BeneficiaryDialogMode>(null)
  const [draft, setDraft] = useState<BeneficiaryDraft>(emptyDraft)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const selectedBeneficiary = beneficiaries.find((item) => item.id === selectedId)

  useEffect(() => {
    api.listBeneficiaries()
      .then(setBeneficiaries)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'No se pudieron cargar los beneficiarios')
      })
      .finally(() => setLoading(false))
  }, [])

  const openDialog = (mode: Exclude<BeneficiaryDialogMode, null>) => {
    setError(null)
    setSuccess(null)
    if (mode === 'edit' && selectedBeneficiary) {
      setDraft({
        name: selectedBeneficiary.name,
        category: selectedBeneficiary.category ?? '',
        referenceCode: selectedBeneficiary.reference_code ?? '',
        allowed: selectedBeneficiary.allowed,
      })
    } else {
      setDraft(emptyDraft)
    }
    setDialog(mode)
  }

  const saveBeneficiary = async (event: React.FormEvent) => {
    event.preventDefault()
    const name = draft.name.trim()
    if (!name) {
      setError('El nombre del beneficiario es obligatorio.')
      return
    }

    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const values = {
        name,
        category: draft.category.trim() || null,
        reference_code: draft.referenceCode.trim() || null,
        allowed: draft.allowed,
      }
      if (dialog === 'edit' && selectedBeneficiary) {
        const updated = await api.updateBeneficiary(selectedBeneficiary.id, values)
        setBeneficiaries((current) => current.map((item) => item.id === updated.id ? updated : item))
        setSuccess('Beneficiario actualizado.')
      } else if (dialog === 'create') {
        const created = await api.createBeneficiary({
          id: `ben_${crypto.randomUUID()}`,
          company_id: beneficiaries[0]?.company_id ?? DEMO_COMPANY_ID,
          normalized_name: normalizeBeneficiaryName(name),
          ...values,
        })
        setBeneficiaries((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)))
        setSelectedId(created.id)
        setSuccess('Beneficiario añadido y seleccionado.')
      } else {
        return
      }
      setDialog(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar el beneficiario.')
    } finally {
      setSaving(false)
    }
  }

  const removeBeneficiary = async (beneficiary: Beneficiary) => {
    if (!window.confirm(`¿Eliminar a ${beneficiary.name}? Esta acción no se puede deshacer.`)) return
    setError(null)
    setSuccess(null)
    try {
      await api.deleteBeneficiary(beneficiary.id)
      setBeneficiaries((current) => current.filter((item) => item.id !== beneficiary.id))
      setSelectedId((current) => current === beneficiary.id ? null : current)
      setSuccess(`Se eliminó el beneficiario ${beneficiary.name}.`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'No se pudo eliminar el beneficiario.')
    }
  }

  if (loading) return <div className="center-panel"><Loader2 size={32} /></div>

  return (
    <div className="page">
      <div className="page-header beneficiaries-page-header">
        <div>
          <h1>Beneficiarios</h1>
          <p className="subtitle">Administra y selecciona los proveedores registrados.</p>
        </div>
        <div className="beneficiary-management-actions">
          <button type="button" className="btn btn-primary" onClick={() => openDialog('create')}>
            <UserRoundPlus size={16} aria-hidden="true" /> Añadir beneficiario
          </button>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => openDialog('edit')}
            disabled={!selectedBeneficiary}
          >
            <Pencil size={16} aria-hidden="true" /> Editar seleccionado
          </button>
        </div>
      </div>

      {error && !dialog && <div className="alert alert-error" role="alert">{error}</div>}
      {success && <div className="alert alert-success" role="status">{success}</div>}

      <div className="card beneficiaries-table-card">
        {beneficiaries.length > 0 ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Nombre</th>
                  <th scope="col">Categoría</th>
                  <th scope="col">¿Permitido?</th>
                  <th scope="col">Código referencia</th>
                  <th scope="col">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {beneficiaries.map((beneficiary) => (
                  <tr key={beneficiary.id} className={selectedId === beneficiary.id ? 'beneficiary-row-selected' : undefined}>
                    <td>{beneficiary.name}</td>
                    <td>{beneficiary.category || '—'}</td>
                    <td>
                      <span className="beneficiary-status">
                        {beneficiary.allowed ? '● Permitido' : '○ No permitido'}
                      </span>
                    </td>
                    <td className="beneficiary-reference">{beneficiary.reference_code || '—'}</td>
                    <td>
                      <div className="beneficiary-row-actions">
                        <button
                          type="button"
                          className="btn btn-outline"
                          aria-pressed={selectedId === beneficiary.id}
                          onClick={() => {
                            setSelectedId(beneficiary.id)
                            setError(null)
                            setSuccess(null)
                          }}
                        >
                          Seleccionar
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline"
                          onClick={() => {
                            setSelectedId(beneficiary.id)
                            setError(null)
                            setSuccess(null)
                            setDraft({
                              name: beneficiary.name,
                              category: beneficiary.category ?? '',
                              referenceCode: beneficiary.reference_code ?? '',
                              allowed: beneficiary.allowed,
                            })
                            setDialog('edit')
                          }}
                        >
                          <Pencil size={14} aria-hidden="true" /> Editar
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline"
                          onClick={() => removeBeneficiary(beneficiary)}
                        >
                          <Trash2 size={14} aria-hidden="true" /> Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No hay beneficiarios registrados. Añade uno para comenzar.</div>
        )}
      </div>

      {dialog && (
        <div className="beneficiary-dialog-backdrop">
          <section
            className="beneficiary-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="beneficiary-dialog-title"
          >
            <div className="beneficiary-dialog-heading">
              <h2 id="beneficiary-dialog-title">
                {dialog === 'edit' ? 'Editar beneficiario' : 'Añadir beneficiario'}
              </h2>
              <button
                type="button"
                className="btn btn-outline"
                aria-label="Cerrar"
                onClick={() => setDialog(null)}
                disabled={saving}
              >
                <X size={18} aria-hidden="true" />
              </button>
            </div>

            {error && <div className="alert alert-error" role="alert">{error}</div>}

            <form onSubmit={saveBeneficiary}>
              <div className="form-group">
                <label htmlFor="beneficiary-name">Nombre</label>
                <input
                  id="beneficiary-name"
                  className="form-control"
                  value={draft.name}
                  onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
                  maxLength={255}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="beneficiary-category">Categoría <span className="field-hint">(opcional)</span></label>
                <input
                  id="beneficiary-category"
                  className="form-control"
                  value={draft.category}
                  onChange={(event) => setDraft((current) => ({ ...current, category: event.target.value }))}
                />
              </div>
              <div className="form-group">
                <label htmlFor="beneficiary-reference">Código de referencia <span className="field-hint">(opcional)</span></label>
                <input
                  id="beneficiary-reference"
                  className="form-control"
                  value={draft.referenceCode}
                  onChange={(event) => setDraft((current) => ({ ...current, referenceCode: event.target.value }))}
                />
              </div>
              <label className="beneficiary-allowed-option">
                <input
                  type="checkbox"
                  checked={draft.allowed}
                  onChange={(event) => setDraft((current) => ({ ...current, allowed: event.target.checked }))}
                />
                Beneficiario permitido
              </label>
              <div className="beneficiary-dialog-actions">
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Guardando...' : dialog === 'edit' ? 'Guardar cambios' : 'Añadir beneficiario'}
                </button>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setDialog(null)}
                  disabled={saving}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}
