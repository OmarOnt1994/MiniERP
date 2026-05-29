import { useEffect, useMemo, useState } from 'react'
import {
  createAlmacen,
  createLocacion,
  createMaterial,
  createMaterialLot,
  createRequisition,
  approveRequisition,
  cancelRequisition,
  deliverRequisition,
  createWorkOrder,
  listAlmacenes,
  listLocaciones,
  listMaterials,
  listLots,
  listRequisitions,
  listWorkOrders,
  updateWorkOrderStatus,
  login,
  listFinishedProducts,
  getFinishedProduct,
  listFinishedProductShipments,
  createFinishedProductShipment,
  createWorkOrderFinishedProduct,
  getWorkOrderProductionSummary,
  type Almacen,
  type Locacion,
  type Material,
  type MaterialLot,
  type Requisition,
  type WorkOrder,
  type FinishedProduct,
  type FinishedProductShipment,
  type WorkOrderProductionSummary,
} from './api'

type View = 'login' | 'storage' | 'materials' | 'material-intake' | 'material-search' | 'requisitions' | 'work-orders' | 'work-order-detail' | 'production-entry' | 'finished-products'
  | 'finished-product-detail'

const emptyMaterialForm = {
  codigo: '',
  nombre: '',
  descripcion: '',
  unidad: 'pieza',
}

const emptyLotForm = {
  material_id: '',
  codigo_lote: '',
  cantidad: '',
  almacen_id: '',
  locacion_id: '',
  costo_unitario: '',
  fecha_caducidad: '',
  notas: '',
}

const emptyAlmacenForm = {
  codigo: '',
  nombre: '',
  tipo: '',
  descripcion: '',
}

const emptyLocacionForm = {
  almacen_id: '',
  codigo: '',
  nombre: '',
  descripcion: '',
}

const emptyWoForm = {
  numero_orden: '',
  descripcion: '',
  cantidad_a_producir: '',
  notas: '',
  // use `woItems` for multiple materials
}

const emptyWoItem = {
  material_id: '',
  cantidad_requerida: '',
}

const emptyRequisitionForm = {
  work_order_id: '',
  requester_area: '',
  purpose: '',
  notes: '',
  material_id: '',
  quantity: '',
}

