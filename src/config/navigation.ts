import type { LucideIcon } from 'lucide-react'
import {
  Activity,
  BarChart3,
  Building2,
  CalendarCheck,
  BadgeCheck,
  Bell,
  BookOpen,
  Boxes,
  CalendarClock,
  CheckSquare,
  ClipboardList,
  CreditCard,
  FileCheck2,
  FolderOpen,
  GitBranch,
  Grid3X3,
  History,
  KeyRound,
  LayoutDashboard,
  Mail,
  MapPinned,
  PackageCheck,
  Receipt,
  ShoppingCart,
  Truck,
  Users,
  UserCog,
} from 'lucide-react'

/**
 * Navigation is driven by permissions (any-of), never by role names.
 * The same `permissions` list is used by the route guard, so hiding a menu item
 * and blocking a typed URL are always consistent.
 */
export interface NavItem {
  key: string
  label: string
  to: string
  icon: LucideIcon
  /** The user needs at least one of these permissions. */
  permissions: string[]
  /** Optional key used by the shell to render a count badge. */
  badge?: 'tasks' | 'notifications' | 'approvals' | 'email' | 'applications' | 'myApplications'
}

export interface NavSection {
  title: string
  items: NavItem[]
}

const ORDER_VIEW = ['order.view_own', 'order.view_assigned', 'order.view_all']

export const NAVIGATION: NavSection[] = [
  {
    title: 'Workspace',
    items: [
      { key: 'overview', label: 'Overview', to: '/app', icon: LayoutDashboard, permissions: ['dashboard.view'] },
      { key: 'tasks', label: 'My Tasks', to: '/app/tasks', icon: CheckSquare, permissions: ['task.view'], badge: 'tasks' },
      { key: 'notifications', label: 'Notifications', to: '/app/notifications', icon: Bell, permissions: ['notification.view'], badge: 'notifications' },
    ],
  },
  {
    title: 'Customer Portal',
    items: [
      { key: 'account', label: 'My Customer Profile', to: '/app/account', icon: Building2, permissions: ['customer.view_own'] },
      { key: 'my-applications', label: 'My Applications', to: '/app/my-applications', icon: BadgeCheck, permissions: ['application.view_own'], badge: 'myApplications' },
    ],
  },
  {
    title: 'Customer Management',
    items: [
      { key: 'customers', label: 'Customers', to: '/app/customers', icon: Users, permissions: ['customer.view_assigned', 'customer.view_all'] },
      { key: 'applications', label: 'Customer Onboarding', to: '/app/applications', icon: FileCheck2, permissions: ['application.view_assigned', 'application.view_territory', 'application.view_all'], badge: 'applications' },
      { key: 'activities', label: 'Visits & Activities', to: '/app/activities', icon: CalendarCheck, permissions: ['activity.view_assigned', 'activity.view_all'] },
      { key: 'performance', label: 'Territory Performance', to: '/app/performance', icon: BarChart3, permissions: ['performance.view_assigned', 'performance.view_all'] },
    ],
  },
  {
    title: 'Sales',
    items: [
      { key: 'catalog', label: 'Product Catalog', to: '/app/catalog', icon: BookOpen, permissions: ['catalog.view'] },
      { key: 'requests', label: 'Sales Requests', to: '/app/requests', icon: ClipboardList, permissions: ['order.create', 'order.create_on_behalf', 'order.approval_monitor'] },
      { key: 'approvals', label: 'Request Approvals', to: '/app/approvals', icon: GitBranch, permissions: ['order.approve', 'order.reject', 'order.approval_monitor', 'order.sap_submit'], badge: 'approvals' },
      { key: 'orders', label: 'Orders', to: '/app/orders', icon: ShoppingCart, permissions: ORDER_VIEW },
      { key: 'invoices', label: 'Proforma Invoices', to: '/app/invoices', icon: Receipt, permissions: ['invoice.view'] },
      { key: 'payments', label: 'Payments', to: '/app/payments', icon: CreditCard, permissions: ['payment.view'] },
    ],
  },
  {
    title: 'Fulfillment',
    items: [
      { key: 'shipments', label: 'Shipment Tracking', to: '/app/shipments', icon: Truck, permissions: ['shipment.view'] },
      { key: 'collection', label: 'Collection Readiness', to: '/app/collection', icon: PackageCheck, permissions: ['collection.view'] },
      { key: 'documents', label: 'Documents', to: '/app/documents', icon: FolderOpen, permissions: ['document.view'] },
    ],
  },
  {
    title: 'Communication',
    items: [
      { key: 'email', label: 'Email Conversations', to: '/app/email', icon: Mail, permissions: ['email.view'], badge: 'email' },
      { key: 'followups', label: 'Follow-ups', to: '/app/follow-ups', icon: CalendarClock, permissions: ['followup.manage'] },
    ],
  },
  {
    title: 'Administration',
    items: [
      { key: 'users', label: 'Users', to: '/app/admin/users', icon: UserCog, permissions: ['user.view'] },
      { key: 'roles', label: 'Roles & Permissions', to: '/app/admin/roles', icon: KeyRound, permissions: ['role.view'] },
      { key: 'authorization', label: 'Authorization Matrix', to: '/app/admin/authorization', icon: Grid3X3, permissions: ['role.view'] },
      { key: 'territories', label: 'Territory Management', to: '/app/admin/territories', icon: MapPinned, permissions: ['territory.view'] },
      { key: 'workflow', label: 'Workflow Rules', to: '/app/admin/workflow', icon: Boxes, permissions: ['workflow.view'] },
      { key: 'integration', label: 'Integration Monitor', to: '/app/admin/integration', icon: Activity, permissions: ['integration.view'] },
      { key: 'audit', label: 'Audit Trail', to: '/app/admin/audit', icon: History, permissions: ['audit.view'] },
    ],
  },
]

export function navigationFor(can: (p: string) => boolean): NavSection[] {
  return NAVIGATION.map((s) => ({ ...s, items: s.items.filter((i) => i.permissions.some(can)) })).filter((s) => s.items.length > 0)
}

/** Flattened lookup used for breadcrumbs and route guards. */
export const ALL_NAV_ITEMS = NAVIGATION.flatMap((s) => s.items)
export const navPermissions = (key: string) => ALL_NAV_ITEMS.find((i) => i.key === key)?.permissions ?? []

/** First page the user may open — used for role-aware landing after sign-in. */
export function landingPathFor(can: (p: string) => boolean) {
  if (!can('dashboard.view') && can('application.view_own')) return '/app/my-applications'
  return navigationFor(can)[0]?.items[0]?.to ?? '/app/no-access'
}
