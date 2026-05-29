# ERP Mini - Sistema de Gestión de Fábrica

Sistema ERP minimalista para gestión de inventario, órdenes de trabajo (Work Orders) y productos terminados.

## Características

✅ **Gestión de Materiales por Lotes**
- Registro de entrada por lote (código, cantidad, fecha caducidad)
- Control de caducidad con alertas automáticas
- Soporte para materiales sin fecha de caducidad

✅ **FIFO Automático**
- Al surtir Work Orders, consume del lote más viejo primero
- Garantiza rotación de inventario
- Previene acumulación de material antiguo

✅ **Work Orders (Órdenes de Trabajo)**
- Crear WO con validación de lotes disponibles
- Status: pendiente → surtido → en_proceso → finalizado
- Al cambiar a "surtido", descuenta automáticamente del lote más antiguo (FIFO)

✅ **Productos Terminados**
- Inventario separado de materia prima
- Entrada automática al finalizar una WO
- Salida por envío o despacho
- Trazabilidad por lote de producción

✅ **Seguridad Operativa**
- Roles por proceso: almacen, produccion, despachos, admin
- Reserva de materiales al crear WO
- Auditoría de movimientos de inventario

✅ **Autenticación**
- Registro de usuarios
- Login con JWT
- Roles: admin, almacen, produccion, despachos, lectura

## Instalación

### 1. Clonar repositorio
```bash
cd ERP_mini
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/Scripts/activate  # Windows
# o
source venv/bin/activate      # Linux/Mac
```

### Entorno recomendado

Recomendamos usar Python 3.12 para evitar problemas con compilaciones de dependencias nativas (por ejemplo `pydantic-core`). Si tienes varias versiones instaladas puedes crear y activar un venv específico así:

```powershell
# Crear venv con Python 3.12 en Windows (si `py -3.12` está disponible)
py -3.12 -m venv .venv312
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv312\Scripts\Activate.ps1

# Luego instalar dependencias
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt
```

Motivo: algunas librerías (p. ej. `pydantic-core`) incluyen componentes nativos que requieren ruedas (wheels) precompiladas para la versión de Python. Usar Python 3.12 evita la necesidad de compilar desde código fuente en la mayoría de los entornos y hace la instalación más fiable.

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus valores
```

### 5. Ejecutar aplicación
```bash
uvicorn app.main:app --reload
```

La API estará disponible en: **http://localhost:8000**
- Documentación interactiva: **http://localhost:8000/docs**

## Flujo de Uso

### 1. Crear usuario y autenticarse
```bash
POST /api/auth/register
{
  "email": "usuario@empresa.com",
  "password": "contraseña",
  "full_name": "Juan Pérez",
  "role": "admin"
}

