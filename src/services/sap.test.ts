/** SAP development-mock contract: approval ≠ submission; failures are reported, never silently "successful". */
import { describe, expect, it } from 'vitest'
import { mockServices, sapMockControls } from './mock'
import { displayStatus } from '@/utils/requestStatus'
import { salesOrderRequests } from '@/data/transactions'

const payload = (over: Partial<Parameters<typeof mockServices.sap.submitSalesOrder>[0]> = {}) => ({
  requestRef: 'SOR-TEST-0001',
  soldTo: 'CUST-10021',
  currency: 'AED' as const,
  requestedDeliveryDate: '2026-11-30',
  items: [{ lineNo: 10, productId: 'p-01', sku: 'MV-EDP-100-AMB', quantity: 12, uom: 'EA', unitPrice: 250 }],
  ...over,
})

describe('SAP development mock', () => {
  it('declares itself as mock and issues clearly marked document numbers', async () => {
    expect(mockServices.sap.mode).toBe('mock')
    const r = await mockServices.sap.submitSalesOrder(payload())
    expect(r.ok && r.documentNumber.startsWith('MOCK-SO-')).toBe(true)
    expect(r.ok && r.fullyConfirmed).toBe(true)
  })
  it('only partially confirms lines above available stock', async () => {
    const r = await mockServices.sap.submitSalesOrder(payload({ items: [{ lineNo: 10, productId: 'p-11', sku: 'LN-EDP-90-ECL', quantity: 120, uom: 'EA', unitPrice: 300 }] }))
    expect(r).toMatchObject({ ok: true, fullyConfirmed: false, confirmedQty: { 'p-11': 85 } })
  })
  it('reports a transient timeout once, then succeeds on retry', async () => {
    sapMockControls.simulateTimeoutOnce.add('SOR-TEST-0002')
    const first = await mockServices.sap.submitSalesOrder(payload({ requestRef: 'SOR-TEST-0002' }))
    expect(first).toMatchObject({ ok: false, errorCode: 'GW-TIMEOUT', retryable: true })
    const second = await mockServices.sap.submitSalesOrder(payload({ requestRef: 'SOR-TEST-0002' }))
    expect(second.ok).toBe(true)
  })
  it('rejects an empty payload', async () => {
    expect(await mockServices.sap.submitSalesOrder(payload({ items: [] }))).toMatchObject({ ok: false, errorCode: 'VAL-ITEMS' })
  })
})

describe('seeded request states keep approval and SAP distinct', () => {
  it('no request is in SAP without being internally approved; r-127 failed and has no document', () => {
    for (const r of salesOrderRequests) if (r.sap) expect(['Approved', 'Awaiting Payment', 'Payment Verified', 'In Fulfillment', 'Ready for Collection', 'Collected']).toContain(r.status)
    const r127 = salesOrderRequests.find((r) => r.id === 'r-127')!
    expect(r127.sap?.status).toBe('SAP Submission Failed')
    expect(r127.externalRef).toBeUndefined()
    expect(displayStatus(r127)).toBe('SAP Submission Failed')
    for (const r of salesOrderRequests.filter((x) => x.status === 'Pending Approval')) expect(r.sap).toBeUndefined()
  })
})
