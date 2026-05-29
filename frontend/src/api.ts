export type UserRole = 'admin' | 'almacen' | 'produccion' | 'despachos'

export type LoginResponse = {
  access_token: string
  token_type: 'bearer'
}

export type Material = {
  id: number
  codigo: string
  nombre: string
  descripcion?: string | null
  unidad: string
  created_at: string
}

export type MaterialLot = {
  id: number
  material_id: number
  codigo_lote: string
  cantidad: number
  cantidad_reservada: number
  cantidad_disponible: number
  almacen_id?: number | null
  locacion_id?: number | null
  costo_unitario?: number | null
  costo_total?: number | null
  fecha_entrada: string
  fecha_caducidad?: string | null
  notas?: string | null
  created_at: string
}

export type Almacen = {
  id: number
  codigo: string
  nombre: string
  tipo?: string | null
  descripcion?: string | null
  activo: boolean
  created_at: string
}

export type Locacion = {
  id: number
  almacen_id: number
  codigo: string
  nombre: string
  descripcion?: string | null
  activo: boolean
  created_at: string
}

export type WorkOrderItem = {
  material_id: number
  cantidad_requerida: number
}

export type WorkOrderItemLotAllocation = {
  material_lot_id: number
  codigo_lote: string
  cantidad: number
}

export type WorkOrderItemDetail = {
  id: number
  work_order_id: number
  material_id: number
  material_codigo: string
  material_nombre: string
  material_unidad: string
  cantidad_requerida: number
  cantidad_asignada: number
  lotes_utilizados: WorkOrderItemLotAllocation[]
}

export type WorkOrderCreate = {
  numero_orden: string
  descripcion?: string
  cantidad_a_producir: number
  notas?: string
  items: WorkOrderItem[]
}

export type WorkOrder = {
  id: number
  numero_orden: string
  descripcion?: string | null
  status: string
  cantidad_a_producir: number
  notas?: string | null
  created_at: string
  updated_at?: string | null
  items?: WorkOrderItemDetail[]
}

export type FinishedProduct = {
  id: number
  codigo: string
  lote_produccion: string
  nombre: string
  descripcion?: string | null
  cantidad_producida: number
  cantidad_disponible: number
  costo_total?: number | null
  work_order_id: number
  created_at: string
}

export type FinishedProductShipment = {
  id: number
  finished_product_id: number
  cantidad: number
  destinatario?: string | null
  documento_envio?: string | null
  observaciones?: string | null
  created_at: string
}

export type WorkOrderProductionSummary = {
  work_order_id: number
  cantidad_a_producir: number
  cantidad_producida: number
  cantidad_disponible: number
  cantidad_pendiente: number
  esta_completa: boolean
}

export type RequisitionItem = {
  id: number
  requisition_id: number
  material_id: number
  quantity: number
  delivered_quantity: number
  notes?: string | null
  created_at: string
}

export type Requisition = {
  id: number
  codigo: string
  work_order_id?: number | null
  requester_area?: string | null
  purpose?: string | null
  is_secondary: boolean
  status: string
  requested_by_user_id?: number | null
  approved_by_user_id?: number | null
  delivered_by_user_id?: number | null
  notes?: string | null
  created_at: string
  approved_at?: string | null
  delivered_at?: string | null
  items: RequisitionItem[]
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

function getToken() {
  return localStorage.getItem('token') ?? ''
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export async function login(username: string, password: string) {
  const body = new URLSearchParams()
  body.set('username', username)
  body.set('password', password)

  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || 'Login fallido')
  }

  return response.json() as Promise<LoginResponse>
}

export async function listMaterials() {
  return request<Material[]>('/materials/')
}

