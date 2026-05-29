# ERP Mini - Sistema de Lotes FIFO

## 📊 Nuevo Modelo de Datos con Lotes

### Cambios Principales

**Antes:** Material tenía `stock_actual` único
```
Material
├── código
├── nombre
├── stock_actual: 500 kg ❌ No sabemos qué lotes tenemos ni cuándo caducan
```

**Ahora:** Material es maestro, MaterialLot contiene el inventario real
```
Material (maestro)
├── código
├── nombre
├── unidad
└── costo_unitario

MaterialLot (inventario real - por lote)
├── codigo_lote: "ACE-001-L001"
├── cantidad: 100 kg
├── fecha_entrada: 2024-01-15
├── fecha_caducidad: 2025-01-15 (opcional)
├── ubicacion: "Almacén A-1"
└── notas: "Proveedor XYZ"
```

---

## 🔄 FIFO (First In - First Out)

Cuando se surtidora una Work Order, el sistema:
1. Ordena los lotes por `fecha_entrada` (ascendente = más viejo primero)
2. Consume del lote más antiguo hasta satisfacer la cantidad
3. Si un lote no tiene suficiente, continúa con el siguiente
4. Esto garantiza rotación de inventario

### Ejemplo

**Inventario:**
- Lote A: 50 kg (entrada: 2024-01-01) ← FIFO: Se usa primero
- Lote B: 100 kg (entrada: 2024-01-10)
- Lote C: 75 kg (entrada: 2024-01-20)

**Crear WO que necesita 120 kg:**
```
1. Consumir de Lote A: 50 kg → Lote A queda con 0 kg
2. Consumir de Lote B: 70 kg → Lote B queda con 30 kg
3. ✅ Total consumido: 120 kg
   Stock restante: 30 (Lote B) + 75 (Lote C) = 105 kg
```

---

## 📅 Control de Caducidad

### Alertas Automáticas

**Endpoint especial para ver alertas:**
```
GET /api/materials/lotes/caducidad/alertas
```

Devuelve:
- **Próximos a caducar** (próximos 30 días)
- **Ya caducados** (lotes pasados de fecha)

```json
{
  "proximos_a_caducar": [
    {
      "lote": "ACERO-L002",
      "material": "Acero Inoxidable",
      "cantidad": 45.5,
      "fecha_caducidad": "2024-02-15",
      "dias_para_caducar": 18
    }
  ],
  "ya_caducados": []
}
```

### Monitoreo por Material

```
GET /api/materials/{material_id}/inventario
```

Devuelve resumen completo:
```json
{
  "material_id": 1,
  "codigo": "ACE-001",
  "nombre": "Acero Inoxidable",
  "unidad": "kg",
  "stock_total": 800.0,
  "cantidad_lotes": 5,
  "proximamente_caduca": 1,     ← ⚠️ 1 lote caduca en próximos 30 días
  "ya_caducados": 0,             ← ✅ Ninguno expirado
  "lotes": [
    {
      "id": 1,
      "material_id": 1,
      "codigo_lote": "ACE-001-L001",
      "cantidad": 100.0,
      "fecha_entrada": "2024-01-01T10:30:00",
      "fecha_caducidad": "2025-01-01T10:30:00",
      "ubicacion": "A-1",
      "notas": "Proveedor ABC"
    },
    // ... más lotes
  ]
}
```

---

## 🔧 Cómo Usar (API)

### 1. Crear Material (Maestro)

```bash
POST /api/materials
{
  "codigo": "ACE-001",
  "nombre": "Acero Inoxidable 304",
  "descripcion": "Planchas de acero",
  "unidad": "kg",
  "costo_unitario": 25.50,
  "stock_minimo": 100.0
}
```

**Respuesta:**
```json
{
  "id": 1,
  "codigo": "ACE-001",
  "nombre": "Acero Inoxidable 304",
  "unidad": "kg",
  "costo_unitario": 25.50,
  "stock_minimo": 100.0,
  "created_at": "2024-01-15T10:00:00"
}
```

---

### 2. Registrar Entrada de Material (Crear Lote)