export default function App() {
  const [token, setToken] = useState<string>(() => localStorage.getItem('token') ?? '')
  const [view, setView] = useState<View>(() => (localStorage.getItem('token') ? 'storage' : 'login'))
  const [email, setEmail] = useState('admin@mini.erp')
  const [password, setPassword] = useState('1234')
  const [message, setMessage] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [materials, setMaterials] = useState<Material[]>([])
  const [materialSearch, setMaterialSearch] = useState('')
  const [materialSearchResult, setMaterialSearchResult] = useState<Material | null>(null)
  const [materialLots, setMaterialLots] = useState<MaterialLot[]>([])
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([])
  const [selectedWorkOrderId, setSelectedWorkOrderId] = useState<number | null>(null)
  const [workOrderSearch, setWorkOrderSearch] = useState('')
  const [selectedFinishedProductId, setSelectedFinishedProductId] = useState<number | null>(null)
  const [requisitions, setRequisitions] = useState<Requisition[]>([])
  const [almacenes, setAlmacenes] = useState<Almacen[]>([])
  const [locaciones, setLocaciones] = useState<Locacion[]>([])
  const [materialForm, setMaterialForm] = useState(emptyMaterialForm)
  const [lotForm, setLotForm] = useState(emptyLotForm)
  const [almacenForm, setAlmacenForm] = useState(emptyAlmacenForm)
  const [locacionForm, setLocacionForm] = useState(emptyLocacionForm)
  const [requisitionForm, setRequisitionForm] = useState(emptyRequisitionForm)
  const [woForm, setWoForm] = useState(emptyWoForm)
  const [woItems, setWoItems] = useState<Array<{ material_id: string; cantidad_requerida: string }>>(() => [{ ...emptyWoItem }])
  const [loading, setLoading] = useState(false)
  const [finishedProducts, setFinishedProducts] = useState<FinishedProduct[]>([])
  const [shipments, setShipments] = useState<FinishedProductShipment[]>([])
  const [selectedFinishedProductDetail, setSelectedFinishedProductDetail] = useState<FinishedProduct | null>(null)
  const [productionForm, setProductionForm] = useState({ work_order_id: '', codigo: '', lote_produccion: '', nombre: '', descripcion: '', cantidad_producida: '', cantidad_disponible: '', costo_total: '' })
  const [shipmentForm, setShipmentForm] = useState({ finished_product_id: '', cantidad: '', destinatario: '', documento_envio: '', observaciones: '' })
  const [closeForm, setCloseForm] = useState({ work_order_id: '' })
  const [productionSummary, setProductionSummary] = useState<WorkOrderProductionSummary | null>(null)
  const selectedWorkOrder = useMemo(
    () => workOrders.find((wo) => wo.id === selectedWorkOrderId) ?? null,
    [workOrders, selectedWorkOrderId],
  )
  const selectedWorkOrderFinishedProducts = useMemo(
    () => finishedProducts.filter((fp) => fp.work_order_id === selectedWorkOrderId),
    [finishedProducts, selectedWorkOrderId],
  )
  const selectedFinishedProduct = useMemo(
    () => selectedFinishedProductDetail ?? finishedProducts.find((fp) => fp.id === selectedFinishedProductId) ?? null,
    [finishedProducts, selectedFinishedProductDetail, selectedFinishedProductId],
  )
  const selectedFinishedProductWorkOrder = useMemo(
    () => (selectedFinishedProduct ? workOrders.find((wo) => wo.id === selectedFinishedProduct.work_order_id) ?? null : null),
    [workOrders, selectedFinishedProduct],
  )
  const selectedFinishedProductShipments = useMemo(
    () => shipments.filter((shipment) => shipment.finished_product_id === selectedFinishedProductId),
    [shipments, selectedFinishedProductId],
  )
  const searchedWorkOrder = useMemo(() => {
    const query = workOrderSearch.trim().toLowerCase()
    if (!query) return null

    const numericId = Number(query)
    if (!Number.isNaN(numericId)) {
      return workOrders.find((wo) => wo.id === numericId) ?? null
    }

    return workOrders.find((wo) => wo.numero_orden.toLowerCase().includes(query)) ?? null
  }, [workOrderSearch, workOrders])

  const locacionesPorAlmacen = useMemo(() => {
    const grouped = new Map<number, Locacion[]>()
    for (const locacion of locaciones) {
      const current = grouped.get(locacion.almacen_id) ?? []
      current.push(locacion)
      grouped.set(locacion.almacen_id, current)
    }
    return grouped
  }, [locaciones])

  const authReady = useMemo(() => Boolean(token), [token])

  useEffect(() => {
    if (!token) return
    void refreshData()
  }, [token])

  useEffect(() => {
    if (!productionForm.work_order_id) {
      setProductionSummary(null)
      return
    }
    void refreshProductionSummary(Number(productionForm.work_order_id))
  }, [productionForm.work_order_id])

  useEffect(() => {
    if (!closeForm.work_order_id) {
      return
    }
    void refreshProductionSummary(Number(closeForm.work_order_id))
  }, [closeForm.work_order_id])

  async function refreshData() {
    try {
      setError('')
      const [materialsResponse, workOrdersResponse, requisitionsResponse, almacenesResponse, locacionesResponse, finishedResponse, shipmentsResponse] = await Promise.all([
        listMaterials(),
        listWorkOrders().catch(() => []),
        listRequisitions().catch(() => []),
        listAlmacenes().catch(() => []),
        listLocaciones().catch(() => []),
        listFinishedProducts().catch(() => []),
        listFinishedProductShipments().catch(() => []),
      ])
      setMaterials(materialsResponse)
      setWorkOrders(workOrdersResponse)
      setRequisitions(requisitionsResponse)
      setAlmacenes(almacenesResponse)
      setLocaciones(locacionesResponse)
      setFinishedProducts(finishedResponse)
      setShipments(shipmentsResponse)
      if (selectedWorkOrderId && !workOrdersResponse.some((wo) => wo.id === selectedWorkOrderId)) {
        setSelectedWorkOrderId(null)
      }
      if (selectedFinishedProductId && !finishedResponse.some((fp) => fp.id === selectedFinishedProductId)) {
        setSelectedFinishedProductId(null)
        setSelectedFinishedProductDetail(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error cargando datos')
    }
  }

  async function handleLogin(event: React.FormEvent) {
    event.preventDefault()
    try {
      setLoading(true)
      setError('')
      const response = await login(email, password)
      localStorage.setItem('token', response.access_token)
      setToken(response.access_token)
      setView('storage')
      setMessage('Sesión iniciada correctamente')
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateMaterial(event: React.FormEvent) {
    event.preventDefault()
    try {
      setLoading(true)
      setError('')
      await createMaterial({
        codigo: materialForm.codigo,
        nombre: materialForm.nombre,
        descripcion: materialForm.descripcion || undefined,
        unidad: materialForm.unidad,
      })
      setMessage('Material creado correctamente')
      setMaterialForm(emptyMaterialForm)
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear el material')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateAlmacen(event: React.FormEvent) {
    event.preventDefault()
    try {
      setLoading(true)
      setError('')
      await createAlmacen({
        codigo: almacenForm.codigo,
        nombre: almacenForm.nombre,
        tipo: almacenForm.tipo || null,
        descripcion: almacenForm.descripcion || null,
        activo: true,
      })
      setMessage('Almacen creado correctamente')
      setAlmacenForm(emptyAlmacenForm)
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear el almacen')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateLocacion(event: React.FormEvent) {
    event.preventDefault()
    try {
      setLoading(true)
      setError('')
      await createLocacion({
        almacen_id: Number(locacionForm.almacen_id),
        codigo: locacionForm.codigo,
        nombre: locacionForm.nombre,
        descripcion: locacionForm.descripcion || null,
        activo: true,
      })
      setMessage('Locacion creada correctamente')
      setLocacionForm(emptyLocacionForm)
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear la locacion')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateLot(event: React.FormEvent) {
    event.preventDefault()
    try {
      if (!lotForm.almacen_id) {
        throw new Error('Debes seleccionar un almacen antes de registrar la entrada')
      }
      setLoading(true)
      setError('')
      await createMaterialLot(Number(lotForm.material_id), {
        codigo_lote: lotForm.codigo_lote,
        cantidad: Number(lotForm.cantidad),
        almacen_id: Number(lotForm.almacen_id),
        locacion_id: lotForm.locacion_id ? Number(lotForm.locacion_id) : null,
        costo_unitario: lotForm.costo_unitario ? Number(lotForm.costo_unitario) : null,
        fecha_caducidad: lotForm.fecha_caducidad || null,
        notas: lotForm.notas || null,
      })
      setMessage('Entrada registrada correctamente')
      setLotForm(emptyLotForm)
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo registrar la entrada')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateWO(event: React.FormEvent) {
    event.preventDefault()
    try {
      setLoading(true)
      setError('')
      const itemsPayload = woItems.map((it) => ({
        material_id: Number(it.material_id),
        cantidad_requerida: Number(it.cantidad_requerida),
      }))

      await createWorkOrder({
        numero_orden: woForm.numero_orden,
        descripcion: woForm.descripcion || undefined,
        cantidad_a_producir: Number(woForm.cantidad_a_producir),
        notas: woForm.notas || undefined,
        items: itemsPayload,
      })
      setMessage('Work Order creada correctamente')
      setWoForm(emptyWoForm)
      setWoItems([{ ...emptyWoItem }])
      setView('work-orders')
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear la WO')
    } finally {
      setLoading(false)
    }
  }

  function handleAddWoItem() {
    setWoItems((prev) => [...prev, { ...emptyWoItem }])
  }

  function handleRemoveWoItem(index: number) {
    setWoItems((prev) => prev.filter((_, i) => i !== index))
  }

  function handleUpdateWoItem(index: number, field: string, value: string) {
    setWoItems((prev) => prev.map((it, i) => (i === index ? { ...it, [field]: value } : it)))
  }

  async function handleUpdateWOStatus(woId: number, status: string) {
    try {
      setLoading(true)
      setError('')
      await updateWorkOrderStatus(woId, status)
      setMessage(status === 'surtido' ? 'WO marcada como surtida' : `WO status actualizado a ${status}`)
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo actualizar la WO')
    } finally {
      setLoading(false)
    }
  }

  function handleSelectWorkOrder(woId: number) {
    setSelectedWorkOrderId(woId)
    setView('work-order-detail')
  }

  function handleOpenWorkOrderDetail(woId: number) {
    setSelectedWorkOrderId(woId)
    setWorkOrderSearch(String(woId))
    setView('work-order-detail')
  }

  function handleSearchWorkOrder(event: React.FormEvent) {
    event.preventDefault()
    if (searchedWorkOrder) {
      setSelectedWorkOrderId(searchedWorkOrder.id)
      setView('work-order-detail')
    } else {
      setError('No se encontró una WO con ese id o código')
    }
  }

  async function handleSearchMaterial(event: React.FormEvent) {
    event.preventDefault()
    const query = materialSearch.trim().toLowerCase()
    if (!query) {
      setError('Ingresa un id o código de material')
      return
    }

    const numericId = Number(query)
    let found: Material | undefined
    if (!Number.isNaN(numericId)) {
      found = materials.find((m) => m.id === numericId)
    }
    if (!found) {
      found = materials.find((m) => m.codigo.toLowerCase().includes(query) || m.nombre.toLowerCase().includes(query))
    }

    if (!found) {
      setError('No se encontró un material con ese id o código')
      setMaterialSearchResult(null)
      setMaterialLots([])
      return
    }

    setError('')
    setMaterialSearchResult(found)
    try {
      const lots = await listLots(found.id)
      setMaterialLots(lots)
    } catch (err) {
      setMaterialLots([])
      setError(err instanceof Error ? err.message : 'No se pudo cargar los lotes')
    }
  }

  async function handleSelectMaterial(materialId: number) {
    const found = materials.find((m) => m.id === materialId) ?? null
    setMaterialSearchResult(found)
    setMaterialSearch(String(materialId))
    if (found) {
      try {
        const lots = await listLots(found.id)
        setMaterialLots(lots)
      } catch (err) {
        setMaterialLots([])
        setError(err instanceof Error ? err.message : 'No se pudo cargar los lotes')
      }
    }
  }

  async function handleSelectFinishedProduct(productId: number) {
    setSelectedFinishedProductId(productId)
    setView('finished-product-detail')
    try {
      const product = await getFinishedProduct(productId)
      setSelectedFinishedProductDetail(product)
    } catch {
      setSelectedFinishedProductDetail(null)
    }
  }

  function handleBackFromFinishedProductDetail() {
    setView('finished-products')
  }

  async function refreshProductionSummary(woId: number) {
    try {
      const summary = await getWorkOrderProductionSummary(woId)
      setProductionSummary(summary)
    } catch (err) {
      setProductionSummary(null)
      setError(err instanceof Error ? err.message : 'No se pudo cargar el resumen de produccion')
    }
  }

  async function handleCreatePartialFinishedProduct(event: React.FormEvent) {
    event.preventDefault()
    try {
      if (!productionForm.work_order_id) {
        throw new Error('Debes seleccionar una Work Order')
      }
      setLoading(true)
      setError('')
      await createWorkOrderFinishedProduct(Number(productionForm.work_order_id), {
        codigo: productionForm.codigo,
        lote_produccion: productionForm.lote_produccion || undefined,
        nombre: productionForm.nombre || undefined,
        descripcion: productionForm.descripcion || undefined,
        cantidad_producida: Number(productionForm.cantidad_producida),
        cantidad_disponible: productionForm.cantidad_disponible ? Number(productionForm.cantidad_disponible) : undefined,
        costo_total: productionForm.costo_total ? Number(productionForm.costo_total) : undefined,
      })
      setMessage('Producto terminado parcial registrado')
      setProductionForm({ work_order_id: '', codigo: '', lote_produccion: '', nombre: '', descripcion: '', cantidad_producida: '', cantidad_disponible: '', costo_total: '' })
      setProductionSummary(null)
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo registrar el producto terminado parcial')
    } finally {
      setLoading(false)
    }
  }

  async function handleCloseWorkOrder(event: React.FormEvent) {
    event.preventDefault()
    try {
      if (!closeForm.work_order_id) {
        throw new Error('Debes seleccionar una Work Order')
      }
      setLoading(true)
      setError('')
      await updateWorkOrderStatus(Number(closeForm.work_order_id), 'finalizado')
      setMessage('Work Order cerrada correctamente')
      setCloseForm({ work_order_id: '' })
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cerrar la Work Order')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateRequisition(event: React.FormEvent) {
    event.preventDefault()
    try {
      setLoading(true)
      setError('')
      await createRequisition({
        work_order_id: requisitionForm.work_order_id ? Number(requisitionForm.work_order_id) : null,
        requester_area: requisitionForm.requester_area || null,
        purpose: requisitionForm.purpose || null,
        notes: requisitionForm.notes || null,
        is_secondary: true,
        items: [
          {
            material_id: Number(requisitionForm.material_id),
            quantity: Number(requisitionForm.quantity),
          },
        ],
      })
      setMessage('Requisicion creada correctamente')
      setRequisitionForm(emptyRequisitionForm)
      setView('requisitions')
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear la requisicion')
    } finally {
      setLoading(false)
    }
  }

  async function handleRequisitionAction(action: 'approve' | 'deliver' | 'cancel', requisitionId: number) {
    try {
      setLoading(true)
      setError('')
      if (action === 'approve') {
        await approveRequisition(requisitionId)
      } else if (action === 'deliver') {
        await deliverRequisition(requisitionId)
      } else {
        await cancelRequisition(requisitionId)
      }
      setMessage(`Requisicion ${action === 'approve' ? 'aprobada' : action === 'deliver' ? 'entregada' : 'cancelada'} correctamente`)
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo ejecutar la accion')
    } finally {
      setLoading(false)
    }
  }

  function logout() {
    localStorage.removeItem('token')
    setToken('')
    setView('login')
    setMaterials([])
    setWorkOrders([])
    setAlmacenes([])
    setLocaciones([])
    setFinishedProducts([])
    setShipments([])
    setMessage('Sesión cerrada')
  }

  if (!authReady || view === 'login') {
    return (
      <div className="page shell login-shell">
        <div className="hero-card">
          <p className="eyebrow">ERP Mini</p>
          <h1>Login operativo para almacén y producción</h1>
          <p className="muted">
            Entra con tu usuario para empezar el flujo de materiales, inventario y órdenes de trabajo.
          </p>

          <form className="form-grid" onSubmit={handleLogin}>
            <label>
              Email
              <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@mini.erp" />
            </label>
            <label>
              Contraseña
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            <button disabled={loading} className="primary-btn" type="submit">
              {loading ? 'Ingresando...' : 'Entrar'}
            </button>
          </form>

          {error ? <p className="error-box">{error}</p> : null}
          {message ? <p className="success-box">{message}</p> : null}
        </div>
      </div>
    )
  }

  return (
    <div className="page shell app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">ERP Mini</p>
          <h2>Flujo de planta</h2>
        </div>
        <nav className="nav">
          <button className={view === 'storage' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('storage')}>Almacenes y locaciones</button>
          <button className={view === 'materials' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('materials')}>Materiales</button>
          <button className={view === 'material-search' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('material-search')}>Buscar material</button>
          <button className={view === 'material-intake' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('material-intake')}>Entrada de material</button>
          <button className={view === 'requisitions' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('requisitions')}>Requisiciones</button>
          <button className={view === 'work-orders' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('work-orders')}>Work Orders</button>
          <button className={view === 'work-order-detail' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('work-order-detail')}>Detalle WO</button>
          <button className={view === 'production-entry' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('production-entry')}>Producción parcial</button>
          <button className={view === 'finished-products' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('finished-products')}>Productos terminados</button>
        </nav>
        <button className="secondary-btn" onClick={logout}>Cerrar sesión</button>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Sesión activa</p>
            <h1>Materiales, lotes y WO</h1>
          </div>
          <button className="secondary-btn" onClick={refreshData}>Refrescar</button>
        </header>

        {message ? <div className="success-box">{message}</div> : null}
        {error ? <div className="error-box">{error}</div> : null}

        {view === 'storage' ? (
          <section className="grid-2">
            <article className="panel">
              <h3>Alta de almacen</h3>
              <form className="form-grid" onSubmit={handleCreateAlmacen}>
                <label>Codigo<input value={almacenForm.codigo} onChange={(e) => setAlmacenForm({ ...almacenForm, codigo: e.target.value })} /></label>
                <label>Nombre<input value={almacenForm.nombre} onChange={(e) => setAlmacenForm({ ...almacenForm, nombre: e.target.value })} /></label>
                <label>Tipo<input value={almacenForm.tipo} onChange={(e) => setAlmacenForm({ ...almacenForm, tipo: e.target.value })} /></label>
                <label className="full">Descripcion<textarea value={almacenForm.descripcion} onChange={(e) => setAlmacenForm({ ...almacenForm, descripcion: e.target.value })} /></label>
                <button disabled={loading} className="primary-btn" type="submit">Crear almacen</button>
              </form>
            </article>

            <article className="panel">
              <h3>Alta de locacion</h3>
              <form className="form-grid" onSubmit={handleCreateLocacion}>
                <label>
                  Almacen
                  <select value={locacionForm.almacen_id} onChange={(e) => setLocacionForm({ ...locacionForm, almacen_id: e.target.value })}>
                    <option value="">Selecciona uno</option>
                    {almacenes.map((almacen) => (
                      <option key={almacen.id} value={almacen.id}>{almacen.codigo} - {almacen.nombre}</option>
                    ))}
                  </select>
                </label>
                <label>Codigo<input value={locacionForm.codigo} onChange={(e) => setLocacionForm({ ...locacionForm, codigo: e.target.value })} /></label>
                <label>Nombre<input value={locacionForm.nombre} onChange={(e) => setLocacionForm({ ...locacionForm, nombre: e.target.value })} /></label>
                <label className="full">Descripcion<textarea value={locacionForm.descripcion} onChange={(e) => setLocacionForm({ ...locacionForm, descripcion: e.target.value })} /></label>
                <button disabled={loading} className="primary-btn" type="submit">Crear locacion</button>
              </form>
            </article>

            <article className="panel">
              <h3>Almacenes registrados</h3>
              <div className="list">
                {almacenes.map((almacen) => (
                  <div key={almacen.id} className="list-item">
                    <strong>{almacen.codigo}</strong>
                    <span>{almacen.nombre}</span>
                    <small>{almacen.tipo ?? 'sin tipo'} · {almacen.activo ? 'activo' : 'inactivo'}</small>
                    <div className="nested-list">
                      {(locacionesPorAlmacen.get(almacen.id) ?? []).map((locacion) => (
                        <div key={locacion.id} className="nested-list-item">
                          <strong>{locacion.codigo}</strong>
                          <span>{locacion.nombre}</span>
                          <small>{locacion.activo ? 'activa' : 'inactiva'}</small>
                        </div>
                      ))}
                      {!locacionesPorAlmacen.get(almacen.id)?.length ? (
                        <p className="muted">Sin locaciones registradas.</p>
                      ) : null}
                    </div>
                  </div>
                ))}
                {!almacenes.length ? <p className="muted">Todavia no hay almacenes.</p> : null}
              </div>
            </article>
          </section>
        ) : null}

        {view === 'material-search' ? (
          <section className="grid-2">
            <article className="panel">
              <h3>Buscar material</h3>
              <p className="muted">Busca por ID numérico, código o nombre.</p>
              <form className="form-grid" onSubmit={handleSearchMaterial}>
                <label className="full">
                  ID o código
                  <input value={materialSearch} onChange={(e) => setMaterialSearch(e.target.value)} placeholder="Ej. 12 o MAT-001" />
                </label>
                <button className="primary-btn" type="submit">Buscar material</button>
              </form>

              <h4 className="mt-1">Resultados rápidos</h4>
              <div className="list">
                {materials
                  .filter((m) => {
                    const q = materialSearch.trim().toLowerCase()
                    if (!q) return true
                    return String(m.id) === q || m.codigo.toLowerCase().includes(q) || m.nombre.toLowerCase().includes(q)
                  })
                  .slice(0, 10)
                  .map((m) => (
                    <div key={m.id} role="button" tabIndex={0} className={materialSearchResult?.id === m.id ? 'list-item list-item-button active' : 'list-item list-item-button'} onClick={() => handleSelectMaterial(m.id)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSelectMaterial(m.id) } }}>
                      <strong>{m.codigo}</strong>
                      <span>#{m.id} · {m.nombre}</span>
                      <small>{m.unidad}</small>
                    </div>
                  ))}
                {!materials.length ? <p className="muted">Todavía no hay materiales registrados.</p> : null}
              </div>
            </article>

            <article className="panel detail-panel">
              {materialSearchResult ? (
                <>
                  <div className="action-row">
                    <button className="secondary-btn" type="button" onClick={() => { setMaterialSearch(''); setMaterialSearchResult(null); setMaterialLots([]) }}>Limpiar</button>
                  </div>
                  <h3>{materialSearchResult.codigo} · {materialSearchResult.nombre}</h3>
                  <p className="muted">Detalle del material y sus lotes registrados.</p>

                  <div className="detail-grid">
                    <div><strong>ID</strong><p>{materialSearchResult.id}</p></div>
                    <div><strong>Unidad</strong><p>{materialSearchResult.unidad}</p></div>
                    <div><strong>Creado</strong><p>{new Date(materialSearchResult.created_at).toLocaleDateString()}</p></div>
                    <div><strong>Descripción</strong><p>{materialSearchResult.descripcion ?? 'sin descripción'}</p></div>
                  </div>

                  <h4 className="mt-1">Lotes</h4>
                  <div className="list">
                    {materialLots.map((lot) => (
                      <div key={lot.id} className="list-item">
                        <strong>{lot.codigo_lote}</strong>
                        <span>{lot.cantidad} · dispon.: {lot.cantidad_disponible} · reserv.: {lot.cantidad_reservada}</span>
                        <small>
                          {lot.almacen_id ? (almacenes.find((a) => a.id === lot.almacen_id)?.codigo ?? `Alm ${lot.almacen_id}`) : 'Sin almacén'}
                          {lot.locacion_id ? ` · ${locaciones.find((l) => l.id === lot.locacion_id)?.codigo ?? `Loc ${lot.locacion_id}`}` : ''}
                          {' · '}{new Date(lot.fecha_entrada).toLocaleDateString()}
                        </small>
                      </div>
                    ))}
                    {!materialLots.length ? <p className="muted">No hay lotes registrados para este material.</p> : null}
                  </div>
                </>
              ) : (
                <>
                  <h3>Buscar material</h3>
                  <p className="muted">Realiza una búsqueda para ver los lotes asociados.</p>
                </>
              )}
            </article>
          </section>
        ) : null}

        {view === 'materials' ? (
          <section className="grid-2">
            <article className="panel">
              <h3>Alta de material</h3>
              <form className="form-grid" onSubmit={handleCreateMaterial}>
                <label>Codigo<input value={materialForm.codigo} onChange={(e) => setMaterialForm({ ...materialForm, codigo: e.target.value })} /></label>
                <label>Nombre<input value={materialForm.nombre} onChange={(e) => setMaterialForm({ ...materialForm, nombre: e.target.value })} /></label>
                <label>Unidad<input value={materialForm.unidad} onChange={(e) => setMaterialForm({ ...materialForm, unidad: e.target.value })} /></label>
                <label className="full">Descripcion<textarea value={materialForm.descripcion} onChange={(e) => setMaterialForm({ ...materialForm, descripcion: e.target.value })} /></label>
                <button disabled={loading} className="primary-btn" type="submit">Crear material</button>
              </form>
            </article>

            <article className="panel">
              <h3>Materiales registrados</h3>
              <div className="list">
                {materials.map((material) => (
                  <div key={material.id} className="list-item">
                    <strong>{material.codigo}</strong>
                    <span>{material.nombre}</span>
                    <small>{material.unidad}</small>
                  </div>
                ))}
                {!materials.length ? <p className="muted">Todavia no hay materiales.</p> : null}
              </div>
            </article>
          </section>
        ) : null}

        {view === 'material-intake' ? (
          <section className="grid-2">
            <article className="panel">
              <h3>Entrada de materia prima</h3>
              <p className="muted">Primero elige el almacen para cargar solo sus locaciones.</p>
              <form className="form-grid" onSubmit={handleCreateLot}>
                <label>
                  Material
                  <select required value={lotForm.material_id} onChange={(e) => setLotForm({ ...lotForm, material_id: e.target.value })}>
                    <option value="">Selecciona uno</option>
                    {materials.map((material) => (
                      <option key={material.id} value={material.id}>{material.codigo} - {material.nombre}</option>
                    ))}
                  </select>
                </label>
                <label>Codigo lote<input value={lotForm.codigo_lote} onChange={(e) => setLotForm({ ...lotForm, codigo_lote: e.target.value })} /></label>
                <label>Cantidad<input type="number" step="0.01" value={lotForm.cantidad} onChange={(e) => setLotForm({ ...lotForm, cantidad: e.target.value })} /></label>
                <label>
                  Almacen
                  <select required value={lotForm.almacen_id} onChange={(e) => setLotForm({ ...lotForm, almacen_id: e.target.value, locacion_id: '' })}>
                    <option value="">Selecciona uno</option>
                    {almacenes.map((almacen) => (
                      <option key={almacen.id} value={almacen.id}>{almacen.codigo} - {almacen.nombre}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Locacion
                  <select
                    disabled={!lotForm.almacen_id}
                    value={lotForm.locacion_id}
                    onChange={(e) => setLotForm({ ...lotForm, locacion_id: e.target.value })}
                  >
                    <option value="">Selecciona una</option>
                    {locaciones.filter((locacion) => locacion.almacen_id === Number(lotForm.almacen_id)).map((locacion) => (
                      <option key={locacion.id} value={locacion.id}>{locacion.codigo} - {locacion.nombre}</option>
                    ))}
                  </select>
                </label>
                <label>Costo unitario<input type="number" step="0.01" value={lotForm.costo_unitario} onChange={(e) => setLotForm({ ...lotForm, costo_unitario: e.target.value })} /></label>
                <label>Fecha caducidad<input type="datetime-local" value={lotForm.fecha_caducidad} onChange={(e) => setLotForm({ ...lotForm, fecha_caducidad: e.target.value })} /></label>
                <label className="full">Notas<textarea value={lotForm.notas} onChange={(e) => setLotForm({ ...lotForm, notas: e.target.value })} /></label>
                <button disabled={loading} className="primary-btn" type="submit">Registrar entrada</button>
              </form>
              {lotForm.almacen_id && !locaciones.some((locacion) => locacion.almacen_id === Number(lotForm.almacen_id)) ? (
                <p className="muted">Este almacen no tiene locaciones registradas todavía.</p>
              ) : null}
            </article>

            <article className="panel">
              <h3>Secuencia sugerida</h3>
              <ol className="steps">
                <li>Dar de alta almacenes y locaciones.</li>
                <li>Registrar el material maestro.</li>
                <li>Registrar el lote de entrada con fecha y ubicación.</li>
                <li>Usar esos lotes en las WO por FIFO.</li>
              </ol>
              <p className="muted">Esta pantalla ya usa el endpoint real <code>/materials/{'{id}'}/lotes</code>.</p>
            </article>
          </section>
        ) : null}

        {view === 'requisitions' ? (
          <section className="grid-2">
            <article className="panel">
              <h3>Crear requisicion</h3>
              <form className="form-grid" onSubmit={handleCreateRequisition}>
                <label>
                  Work Order
                  <select value={requisitionForm.work_order_id} onChange={(e) => setRequisitionForm({ ...requisitionForm, work_order_id: e.target.value })}>
                    <option value="">Opcional</option>
                    {workOrders.map((wo) => (
                      <option key={wo.id} value={wo.id}>{wo.numero_orden} - {wo.status}</option>
                    ))}
                  </select>
                </label>
                <label>Area solicitante<input value={requisitionForm.requester_area} onChange={(e) => setRequisitionForm({ ...requisitionForm, requester_area: e.target.value })} /></label>
                <label>Proposito<input value={requisitionForm.purpose} onChange={(e) => setRequisitionForm({ ...requisitionForm, purpose: e.target.value })} /></label>
                <label>
                  Material
                  <select required value={requisitionForm.material_id} onChange={(e) => setRequisitionForm({ ...requisitionForm, material_id: e.target.value })}>
                    <option value="">Selecciona uno</option>
                    {materials.map((material) => (
                      <option key={material.id} value={material.id}>{material.codigo} - {material.nombre}</option>
                    ))}
                  </select>
                </label>
                <label>Cantidad<input required type="number" step="0.01" value={requisitionForm.quantity} onChange={(e) => setRequisitionForm({ ...requisitionForm, quantity: e.target.value })} /></label>
                <label className="full">Notas<textarea value={requisitionForm.notes} onChange={(e) => setRequisitionForm({ ...requisitionForm, notes: e.target.value })} /></label>
                <button disabled={loading} className="primary-btn" type="submit">Crear requisicion</button>
              </form>
            </article>

            <article className="panel">
              <h3>Requisiciones registradas</h3>
              <div className="list">
                {requisitions.map((req) => (
                  <div key={req.id} className="list-item">
                    <strong>{req.codigo}</strong>
                    <span>{req.status} {req.work_order_id ? `· WO ${req.work_order_id}` : ''}</span>
                    <small>{req.items.length} item(s) · {req.requester_area ?? 'sin area'}</small>
                    <div className="action-row">
                      <button className="secondary-btn" type="button" onClick={() => handleRequisitionAction('approve', req.id)} disabled={loading}>Aprobar</button>
                      <button className="secondary-btn" type="button" onClick={() => handleRequisitionAction('deliver', req.id)} disabled={loading}>Entregar</button>
                      <button className="secondary-btn" type="button" onClick={() => handleRequisitionAction('cancel', req.id)} disabled={loading}>Cancelar</button>
                    </div>
                  </div>
                ))}
                {!requisitions.length ? <p className="muted">Todavia no hay requisiciones.</p> : null}
              </div>
            </article>
          </section>
        ) : null}

        {view === 'work-orders' ? (
          <section className="grid-2">
            <article className="panel">
              <h3>Crear Work Order</h3>
              <form className="form-grid" onSubmit={handleCreateWO}>
                <label>Numero orden<input value={woForm.numero_orden} onChange={(e) => setWoForm({ ...woForm, numero_orden: e.target.value })} /></label>
                <label>Descripcion<input value={woForm.descripcion} onChange={(e) => setWoForm({ ...woForm, descripcion: e.target.value })} /></label>
                <label>Cantidad a producir<input type="number" step="0.01" value={woForm.cantidad_a_producir} onChange={(e) => setWoForm({ ...woForm, cantidad_a_producir: e.target.value })} /></label>
                {woItems.map((it, idx) => (
                  <div key={idx} className="wo-item-row">
                    <label>
                      Material
                      <select value={it.material_id} onChange={(e) => handleUpdateWoItem(idx, 'material_id', e.target.value)}>
                        <option value="">Selecciona uno</option>
                        {materials.map((material) => (
                          <option key={material.id} value={material.id}>{material.codigo} - {material.nombre}</option>
                        ))}
                      </select>
                    </label>
                    <label>Cantidad requerida<input type="number" step="0.01" value={it.cantidad_requerida} onChange={(e) => handleUpdateWoItem(idx, 'cantidad_requerida', e.target.value)} /></label>
                    <div className="item-actions">
                      <button type="button" className="secondary-btn" onClick={() => handleRemoveWoItem(idx)} disabled={woItems.length <= 1}>Quitar</button>
                    </div>
                  </div>
                ))}
                <div>
                  <button type="button" className="secondary-btn" onClick={handleAddWoItem}>Agregar item</button>
                </div>
                <label className="full">Notas<textarea value={woForm.notas} onChange={(e) => setWoForm({ ...woForm, notas: e.target.value })} /></label>
                <button disabled={loading} className="primary-btn" type="submit">Crear WO</button>
              </form>
            </article>

            <article className="panel">
              <h3>Work Orders recientes</h3>
              <div className="list">
                {workOrders.map((wo) => (
                  <div
                    key={wo.id}
                    role="button"
                    tabIndex={0}
                    className={selectedWorkOrderId === wo.id ? 'list-item list-item-button active' : 'list-item list-item-button'}
                    onClick={() => handleOpenWorkOrderDetail(wo.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleOpenWorkOrderDetail(wo.id)
                      }
                    }}
                  >
                    <strong>{wo.numero_orden}</strong>
                    <span>{wo.status}</span>
                    <small>{wo.cantidad_a_producir} unidades</small>
                    <div className="action-row">
                      <button className="secondary-btn" type="button" onClick={(e) => { e.stopPropagation(); void handleUpdateWOStatus(wo.id, 'surtido') }} disabled={loading || wo.status !== 'pendiente'}>Marcar surtido</button>
                    </div>
                  </div>
                ))}
                {!workOrders.length ? <p className="muted">Aun no hay WO.</p> : null}
              </div>
            </article>
          </section>
        ) : null}

        {view === 'work-orders' && selectedWorkOrder ? (
          <section className="panel detail-panel">
            <h3>Detalle de {selectedWorkOrder.numero_orden}</h3>
            <p className="muted">Descripción: {selectedWorkOrder.descripcion ?? 'sin descripción'}</p>
            <div className="detail-grid">
              <div>
                <strong>Estado</strong>
                <p>{selectedWorkOrder.status}</p>
              </div>
              <div>
                <strong>Cantidad planeada</strong>
                <p>{selectedWorkOrder.cantidad_a_producir}</p>
              </div>
              <div>
                <strong>Notas</strong>
                <p>{selectedWorkOrder.notas ?? 'sin notas'}</p>
              </div>
              <div>
                <strong>Fecha</strong>
                <p>{new Date(selectedWorkOrder.created_at).toLocaleDateString()}</p>
              </div>
            </div>

            <h4 className="mt-1">Material cargado en la orden</h4>
            <div className="list">
              {(selectedWorkOrder.items ?? []).map((item) => (
                <div key={item.id} className="list-item">
                  <strong>{item.material_codigo} - {item.material_nombre}</strong>
                  <span>{item.cantidad_asignada} de {item.cantidad_requerida} cargadas</span>
                  <small>{item.material_unidad} · {item.lotes_utilizados.length} lote(s)</small>
                  <div className="nested-list">
                    {item.lotes_utilizados.map((lote) => (
                      <div key={`${item.id}-${lote.material_lot_id}`} className="nested-list-item">
                        <strong>{lote.codigo_lote}</strong>
                        <span>{lote.cantidad}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {!selectedWorkOrder.items?.length ? <p className="muted">Esta orden aún no tiene materiales cargados.</p> : null}
            </div>

            <h4 className="mt-1">Producción registrada</h4>
            <div className="list">
              {selectedWorkOrderFinishedProducts.map((fp) => (
                <div key={fp.id} className="list-item">
                  <strong>{fp.codigo}</strong>
                  <span>{fp.nombre}</span>
                  <small>{fp.cantidad_producida} producidas · {fp.cantidad_disponible} disponibles</small>
                </div>
              ))}
              {!selectedWorkOrderFinishedProducts.length ? <p className="muted">Todavía no hay producto terminado registrado para esta orden.</p> : null}
            </div>

            <h4 className="mt-1">Avance general</h4>
            {productionSummary?.work_order_id === selectedWorkOrder.id ? (
              <div className="detail-grid">
                <div><strong>Producido</strong><p>{productionSummary.cantidad_producida}</p></div>
                <div><strong>Pendiente</strong><p>{productionSummary.cantidad_pendiente}</p></div>
                <div><strong>Disponible</strong><p>{productionSummary.cantidad_disponible}</p></div>
                <div><strong>Completa</strong><p>{productionSummary.esta_completa ? 'sí' : 'no'}</p></div>
              </div>
            ) : (
              <p className="muted">Selecciona la misma orden en Producción parcial para ver el resumen completo.</p>
            )}
          </section>
        ) : null}

        {view === 'work-order-detail' ? (
          <section className="grid-2">
            <article className="panel">
              <h3>Buscar Work Order</h3>
              <p className="muted">Busca por ID numérico o por código/numero de orden.</p>
              <form className="form-grid" onSubmit={handleSearchWorkOrder}>
                <label className="full">
                  ID o código
                  <input
                    value={workOrderSearch}
                    onChange={(e) => setWorkOrderSearch(e.target.value)}
                    placeholder="Ej. 12 o WO-TEST-MULTI-002"
                  />
                </label>
                <button className="primary-btn" type="submit">Buscar WO</button>
              </form>

              <h4 className="mt-1">Resultados rápidos</h4>
              <div className="list">
                {workOrders
                  .filter((wo) => {
                    const query = workOrderSearch.trim().toLowerCase()
                    if (!query) return true
                    return String(wo.id) === query || wo.numero_orden.toLowerCase().includes(query)
                  })
                  .slice(0, 10)
                  .map((wo) => (
                    <div
                      key={wo.id}
                      role="button"
                      tabIndex={0}
                      className={selectedWorkOrderId === wo.id ? 'list-item list-item-button active' : 'list-item list-item-button'}
                      onClick={() => handleSelectWorkOrder(wo.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          handleSelectWorkOrder(wo.id)
                        }
                      }}
                    >
                      <strong>{wo.numero_orden}</strong>
                      <span>#{wo.id} · {wo.status}</span>
                      <small>{wo.cantidad_a_producir} unidades</small>
                    </div>
                  ))}
                {!workOrders.length ? <p className="muted">No hay WO registradas.</p> : null}
              </div>
            </article>

            <article className="panel detail-panel">
              {selectedWorkOrder ? (
                <>
                  <div className="action-row">
                    <button className="secondary-btn" type="button" onClick={() => setView('work-orders')}>Volver a Work Orders</button>
                  </div>
                  <h3>Detalle de {selectedWorkOrder.numero_orden}</h3>
                  <p className="muted">La WO completa en una pestaña independiente.</p>

                  <div className="detail-grid">
                    <div><strong>ID</strong><p>{selectedWorkOrder.id}</p></div>
                    <div><strong>Estado</strong><p>{selectedWorkOrder.status}</p></div>
                    <div><strong>Cantidad planeada</strong><p>{selectedWorkOrder.cantidad_a_producir}</p></div>
                    <div><strong>Fecha</strong><p>{new Date(selectedWorkOrder.created_at).toLocaleDateString()}</p></div>
                  </div>

                  <h4 className="mt-1">Material cargado</h4>
                  <div className="list">
                    {(selectedWorkOrder.items ?? []).map((item) => (
                      <div key={item.id} className="list-item">
                        <strong>{item.material_codigo} - {item.material_nombre}</strong>
                        <span>{item.cantidad_asignada} de {item.cantidad_requerida}</span>
                        <small>{item.material_unidad} · {item.lotes_utilizados.length} lote(s)</small>
                      </div>
                    ))}
                    {!selectedWorkOrder.items?.length ? <p className="muted">Esta orden no tiene materiales cargados.</p> : null}
                  </div>

                  <h4 className="mt-1">Producción registrada</h4>
                  <div className="list">
                    {selectedWorkOrderFinishedProducts.map((fp) => (
                      <div key={fp.id} className="list-item">
                        <strong>{fp.codigo}</strong>
                        <span>{fp.nombre}</span>
                        <small>{fp.cantidad_producida} producidas · {fp.cantidad_disponible} disponibles</small>
                      </div>
                    ))}
                    {!selectedWorkOrderFinishedProducts.length ? <p className="muted">Todavía no hay producto terminado para esta WO.</p> : null}
                  </div>
                </>
              ) : (
                <>
                  <h3>Detalle de Work Order</h3>
                  <p className="muted">Busca una WO por id o código para ver su detalle completo aquí.</p>
                </>
              )}
            </article>
          </section>
        ) : null}

        {view === 'production-entry' ? (
          <section className="grid-2">
            <article className="panel">
              <h3>Registrar producto terminado parcial</h3>
              <form className="form-grid" onSubmit={handleCreatePartialFinishedProduct}>
                <label>
                  Work Order
                  <select value={productionForm.work_order_id} onChange={(e) => setProductionForm({ ...productionForm, work_order_id: e.target.value })}>
                    <option value="">Selecciona una</option>
                    {workOrders.map((wo) => (
                      <option key={wo.id} value={wo.id}>{wo.numero_orden} · {wo.status}</option>
                    ))}
                  </select>
                </label>
                <label>Codigo<input value={productionForm.codigo} onChange={(e) => setProductionForm({ ...productionForm, codigo: e.target.value })} /></label>
                <label>Lote produccion<input value={productionForm.lote_produccion} onChange={(e) => setProductionForm({ ...productionForm, lote_produccion: e.target.value })} /></label>
                <label>Nombre<input value={productionForm.nombre} onChange={(e) => setProductionForm({ ...productionForm, nombre: e.target.value })} /></label>
                <label>Cantidad producida<input type="number" step="0.01" value={productionForm.cantidad_producida} onChange={(e) => setProductionForm({ ...productionForm, cantidad_producida: e.target.value })} /></label>
                <label>Cantidad disponible<input type="number" step="0.01" value={productionForm.cantidad_disponible} onChange={(e) => setProductionForm({ ...productionForm, cantidad_disponible: e.target.value })} /></label>
                <label>Costo total<input type="number" step="0.01" value={productionForm.costo_total} onChange={(e) => setProductionForm({ ...productionForm, costo_total: e.target.value })} /></label>
                <label className="full">Descripcion<textarea value={productionForm.descripcion} onChange={(e) => setProductionForm({ ...productionForm, descripcion: e.target.value })} /></label>
                <button disabled={loading} className="primary-btn" type="submit">Registrar parcial</button>
              </form>
            </article>

            <article className="panel">
              <h3>Resumen de producción</h3>
              <p className="muted">Selecciona una Work Order para ver el avance de lo producido.</p>
              {productionForm.work_order_id ? (
                <div className="list-item">
                  <strong>{workOrders.find((wo) => wo.id === Number(productionForm.work_order_id))?.numero_orden ?? 'WO'}</strong>
                  <span>{productionSummary ? `${productionSummary.cantidad_producida} producidas de ${productionSummary.cantidad_a_producir}` : 'Cargando resumen...'}</span>
                  <small>{productionSummary ? `${productionSummary.cantidad_pendiente} pendientes · ${productionSummary.esta_completa ? 'completa' : 'parcial'}` : 'Sin datos'}</small>
                </div>
              ) : null}

              <h4 className="mt-1">Productos y envíos</h4>
              <div className="list">
                {finishedProducts.map((fp) => (
                  <div
                    key={fp.id}
                    role="button"
                    tabIndex={0}
                    className={selectedFinishedProductId === fp.id ? 'list-item list-item-button active' : 'list-item list-item-button'}
                    onClick={() => { void handleSelectFinishedProduct(fp.id) }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        void handleSelectFinishedProduct(fp.id)
                      }
                    }}
                  >
                    <strong>{fp.codigo}</strong>
                    <span>{fp.nombre} · {fp.cantidad_disponible} disponibles</span>
                    <small>Lote: {fp.lote_produccion}</small>
                  </div>
                ))}
                {!finishedProducts.length ? <p className="muted">Todavia no hay productos terminados.</p> : null}
              </div>

              <h4 className="mt-1">Registrar envío</h4>
              <form
                className="form-grid"
                onSubmit={async (e) => {
                  e.preventDefault()
                  try {
                    setLoading(true)
                    setError('')
                    await createFinishedProductShipment({
                      finished_product_id: Number(shipmentForm.finished_product_id),
                      cantidad: Number(shipmentForm.cantidad),
                      destinatario: shipmentForm.destinatario || undefined,
                      documento_envio: shipmentForm.documento_envio || undefined,
                      observaciones: shipmentForm.observaciones || undefined,
                    })
                    setMessage('Envio registrado')
                    setShipmentForm({ finished_product_id: '', cantidad: '', destinatario: '', documento_envio: '', observaciones: '' })
                    await refreshData()
                  } catch (err) {
                    setError(err instanceof Error ? err.message : 'No se pudo registrar el envio')
                  } finally {
                    setLoading(false)
                  }
                }}
              >
                <label>
                  Producto
                  <select value={shipmentForm.finished_product_id} onChange={(e) => setShipmentForm({ ...shipmentForm, finished_product_id: e.target.value })}>
                    <option value="">Selecciona uno</option>
                    {finishedProducts.map((fp) => (
                      <option key={fp.id} value={fp.id}>{fp.codigo} - {fp.nombre} ({fp.cantidad_disponible})</option>
                    ))}
                  </select>
                </label>
                <label>Cantidad<input type="number" step="0.01" value={shipmentForm.cantidad} onChange={(e) => setShipmentForm({ ...shipmentForm, cantidad: e.target.value })} /></label>
                <label>Destinatario<input value={shipmentForm.destinatario} onChange={(e) => setShipmentForm({ ...shipmentForm, destinatario: e.target.value })} /></label>
                <label>Documento<input value={shipmentForm.documento_envio} onChange={(e) => setShipmentForm({ ...shipmentForm, documento_envio: e.target.value })} /></label>
                <label className="full">Observaciones<textarea value={shipmentForm.observaciones} onChange={(e) => setShipmentForm({ ...shipmentForm, observaciones: e.target.value })} /></label>
                <button disabled={loading} className="primary-btn" type="submit">Registrar envio</button>
              </form>

              <h4 className="mt-1">Envios recientes</h4>
              <div className="list">
                {shipments.map((s) => {
                  const product = finishedProducts.find((fp) => fp.id === s.finished_product_id)
                  return (
                    <div key={s.id} className="list-item">
                      <strong>{product ? product.nombre : `Producto ${s.finished_product_id}`}</strong>
                      <span>{s.destinatario ?? 'sin destinatario'}</span>
                      <small>WO {product?.work_order_id ?? 'N/A'} · {s.cantidad} · {new Date(s.created_at).toLocaleDateString()}</small>
                    </div>
                  )
                })}
                {!shipments.length ? <p className="muted">No hay envíos registrados.</p> : null}
              </div>
            </article>
          </section>
        ) : null}

        {view === 'finished-products' ? (
          <section className="grid-2">
            <article className="panel">
              <h3>Cerrar Work Order</h3>
              <p className="muted">Esta pantalla queda para cerrar la orden cuando ya se registró la producción parcial y los envíos necesarios.</p>
              <form className="form-grid" onSubmit={handleCloseWorkOrder}>
                <label>
                  Work Order
                  <select value={closeForm.work_order_id} onChange={(e) => setCloseForm({ work_order_id: e.target.value })}>
                    <option value="">Selecciona una</option>
                    {workOrders.map((wo) => (
                      <option key={wo.id} value={wo.id}>{wo.numero_orden} · {wo.status}</option>
                    ))}
                  </select>
                </label>
                {closeForm.work_order_id ? (
                  <div className="list-item full">
                    <strong>Resumen</strong>
                    <span>
                      {productionSummary && productionSummary.work_order_id === Number(closeForm.work_order_id)
                        ? `${productionSummary.cantidad_producida} producidas de ${productionSummary.cantidad_a_producir}`
                        : 'Selecciona la WO para ver el resumen.'}
                    </span>
                    <small>
                      {productionSummary && productionSummary.work_order_id === Number(closeForm.work_order_id)
                        ? `${productionSummary.cantidad_pendiente} pendientes · ${productionSummary.esta_completa ? 'lista para cerrar' : 'aún parcial'}`
                        : 'El cierre solo debe hacerse cuando ya se terminó y envió lo necesario.'}
                    </small>
                  </div>
                ) : null}
                <button disabled={loading} className="primary-btn" type="submit">Cerrar orden</button>
              </form>
            </article>

            <article className="panel">
              <h3>Órdenes abiertas</h3>
              <div className="list">
                {workOrders.map((wo) => (
                  <div
                    key={wo.id}
                    role="button"
                    tabIndex={0}
                    className={selectedWorkOrderId === wo.id ? 'list-item list-item-button active' : 'list-item list-item-button'}
                    onClick={() => handleOpenWorkOrderDetail(wo.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleOpenWorkOrderDetail(wo.id)
                      }
                    }}
                  >
                    <strong>{wo.numero_orden}</strong>
                    <span>{wo.status}</span>
                    <small>{wo.cantidad_a_producir} unidades</small>
                  </div>
                ))}
                {!workOrders.length ? <p className="muted">Aun no hay WO.</p> : null}
              </div>
            </article>
          </section>
        ) : null}

        {view === 'finished-products' && selectedWorkOrder ? (
          <section className="panel detail-panel">
            <div className="action-row">
              <button className="secondary-btn" type="button" onClick={() => setSelectedWorkOrderId(null)}>Quitar detalle</button>
              <button className="secondary-btn" type="button" onClick={() => { setView('work-orders') }}>Abrir en Work Orders</button>
            </div>
            <h3>Detalle de {selectedWorkOrder.numero_orden}</h3>
            <p className="muted">La misma WO mostrada desde la pestaña de productos terminados.</p>

            <div className="detail-grid">
              <div>
                <strong>Estado</strong>
                <p>{selectedWorkOrder.status}</p>
              </div>
              <div>
                <strong>Cantidad planeada</strong>
                <p>{selectedWorkOrder.cantidad_a_producir}</p>
              </div>
              <div>
                <strong>Notas</strong>
                <p>{selectedWorkOrder.notas ?? 'sin notas'}</p>
              </div>
              <div>
                <strong>Fecha</strong>
                <p>{new Date(selectedWorkOrder.created_at).toLocaleDateString()}</p>
              </div>
            </div>

            <h4 className="mt-1">Material cargado</h4>
            <div className="list">
              {(selectedWorkOrder.items ?? []).map((item) => (
                <div key={item.id} className="list-item">
                  <strong>{item.material_codigo} - {item.material_nombre}</strong>
                  <span>{item.cantidad_asignada} de {item.cantidad_requerida} cargadas</span>
                  <small>{item.material_unidad} · {item.lotes_utilizados.length} lote(s)</small>
                </div>
              ))}
              {!selectedWorkOrder.items?.length ? <p className="muted">Esta orden aún no tiene materiales cargados.</p> : null}
            </div>

            <h4 className="mt-1">Producto terminado asociado</h4>
            <div className="list">
              {selectedWorkOrderFinishedProducts.map((fp) => (
                <div key={fp.id} className="list-item">
                  <strong>{fp.codigo}</strong>
                  <span>{fp.nombre}</span>
                  <small>{fp.cantidad_producida} producidas · {fp.cantidad_disponible} disponibles</small>
                </div>
              ))}
              {!selectedWorkOrderFinishedProducts.length ? <p className="muted">No hay producto terminado para esta WO todavía.</p> : null}
            </div>
          </section>
        ) : null}

        {view === 'finished-product-detail' && selectedFinishedProduct ? (
          <section className="grid-2">
            <article className="panel">
              <div className="action-row">
                <button className="secondary-btn" type="button" onClick={handleBackFromFinishedProductDetail}>Volver a productos terminados</button>
              </div>
              <h3>{selectedFinishedProduct.nombre}</h3>
              <p className="muted">Detalle completo del producto terminado y su Work Order de origen.</p>

              <div className="detail-grid">
                <div><strong>Código</strong><p>{selectedFinishedProduct.codigo}</p></div>
                <div><strong>Lote</strong><p>{selectedFinishedProduct.lote_produccion}</p></div>
                <div><strong>Producido</strong><p>{selectedFinishedProduct.cantidad_producida}</p></div>
                <div><strong>Disponible</strong><p>{selectedFinishedProduct.cantidad_disponible}</p></div>
                <div><strong>Costo total</strong><p>{selectedFinishedProduct.costo_total ?? 'N/A'}</p></div>
                <div><strong>Fecha</strong><p>{new Date(selectedFinishedProduct.created_at).toLocaleDateString()}</p></div>
              </div>

              <h4 className="mt-1">Work Order asociada</h4>
              {selectedFinishedProductWorkOrder ? (
                <div className="list-item">
                  <strong>{selectedFinishedProductWorkOrder.numero_orden}</strong>
                  <span>{selectedFinishedProductWorkOrder.status}</span>
                  <small>{selectedFinishedProductWorkOrder.cantidad_a_producir} unidades planificadas</small>
                </div>
              ) : (
                <p className="muted">No se encontró la WO asociada en memoria.</p>
              )}

              {selectedFinishedProductWorkOrder ? (
                <div className="action-row mt-1">
                  <button className="secondary-btn" type="button" onClick={() => { setSelectedWorkOrderId(selectedFinishedProductWorkOrder.id); setView('work-orders') }}>
                    Ver WO completa
                  </button>
                </div>
              ) : null}
            </article>

            <article className="panel">
              <h3>Producción y envíos</h3>
              <div className="list">
                <div className="list-item">
                  <strong>Producción</strong>
                  <span>{selectedFinishedProduct.cantidad_producida} unidades registradas</span>
                  <small>{selectedFinishedProduct.cantidad_disponible} disponibles para envío</small>
                </div>
                {selectedFinishedProductShipments.map((shipment) => (
                  <div key={shipment.id} className="list-item">
                    <strong>{shipment.destinatario ?? 'sin destinatario'}</strong>
                    <span>{shipment.documento_envio ?? 'sin documento'}</span>
                    <small>{shipment.cantidad} · {new Date(shipment.created_at).toLocaleDateString()}</small>
                  </div>
                ))}
                {!selectedFinishedProductShipments.length ? <p className="muted">Este producto aún no tiene envíos.</p> : null}
              </div>
            </article>
          </section>
        ) : null}
      </main>
    </div>
  )
}
