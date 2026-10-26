/**
 * Mock implementations of the service contracts.
 * They read seeded data, add a small artificial latency and never leave the browser.
 * Swap `services` in ./index.ts for a real implementation later.
 */
import type { TradeFlowServices } from './contracts'
import { customers } from '@/data/customers'
import { products } from '@/data/catalog'
import { salesOrderRequests, invoices, payments, shipments } from '@/data/transactions'
import { emailThreads } from '@/data/communications'
import { fromUsd, roundMoney } from '@/utils/fx'
import { uid } from '@/utils/time'

const delay = <T,>(value: T, ms = 450 + Math.random() * 350) => new Promise<T>((r) => setTimeout(() => r(value), ms))

let reqSeq = 146
let sapSeq = 7000

/**
 * DEVELOPMENT-MODE SAP mock. Deterministic so the demo is repeatable:
 *  - sold-to on credit hold (customer status "On Hold" / "Blocked") → failed, not retryable until resolved
 *  - request refs listed in `simulateTimeoutOnce` fail once with a gateway timeout, then succeed on retry
 *  - otherwise the order is accepted; lines above available stock are only partially confirmed.
 * Document numbers are prefixed MOCK- so they can never be mistaken for real SAP documents.
 */
const timedOutOnce = new Set<string>()
export const sapMockControls = {
  stockOf: (productId: string) => products.find((p) => p.id === productId)?.availableQty ?? 0,
  blockedSoldTo: (soldTo: string) => customers.some((c) => c.code === soldTo && (c.status === 'On Hold' || c.status === 'Blocked')),
  simulateTimeoutOnce: new Set<string>(), // add a request ref here to demo a transient timeout
}

export const mockServices: TradeFlowServices = {
  customers: {
    lookupCustomers: (q) => delay(customers.filter((c) => `${c.name} ${c.code}`.toLowerCase().includes(q.toLowerCase()))),
    getCustomer: (id) => delay(customers.find((c) => c.id === id)),
  },
  catalog: {
    listProducts: (q = {}) =>
      delay(
        products.filter(
          (p) =>
            (!q.search || `${p.name} ${p.sku}`.toLowerCase().includes(q.search.toLowerCase())) &&
            (!q.brandIds?.length || q.brandIds.includes(p.brandId)) &&
            (!q.categories?.length || q.categories.includes(p.category)),
        ),
      ),
    getPriceAndAvailability: (ids, customerId) => {
      const currency = customers.find((c) => c.id === customerId)?.currency ?? 'USD'
      return delay(
        products
          .filter((p) => ids.includes(p.id))
          .map((p) => ({ productId: p.id, currency, unitPrice: roundMoney(fromUsd(p.unitPriceUsd, currency)), availableQty: p.availableQty, stockStatus: p.stockStatus, source: 'mock' as const })),
        600,
      )
    },
  },
  orders: {
    submitRequest: () =>
      delay({ id: uid('r'), ref: `SOR-${new Date().getFullYear()}-${String(reqSeq++).padStart(4, '0')}`, receivedAt: new Date().toISOString() }, 800),
    getApprovalStatus: (id) => delay(salesOrderRequests.find((r) => r.id === id)?.approvalSteps ?? []),
  },
  finance: {
    getProformaInvoice: (id) => delay(invoices.find((i) => i.id === id)),
    getPaymentStatus: (invoiceId) => delay(payments.find((p) => p.invoiceId === invoiceId)),
  },
  logistics: {
    getShipmentStatus: (id) => delay(shipments.find((s) => s.id === id)),
  },
  communications: {
    listConversations: (customerId) => delay(emailThreads.filter((t) => !customerId || t.customerId === customerId)),
  },
  sap: {
    mode: 'mock',
    submitSalesOrder: (payload) => {
      if (sapMockControls.simulateTimeoutOnce.has(payload.requestRef) && !timedOutOnce.has(payload.requestRef)) {
        timedOutOnce.add(payload.requestRef)
        return delay({ ok: false as const, errorCode: 'GW-TIMEOUT', message: 'Gateway timeout after 30 s (development mock). Safe to retry.', retryable: true }, 1100)
      }
      if (sapMockControls.blockedSoldTo(payload.soldTo))
        return delay({ ok: false as const, errorCode: 'CREDIT-BLOCK', message: `Sold-to ${payload.soldTo} is on credit/delivery block (development mock). Resolve the customer status, then retry.`, retryable: true }, 900)
      if (!payload.items.length || payload.items.some((i) => i.quantity <= 0))
        return delay({ ok: false as const, errorCode: 'VAL-ITEMS', message: 'Payload rejected: no valid items (development mock).', retryable: false }, 500)
      const confirmedQty: Record<string, number> = {}
      let full = true
      for (const i of payload.items) {
        const c = Math.max(0, Math.min(i.quantity, sapMockControls.stockOf(i.productId)))
        confirmedQty[i.productId] = c
        if (c < i.quantity) full = false
      }
      return delay(
        {
          ok: true as const,
          documentNumber: `MOCK-SO-${++sapSeq}`,
          confirmedQty,
          fullyConfirmed: full,
          message: full ? 'Order accepted; all schedule lines confirmed (development mock).' : 'Order accepted; some lines only partially confirmed against available stock (development mock).',
        },
        1200,
      )
    },
  },
  integration: {
    retry: (event) =>
      delay(
        {
          ...event,
          attempts: event.attempts + 1,
          at: new Date().toISOString(),
          // Deterministic demo outcome: timeouts recover, validation errors keep failing.
          status: event.errorCode === 'BP-VAL-014' ? ('Failed' as const) : ('Synced' as const),
          message:
            event.errorCode === 'BP-VAL-014'
              ? 'Retry failed: tax number still rejected. Correct the customer’s master data (SAP customer master) and retry (simulated).'
              : 'Retry succeeded in mock environment.',
          errorCode: event.errorCode === 'BP-VAL-014' ? event.errorCode : undefined,
        },
        1200,
      ),
  },
}