```bash
POST /api/materials/1/lotes
{
  "codigo_lote": "ACE-001-L001",
  "cantidad": 500.0,
  "fecha_caducidad": "2025-01-15",
  "ubicacion": "Almacén A-1",
  "notas": "Compra lote mensal del proveedor ABC"
}
```

**Respuesta:**
```json
{
  "id": 1,
  "material_id": 1,
  "codigo_lote": "ACE-001-L001",
  "cantidad": 500.0,
  "fecha_entrada": "2024-01-15T10:30:00",
  "fecha_caducidad": "2025-01-15T00:00:00",
  "ubicacion": "Almacén A-1",
  "notas": "Compra lote mensual del proveedor ABC",
  "created_at": "2024-01-15T10:30:00"
}
```

---

### 3. Ver Lotes Disponibles (FIFO Order)

```bash
GET /api/materials/1/lotes
```

**Respuesta (ordenada por FIFO):**
```json
[
  {
    "id": 1,
    "codigo_lote": "ACE-001-L001",
    "cantidad": 500.0,
    "fecha_entrada": "2024-01-01T00:00:00",  ← MÁS VIEJO (se usa primero)
    "fecha_caducidad": "2025-01-01T00:00:00"
  },
  {
    "id": 2,
    "codigo_lote": "ACE-001-L002",
    "cantidad": 300.0,
    "fecha_entrada": "2024-01-10T00:00:00",
    "fecha_caducidad": "2025-02-15T00:00:00"
  },
  {
    "id": 3,
    "codigo_lote": "ACE-001-L003",
    "cantidad": 200.0,
    "fecha_entrada": "2024-01-20T00:00:00",  ← MÁS NUEVO (se usa último)
    "fecha_caducidad": null
  }
]
```

---

### 4. Ver Resumen de Inventario

```bash
GET /api/materials/1/inventario
```

**Respuesta:**
```json
{
  "material_id": 1,
  "codigo": "ACE-001",
  "nombre": "Acero Inoxidable",
  "unidad": "kg",
  "stock_total": 1000.0,
  "cantidad_lotes": 3,
  "proximamente_caduca": 1,
  "ya_caducados": 0,
  "lotes": [ ... ]  // Array completo de lotes
}
```

---

### 5. Ver Alertas de Caducidad Global

```bash
GET /api/materials/lotes/caducidad/alertas
```

**Respuesta:**
```json
{
  "proximos_a_caducar": [
    {
      "lote": "ACE-001-L002",
      "material": "Acero Inoxidable",
      "cantidad": 45.5,
      "fecha_caducidad": "2024-02-15T00:00:00",
      "dias_para_caducar": 18
    }
  ],
  "ya_caducados": []
}
```

---

### 6. Actualizar Datos de Lote

```bash
PUT /api/materials/1/lotes/1
{
  "cantidad": 480.0,         // Ajustar cantidad
  "ubicacion": "Almacén B-2", // Cambiar ubicación
  "notas": "Movido a nueva ubicación",
  "fecha_caducidad": "2025-02-01"  // Actualizar caducidad
}
```

---

### 7. Crear Work Order (Valida Lotes)

```bash
POST /api/work-orders
{
  "numero_orden": "WO-2024-001",
  "descripcion": "Producción de piezas A",
  "cantidad_a_producir": 1000.0,
  "items": [
    {
      "material_id": 1,
      "cantidad_requerida": 150.0
    }
  ]
}
```

**Sistema valida:**
- ✅ Material existe
- ✅ Hay lotes disponibles
- ✅ Stock total >= cantidad_requerida

---

### 8. Surtir Work Order (Consume FIFO)

```bash
PUT /api/work-orders/1/status
{
  "status": "surtido"
}
```

**Sistema hace:**
1. Obtiene lotes del material ordenados por `fecha_entrada` (ASC)
2. Consume del lote más viejo primero
3. Reduce cantidad en cada lote
4. Cambia status a "surtido"