export async function createMaterial(payload: {
  codigo: string
  nombre: string
  descripcion?: string
  unidad?: string
}) {
  return request<Material>('/materials/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function createMaterialLot(materialId: number, payload: {
  codigo_lote: string
  cantidad: number
  almacen_id?: number | null
  locacion_id?: number | null
  costo_unitario?: number | null
  fecha_caducidad?: string | null
  notas?: string | null
}) {
  return request<MaterialLot>(`/materials/${materialId}/lotes`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listAlmacenes() {
  return request<Almacen[]>('/storage/almacenes')
}

export async function createAlmacen(payload: {
  codigo: string
  nombre: string
  tipo?: string | null
  descripcion?: string | null
  activo?: boolean
}) {
  return request<Almacen>('/storage/almacenes', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listLocaciones(almacenId?: number) {
  const suffix = almacenId ? `?almacen_id=${almacenId}` : ''
  return request<Locacion[]>(`/storage/locaciones${suffix}`)
}

export async function createLocacion(payload: {
  almacen_id: number
  codigo: string
  nombre: string
  descripcion?: string | null
  activo?: boolean
}) {
  return request<Locacion>('/storage/locaciones', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listWorkOrders() {
  return request<WorkOrder[]>('/work-orders/')
}

export async function getWorkOrder(workOrderId: number) {
  return request<WorkOrder>(`/work-orders/${workOrderId}`)
}

export async function updateWorkOrderStatus(workOrderId: number, status: string) {
  return request<WorkOrder>(`/work-orders/${workOrderId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  })
}

export async function createWorkOrder(payload: WorkOrderCreate) {
  return request<WorkOrder>('/work-orders/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listLots(materialId: number) {
  return request<MaterialLot[]>(`/materials/${materialId}/lotes`)
}

export async function listRequisitions() {
  return request<Requisition[]>('/requisitions/')
}

export async function createRequisition(payload: {
  work_order_id?: number | null
  requester_area?: string | null
  purpose?: string | null
  is_secondary?: boolean
  notes?: string | null
  items: Array<{ material_id: number; quantity: number; notes?: string | null }>
}) {
  return request<Requisition>('/requisitions/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function approveRequisition(requisitionId: number) {
  return request<Requisition>(`/requisitions/${requisitionId}/approve`, {
    method: 'PUT',
  })
}

export async function deliverRequisition(requisitionId: number) {
  return request<Requisition>(`/requisitions/${requisitionId}/deliver`, {
    method: 'PUT',
  })
}

export async function cancelRequisition(requisitionId: number) {
  return request<Requisition>(`/requisitions/${requisitionId}/cancel`, {
    method: 'PUT',
  })
}

// Finished products
export async function listFinishedProducts() {
  return request<FinishedProduct[]>('/finished-products/')
}

export async function getFinishedProduct(productId: number) {
  return request<FinishedProduct>(`/finished-products/${productId}`)
}

export async function createFinishedProduct(payload: {
  codigo: string
  lote_produccion?: string | null
  nombre: string
  descripcion?: string | null
  cantidad_producida: number
  cantidad_disponible?: number | null
  costo_total?: number | null
  work_order_id: number
}) {
  return request<FinishedProduct>('/finished-products/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function createWorkOrderFinishedProduct(woId: number, payload: {
  codigo: string
  lote_produccion?: string | null
  nombre?: string | null
  descripcion?: string | null
  cantidad_producida: number
  cantidad_disponible?: number | null
  costo_total?: number | null
}) {
  return request<FinishedProduct>(`/work-orders/${woId}/finished-products`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getWorkOrderProductionSummary(woId: number) {
  return request<WorkOrderProductionSummary>(`/work-orders/${woId}/production-summary`)
}

export async function listFinishedProductShipments() {
  return request<FinishedProductShipment[]>('/finished-products/shipments')
}

export async function createFinishedProductShipment(payload: {
  finished_product_id: number
  cantidad: number
  destinatario?: string | null
  documento_envio?: string | null
  observaciones?: string | null
}) {
  return request<FinishedProductShipment>('/finished-products/shipments', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
