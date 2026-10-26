import { useState } from 'react'
import { CloudUpload, FlaskConical, Loader2, RefreshCw } from 'lucide-react'
import { canSubmitToSap, useLookups, useStore } from '@/app/store'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge, StatusBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Notice } from '@/components/ui/misc'
import { useToast } from '@/components/ui/Toast'
import { SAP_MODE, SAP_MODE_LABEL } from '@/services'
import { dateTime } from '@/utils/format'
import type { SalesOrderRequest } from '@/types/domain'

/** Customer-facing wording: no error codes or technical messages (requirements §13). */
const CUSTOMER_TEXT: Record<string, string> = {
  'Pending SAP Submission': 'Approved — being forwarded for order processing.',
  'SAP Submission Failed': 'Approved — order processing is delayed. Our team has been notified; no action is needed from you.',
  'Submitted to SAP': 'Accepted for processing. Some quantities are not yet confirmed.',
  'SAP Confirmed': 'Accepted for processing. Quantities confirmed.',
}

export function SapSubmissionPanel({ request: r }: { request: SalesOrderRequest }) {
  const { state, user, submitToSap } = useStore()
  const lookups = useLookups()
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  if (!r.sap) return null
  const sap = r.sap
  const external = user.kind === 'external'
  const allowed = canSubmitToSap(state, user, r)
  const inFlight = busy || sap.inFlight

  const run = async () => {
    setBusy(true)
    const res = await submitToSap(r.id)
    setBusy(false)
    if (!res.ok) return toast.error('SAP submission not started', res.error)
    if (res.outcome === 'failed') toast.error('SAP submission failed', res.message)
    else toast.success(res.outcome === 'confirmed' ? 'Accepted by SAP (development mock)' : 'Accepted with partial confirmation (development mock)', res.message)
  }

  if (external)
    return (
      <Card>
        <CardHeader title="Order processing" actions={<StatusBadge status={sap.status === 'SAP Submission Failed' ? 'Pending SAP Submission' : sap.status} />} />
        <CardBody className="space-y-2 text-[13px]">
          <p>{CUSTOMER_TEXT[sap.status]}</p>
          {sap.documentNumber && <p className="text-xs text-muted">Order reference: <span className="font-mono">{sap.documentNumber}</span>{SAP_MODE === 'mock' && ' (test reference)'}</p>}
        </CardBody>
      </Card>
    )

  return (
    <Card>
      <CardHeader
        title="SAP submission"
        description="Separate from internal approval"
        actions={<StatusBadge status={inFlight ? 'Submitting…' : sap.status} />}
      />
      <CardBody className="space-y-3 text-[13px]">
        <p className="flex items-center gap-1.5 text-xs text-muted"><FlaskConical className="size-3.5 shrink-0" />{SAP_MODE_LABEL}</p>
        {sap.documentNumber && (
          <div className="flex justify-between"><span className="text-muted">Sales document</span><span className="font-mono">{sap.documentNumber}</span></div>
        )}
        {sap.status === 'SAP Submission Failed' && sap.errorMessage && (
          <Notice tone="danger" title={`Last attempt failed${sap.errorCode ? ` · ${sap.errorCode}` : ''}`}>{sap.errorMessage}</Notice>
        )}
        {sap.status === 'Pending SAP Submission' && !inFlight && <p className="text-muted">Internally approved. Not yet sent to SAP — no SAP document exists.</p>}
        {allowed && (
          <Button size="sm" icon={inFlight ? <Loader2 className="size-4 animate-spin" /> : sap.attempts.length ? <RefreshCw className="size-4" /> : <CloudUpload className="size-4" />} disabled={inFlight} onClick={run}>
            {inFlight ? 'Submitting…' : sap.attempts.length ? 'Retry SAP submission' : 'Submit to SAP'}
          </Button>
        )}
        {!allowed && !inFlight && (sap.status === 'Pending SAP Submission' || sap.status === 'SAP Submission Failed') && (
          <p className="text-xs text-muted">Waiting for a Sales Representative, Head of Sales or Operations user to submit.</p>
        )}
        {sap.attempts.length > 0 && (
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted">Attempts</p>
            <ol className="space-y-1.5">
              {[...sap.attempts].reverse().map((a, i) => (
                <li key={i} className="rounded-md border border-line px-2.5 py-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <Badge tone={a.outcome === 'failed' ? 'danger' : a.outcome === 'confirmed' ? 'success' : 'info'}>{a.outcome === 'failed' ? 'Failed' : a.outcome === 'confirmed' ? 'Confirmed' : 'Partially confirmed'}</Badge>
                    <span className="text-[11px] text-muted">{dateTime(a.at)}</span>
                  </div>
                  <p className="mt-1 text-xs">{a.message}</p>
                  <p className="text-[11px] text-muted">by {lookups.user(a.byId)?.name ?? 'System'} · {a.mode === 'mock' ? 'development mock' : 'live'}</p>
                </li>
              ))}
            </ol>
          </div>
        )}
      </CardBody>
    </Card>
  )
}
