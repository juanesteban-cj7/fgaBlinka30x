import { useCallback, useEffect, useState } from 'react'
import { Loader2, Plus, ShieldCheck } from 'lucide-react'
import { api, ApiError } from '../services/api'
import { PaymentPolicy, PolicyDraft, PolicyMutation, RuleCatalogItem } from '../types'
import PolicyParams from '../components/rules/PolicyParams'
import PolicyActionsMatrix from '../components/rules/PolicyActionsMatrix'
import PolicyEditor from '../components/rules/PolicyEditor'
import PolicyVersionsTable from '../components/rules/PolicyVersionsTable'

function draftFromPolicy(source: PaymentPolicy, version: number, catalog: RuleCatalogItem[]): PolicyDraft {
  const configuredActions = new Map(source.rule_actions.map(({ code, action }) => [code, action]))
  return {
    version,
    currency: source.currency,
    max_invoice_amount: String(source.max_invoice_amount),
    approval_threshold: String(source.approval_threshold),
    period_budget: String(source.period_budget),
    period_type: source.period_type,
    period_basis: source.period_basis,
    amount_tolerance_pct: String(source.amount_tolerance_pct),
    min_extraction_confidence: String(source.min_extraction_confidence),
    name_similarity_threshold: String(source.name_similarity_threshold),
    possible_duplicate_date_window_days: String(source.possible_duplicate_date_window_days),
    rule_actions: catalog.map((item) => ({
      code: item.code,
      action: configuredActions.get(item.code) ?? item.default_action,
    })),
    change_reason: '',
    activate: true,
  }
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.detail : error instanceof Error ? error.message : 'Ocurrió un error inesperado.'
}

export default function Rules() {
  const [policy, setPolicy] = useState<PaymentPolicy | null>(null)
  const [catalog, setCatalog] = useState<RuleCatalogItem[]>([])
  const [versions, setVersions] = useState<PaymentPolicy[]>([])
  const [draftSource, setDraftSource] = useState<PaymentPolicy | null>(null)
  const [draft, setDraft] = useState<PolicyDraft | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const canEdit = true

  const refresh = useCallback(async () => {
    const [activePolicy, ruleCatalog, policyVersions] = await Promise.all([
      api.getPolicy(),
      api.getPolicyCatalog(),
      api.listPolicyVersions(),
    ])
    setPolicy(activePolicy)
    setCatalog(ruleCatalog)
    setVersions(policyVersions.sort((left, right) => right.version - left.version))
  }, [])

  useEffect(() => {
    refresh()
      .catch((err: unknown) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [refresh])

  const startDraft = (source: PaymentPolicy) => {
    const nextVersion = Math.max(0, ...versions.map(({ version }) => version)) + 1
    setDraftSource(source)
    setDraft(draftFromPolicy(source, nextVersion, catalog))
    setError(null)
    setNotice(null)
  }

  const closeDraft = () => {
    setDraftSource(null)
    setDraft(null)
    setError(null)
  }

  const saveDraft = async (payload: PolicyMutation) => {
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const created = await api.createPolicy(payload)
      setNotice(`Se creó la versión v${created.version}${payload.activate ? ' y quedó activa' : ''}.`)
      closeDraft()
      try {
        await refresh()
      } catch (refreshError: unknown) {
        setNotice(`Se creó la versión v${created.version}${payload.activate ? ' y quedó activa' : ''}, pero no se pudo actualizar la pantalla: ${errorMessage(refreshError)} Recarga antes de crear otra versión.`)
      }
    } catch (err: unknown) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const activateVersion = async (selected: PaymentPolicy) => {
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      await api.activatePolicy(selected.id)
      await refresh()
      setNotice(`La versión v${selected.version} está activa.`)
    } catch (err: unknown) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="center-panel"><Loader2 size={32} className="spin" aria-label="Cargando reglas y políticas" /></div>
  if (!policy) return <div className="page"><div className="alert alert-error" role="alert" aria-live="assertive">{error ?? 'No se pudo cargar la política.'}</div></div>

  return (
    <div className="page rules-page">
      <div className="rules-page-heading">
        <div className="alert alert-info rules-intro">
          <ShieldCheck size={18} aria-hidden="true" />
          <span><strong>Política activa v{policy.version}.</strong> Las decisiones anteriores conservan la versión con la que fueron evaluadas.</span>
        </div>
        {!draft && (
          <button className="btn btn-primary" type="button" onClick={() => startDraft(policy)}>
            <Plus size={17} /> Crear nueva versión
          </button>
        )}
      </div>

      {notice && <div className="alert alert-success" role="status" aria-live="polite">{notice}</div>}
      {error && !draft && <div className="alert alert-error" role="alert" aria-live="assertive">{error}</div>}

      {draft && draftSource ? (
        <PolicyEditor
          key={`${draftSource.id}-${draft.version}`}
          source={draftSource}
          draft={draft}
          catalog={catalog}
          canEdit={canEdit}
          saving={saving}
          error={error}
          onCancel={closeDraft}
          onSave={saveDraft}
        />
      ) : (
        <>
          <PolicyParams policy={policy} />
          <PolicyActionsMatrix catalog={catalog} actions={policy.rule_actions} editable={false} onChange={() => undefined} />
        </>
      )}

      <PolicyVersionsTable
        policies={versions}
        canEdit={canEdit}
        busy={saving}
        onActivate={activateVersion}
        onDuplicate={startDraft}
      />
    </div>
  )
}