**Ejemplo con nuestros lotes:**
- Lote L001 (100 kg) → Consume 100 kg → Queda 0 kg
- Lote L002 (100 kg) → Consume 50 kg → Queda 50 kg
- ✅ Total consumido: 150 kg de los lotes más antiguos

---

### 9. Ver Detalles de Work Order

```bash
GET /api/work-orders/1
```

**Respuesta:**
```json
{
  "id": 1,
  "numero_orden": "WO-2024-001",
  "descripcion": "Producción de piezas A",
  "status": "surtido",
  "cantidad_a_producir": 1000.0,
  "items": [
    {
      "id": 1,
      "work_order_id": 1,
      "material_id": 1,
      "cantidad_requerida": 150.0,
      "cantidad_asignada": 150.0  ← Fue surtida con FIFO
    }
  ],
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:15:00"
}
```

---

## 📋 Endpoints Nuevos/Modificados

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/materials` | Crear material maestro |
| `GET` | `/api/materials` | Listar materiales |
| `GET` | `/api/materials/{id}` | Detalle material |
| `PUT` | `/api/materials/{id}` | Actualizar material |
| `POST` | `/api/materials/{id}/lotes` | Crear/registrar lote (entrada) |
| `GET` | `/api/materials/{id}/lotes` | Listar lotes (FIFO order) |
| `GET` | `/api/materials/{id}/inventario` | Resumen completo con alertas |
| `GET` | `/api/materials/lotes/caducidad/alertas` | Alertas globales de caducidad |
| `PUT` | `/api/materials/{id}/lotes/{lot_id}` | Actualizar lote |
| `DELETE` | `/api/materials/{id}/lotes/{lot_id}` | Eliminar lote |
| `POST` | `/api/materials/{id}/lotes/{lot_id}/usar` | Consumir cantidad (manual) |

---

## 🎯 Flujo Completo ERP Mini v2 (Con Lotes FIFO)

```
1. 📥 ENTRADA DE MATERIAL
   Usuario registra entrada: Material ACE-001, Lote L001, 500 kg, Caducidad: 2025-01-15
   → Sistema crea MaterialLot con fecha_entrada = hoy

2. 📊 VISUALIZAR INVENTARIO
   GET /api/materials/1/inventario
   → Ver stock total, lotes disponibles, alertas de caducidad

3. ⚠️ MONITOREO
   GET /api/materials/lotes/caducidad/alertas
   → Ver qué lotes van a caducar pronto

4. 🏭 CREAR WORK ORDER
   POST /api/work-orders
   → Sistema valida: Material existe + Hay lotes disponibles + Stock suficiente
   → Status inicial: "pendiente"

5. ✂️ SURTIR (FIFO)
   PUT /api/work-orders/{id}/status = "surtido"
   → Sistema consume del lote MÁS VIEJO primero
   → Garantiza rotación automática

6. ⚙️ PRODUCCIÓN
   PUT /api/work-orders/{id}/status = "en_proceso"

7. ✅ FINALIZAR
   PUT /api/work-orders/{id}/status = "finalizado"

8. 📦 REGISTRAR PRODUCTO TERMINADO
   POST /api/finished-products
   → Producto vinculado a WO finalizada
```

---

## 💡 Ventajas de Esta Arquitectura

| Ventaja | Beneficio |
|---------|-----------|
| **FIFO Automático** | Rotación garantizada, evita que se acumulen lotes viejos |
| **Control de Caducidad** | Alertas antes de que expire material → Reduce desperdicio |
| **Trazabilidad** | Cada lote tiene código, fecha entrada, fecha caducidad |
| **Stock por Lote** | Sabes exactamente qué lotes usaste y cuándo |
| **Flexibilidad** | Materiales sin caducidad también soportados (fecha_caducidad = null) |
| **Auditoría** | Historial de movimientos por lote |

---

## 🚀 Próximas Mejoras (Opcional)

- [ ] Historial de movimientos de lotes (auditoría)
- [ ] Reportes de rotación por material
- [ ] Previsión de caducidad (forecast)
- [ ] Costos por lote (para COGS más preciso)
- [ ] Etiquetado QR de lotes
- [ ] Integración con sistema de almacenes