POST /api/auth/login
{
  "username": "usuario@empresa.com",
  "password": "contraseña"
}
# Recibirás: access_token
```

### 2. Crear material (maestro)
```bash
POST /api/materials
{
  "codigo": "ACE-001",
  "nombre": "Acero Inoxidable",
  "descripcion": "Acero 304",
  "unidad": "kg",
  "stock_minimo": 100.0,
  "costo_unitario": 15.50
}
```

### 3. Registrar entrada de material (por lote)
```bash
POST /api/materials/1/lotes
{
  "codigo_lote": "ACE-001-L001",
  "cantidad": 500.0,
  "fecha_caducidad": "2025-01-15",
  "ubicacion": "Almacén A-1",
  "notas": "Compra a proveedor ABC"
}
```

### 4. Ver lotes disponibles (FIFO order)
```bash
GET /api/materials/1/lotes
# Devuelve lotes ordenados por fecha_entrada (más viejo primero)
```

### 5. Ver alertas de caducidad
```bash
GET /api/materials/lotes/caducidad/alertas
# Muestra lotes próximos a caducar o ya caducados
```

### 6. Ver resumen de inventario
```bash
GET /api/materials/1/inventario
# Stock total, cantidad de lotes, alertas, detalles completos
```

### 7. Crear Work Order
```bash
POST /api/work-orders
{
  "numero_orden": "WO-2024-001",
  "descripcion": "Producción de piezas A",
  "cantidad_a_producir": 1000.0,
  "items": [
    {
      "material_id": 1,
      "cantidad_requerida": 150.0,
      "lotes_seleccionados": [
        {
          "material_lot_id": 1,
          "cantidad": 100.0
        },
        {
          "material_lot_id": 2,
          "cantidad": 50.0
        }
      ]
    }
  ]
}
```

Si no envías `lotes_seleccionados`, el sistema usa FIFO automáticamente con los lotes más viejos primero. En la respuesta de la WO verás cada material con `codigo`, `nombre`, `unidad` y los lotes utilizados.

### 8. Surtir Work Order (Consume FIFO automático)
```bash
PUT /api/work-orders/1/status
{
  "status": "surtido"
}
# Sistema consume del lote más viejo primero (FIFO)
```

## Estructura del Proyecto

```
app/
├── core/
│   ├── config.py       # Configuración y variables de entorno
│   ├── database.py     # Conexión a BD
│   └── security.py     # Hashing y JWT
├── models/
│   ├── user.py         # Modelo Usuario
│   ├── material.py     # Modelo Material
│   ├── work_order.py   # Modelos WorkOrder, WorkOrderItem
│   └── finished_product.py
├── schemas/
│   ├── user.py         # Schemas de entrada/salida
│   ├── material.py
│   ├── work_order.py
│   └── finished_product.py
├── routers/
│   ├── auth.py         # Endpoints de autenticación
│   ├── materials.py    # Endpoints de inventario
│   └── work_orders.py  # Endpoints de WO y productos
└── main.py             # Punto de entrada
```

## API Endpoints

### Autenticación
- `POST /api/auth/register` - Registrar usuario
- `POST /api/auth/login` - Iniciar sesión

### Materiales
- `POST /api/materials` - Crear material (maestro)
- `GET /api/materials` - Listar materiales
- `GET /api/materials/{id}` - Detalle de material
- `PUT /api/materials/{id}` - Actualizar material
- `POST /api/materials/{id}/lotes` - Registrar entrada (crear lote)
- `GET /api/materials/{id}/lotes` - Listar lotes (FIFO order)
- `GET /api/materials/{id}/inventario` - Resumen con alertas
- `GET /api/materials/lotes/caducidad/alertas` - Alertas globales
- `PUT /api/materials/{id}/lotes/{lot_id}` - Actualizar lote
- `DELETE /api/materials/{id}/lotes/{lot_id}` - Eliminar lote

### Work Orders
- `POST /api/work-orders` - Crear WO (valida stock y permite elegir lotes)
- `GET /api/work-orders` - Listar WO
- `GET /api/work-orders/{id}` - Detalle de WO
- `PUT /api/work-orders/{id}/status` - Cambiar status

### Productos Terminados
- `POST /api/finished-products` - Registrar producto terminado manualmente
- `GET /api/finished-products` - Listar inventario de productos terminados
- `GET /api/finished-products/{id}` - Detalle de producto terminado
- `POST /api/finished-products/shipments` - Registrar envío/salida y descontar stock
- `GET /api/finished-products/shipments` - Listar envíos

### Auditoría
- `GET /api/materials/movimientos` - Historial de movimientos de inventario
- `GET /api/materials/movimientos/reporte` - Reporte filtrable con resumen

## Validaciones Importantes

⚠️ **Al crear Work Order:**
- Todos los materiales deben existir en la BD
- Debe haber lotes disponibles con stock suficiente (disponible = cantidad - reservada)
- El sistema reserva stock al crear la WO para evitar que otra orden use el mismo lote

⚠️ **Al cambiar a "surtido":**
- Descuenta automáticamente de las reservas hechas al crear la WO
- Si la WO fue creada sin selección manual, se reserva usando FIFO

⚠️ **Al registrar entrada:**
- Crear lote con código único por material
- Fecha caducidad (opcional) debe ser futura
- Se registra automáticamente fecha_entrada = hoy

⚠️ **Permisos:**
- `almacen`: materiales, lotes y ajustes de inventario
- `produccion`: WO y finalización
- `despachos`: salidas de producto terminado
- `admin`: acceso total

⚠️ **Alertas de caducidad:**
- Lotes próximos a caducar (próximos 30 días)
- Lotes ya caducados (para descarte)

⚠️ **Al registrar Producto Terminado:**
- La Work Order debe estar en status "finalizado"
- Al finalizar la WO, el sistema crea automáticamente el inventario del producto terminado

⚠️ **Al registrar un envío:**
- Solo se puede descontar del inventario de producto terminado
- No afecta el inventario de materia prima
- Si no hay cantidad disponible, el sistema rechaza el envío

### Reporte de movimientos

Ejemplo:
```bash
GET /api/materials/movimientos/reporte?inventory_type=material&movement_type=reserva&start_date=2026-05-01T00:00:00&end_date=2026-05-31T23:59:59
```

Filtros disponibles:
- `start_date`
- `end_date`
- `inventory_type` (`material` o `finished_product`)
- `movement_type` (`entrada`, `reserva`, `consumo`, `salida`, `ajuste`)
- `material_id`
- `finished_product_id`
- `work_order_id`

El reporte devuelve:
- `summary` con totales y cantidades por tipo de movimiento
- `movements` con el detalle ordenado del más reciente al más antiguo

## Próximas Mejoras

- [ ] Historial de movimientos de lotes (auditoría)
- [ ] Reportes de rotación por material
- [ ] Previsión de caducidad (forecast)
- [ ] Etiquetado QR de lotes
- [ ] Integración con sistema de almacenes
- [ ] Costos por lote (para COGS más preciso)
- [ ] Frontend web (React/Vue)

## Migraciones (Alembic)

Se configuró `alembic/env.py` para leer `DATABASE_URL` desde `.env` y usar `SQLModel.metadata`.

Para generar la migración inicial y aplicarla (ejecuta con el venv activado desde `C:\proyectos\ERP_mini`):

```powershell
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Después de aplicar las migraciones, siembra datos iniciales (admin):

```powershell
python scripts/seed_initial_data.py
```

El script crea `admin@mini.erp` con contraseña `Admin123!` (cámbiala después).

## Tecnologías

- **Framework:** FastAPI
- **ORM:** SQLModel (SQLAlchemy + Pydantic)
- **Base de datos:** SQLite (configurable)
- **Autenticación:** JWT + Passlib
- **Validación:** Pydantic v2

---

**Autor:** ERP Mini Development  
**Versión:** 1.0  
**Licencia:** MIT

## Quick demo (arranque rápido)

Si quieres mostrar la app rápidamente en otra máquina, estos son los pasos mínimos:

1. Crear/activar venv e instalar dependencias:

```powershell
py -3.12 -m venv .venv312
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv312\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

2. Iniciar backend y frontend (dos terminales):

```powershell
# Backend
$env:PYTHONPATH='c:\proyectos\ERP_mini'
& .\.venv312\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Frontend (desde carpeta frontend)
cd frontend
npm run dev
```

3. Credenciales de demo rápido (si ejecutas `scripts/seed_initial_data.py`):

- Usuario: `admin@mini.erp`
- Contraseña: `1234`

4. Abrir UI: http://localhost:5173 — inicia sesión y usa el menú lateral "Buscar material".

Notas:
- Si prefieres usar Docker o desplegar en un servidor, puedo añadir `docker-compose` y workflows de CI.
