import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShoppingCart } from 'lucide-react'
import { requestTotal, useLookups, useStore } from '@/app/store'
import { useScope } from '@/hooks/useScope'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/Badge'
import { EmptyState, ProgressBar } from '@/components/ui/misc'
import { DataTable, type Column } from '@/components/data-display/DataTable'
import { FilterBar, FilterSelect, SearchInput } from '@/components/data-display/FilterBar'
import { SHIPMENT_FLOW } from '@/types/domain'
import { date, money } from '@/utils/format'
import type { SalesOrderRequest } from '@/types/domain'

const ORDER_STATUSES = ['Approved', 'Awaiting Payment', 'Payment Verified', 'In Fulfillment', 'Ready for Collection', 'Collected'] as const

export default function OrdersPage() {
  const scope = useScope()
  const { user } = useStore()
  const lookups = useLookups()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')

  const orders = useMemo(
    () =>
      scope.requests.filter(
        (r) =>
          (ORDER_STATUSES as readonly string[]).includes(r.status) &&
          (!status || r.status === status) &&
          (!q || `${r.ref} ${r.externalRef ?? ''} ${lookups.customer(r.customerId)?.name}`.toLowerCase().includes(q.toLowerCase())),
      ),
    [scope.requests, q, status, lookups],
  )

  const progress = (r: SalesOrderRequest) => {
    const s = lookups.shipment(r.shipmentId)
    return s ? ((SHIPMENT_FLOW.indexOf(s.status) + 1) / SHIPMENT_FLOW.length) * 100 : 10
  }
  const approvedAt = (r: SalesOrderRequest) => r.approvalSteps.at(-1)?.actedAt ?? r.updatedAt

  const columns: Column<SalesOrderRequest>[] = [
    {
      key: 'ref', header: 'Order', primary: true, sortValue: (r) => r.ref,
      cell: (r) => (
        <span>
          <span className="block font-mono text-[12px] font-semibold">{r.ref}</span>
          <span className="block text-[11px] text-muted">{r.sap?.documentNumber ?? r.sap?.status ?? 'SAP document pending'}</span>
        </span>
      ),
    },
    ...(user.kind !== 'external' ? [{ key: 'customer', header: 'Customer', sortValue: (r: SalesOrderRequest) => lookups.customer(r.customerId)?.name ?? '', cell: (r: SalesOrderRequest) => <span className="font-medium">{lookups.customer(r.customerId)?.name}</span> } as Column<SalesOrderRequest>] : []),
    { key: 'approved', header: 'Approved', sortValue: approvedAt, cell: (r) => date(approvedAt(r)) },
    { key: 'value', header: 'Value', align: 'right', sortValue: requestTotal, cell: (r) => <span className="font-medium tabular">{money(requestTotal(r), r.currency)}</span> },
    { key: 'payment', header: 'Proforma', hideOnMobile: true, cell: (r) => { const i = lookups.invoice(r.invoiceId); return i ? <StatusBadge status={i.status} /> : <span className="text-xs text-muted">To be issued</span> } },
    {
      key: 'progress', header: 'Fulfilment', sortValue: progress,
      cell: (r) => (
        <span className="block min-w-36">
          <span className="mb-1 block text-xs text-muted">{lookups.shipment(r.shipmentId)?.status ?? 'Approved'}</span>
          <ProgressBar value={progress(r)} tone={r.status === 'Collected' ? 'success' : 'primary'} />
        </span>
      ),
    },
    { key: 'status', header: 'Status', sortValue: (r) => r.status, cell: (r) => <StatusBadge status={r.status} /> },
  ]

  return (
    <>
      <PageHeader title="Orders" description="Approved requests and their journey through payment, warehouse preparation and collection." breadcrumbs={[{ label: 'Sales' }, { label: 'Orders' }]} />
      <Card>
        <FilterBar active={!!(q || status)} onReset={() => { setQ(''); setStatus('') }}>
          <SearchInput value={q} onChange={setQ} placeholder="Order, SAP doc or customer…" className="w-full sm:w-64" />
          <FilterSelect label="Status" value={status} onChange={setStatus} options={ORDER_STATUSES.map((s) => ({ value: s, label: s }))} />
        </FilterBar>
        <DataTable
          rows={orders}
          columns={columns}
          rowKey={(r) => r.id}
          onRowClick={(r) => navigate(`/app/requests/${r.id}`)}
          initialSort={{ key: 'approved', dir: 'desc' }}
          caption="Orders"
          empty={<EmptyState icon={<ShoppingCart className="size-5" />} title="No orders yet" description="Requests appear here once fully approved." />}
        />
      </Card>
    </>
  )
}
