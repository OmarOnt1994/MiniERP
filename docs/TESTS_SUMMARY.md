Resumen de fallo de tests y solución aplicada

Fecha: 2026-05-14

Descripción breve:

- Al ejecutar los tests de integración se produjo un error de validación de Pydantic durante la serialización del reporte de movimientos de inventario (InventoryMovementReportResponse).
- Error inicial: `pydantic_core._pydantic_core.ValidationError` con varios errores de validación al intentar convertir objetos ORM (instancias de SQLModel) a modelos Pydantic.
- Además se encontraron problemas de instalación de dependencias en el entorno virtual inicial relacionados con la compilación de `pydantic-core` en Python 3.14; se solucionó creando/usiando un venv con Python 3.12.

Qué hice para diagnosticar:

1. Revisé los modelos y esquemas relacionados: `app/models/material.py`, `app/models/finished_product.py`, `app/schemas/material.py`.
2. Ejecuté los tests fallando localmente para obtener la traza completa de error.
3. Identifiqué que FastAPI/Pydantic estaban intentando validar objetos ORM contra los Pydantic models sin permitir lectura desde atributos.

Cambios realizados:

- Modifiqué `app/schemas/material.py` y añadí `model_config = {"from_attributes": True}` en los modelos:
  - `InventoryMovementRead`
  - `InventoryMovementReportSummary`
  - `InventoryMovementReportResponse`
  Esto permite que Pydantic construya los modelos desde instancias ORM (objetos SQLModel) en lugar de esperar dicts.

- Añadí campos de costo al modelo `MaterialLot` y a `InventoryMovement` en `app/models/material.py`:
  - `MaterialLot.costo_unitario`, `MaterialLot.costo_total`
  - `InventoryMovement.unit_cost`, `InventoryMovement.total_cost`

- Actualicé `app/routers/materials.py` y `app/routers/work_orders.py` para:
  - Guardar el costo en la creación de lotes.
  - Registrar `unit_cost` y `total_cost` en movimientos de `entrada` y `consumo`.
  - Calcular y asignar `FinishedProduct.costo_total` al finalizar una Work Order, sumando los `total_cost` de los movimientos de consumo asociados.

Problemas de entorno y soluciones:

- Error al instalar `pydantic-core` en Python 3.14 (compilación Rust fallando). Solución aplicada: crear y usar un entorno virtual con Python 3.12 (`.venv312`) e instalar allí las dependencias desde `requirements.txt`.
- Instalé localmente dependencias faltantes durante la ejecución de tests (por ejemplo `sqlmodel`, `pydantic-settings`, `python-multipart`, `email-validator`, `python-jose`, `passlib`, `bcrypt`) para poder reproducir los tests en este entorno.

Verificación:

- Ejecuté el test problemático: `tests/test_integration.py::test_full_flow_material_to_shipment` — ahora pasa.
- Corrí la suite de tests y actualmente quedan advertencias, pero el fallo de validación fue resuelto.

Pasos siguientes recomendados:

- Generar una migración Alembic para agregar las nuevas columnas en la base de datos (`MaterialLot` y `InventoryMovement`).
- Añadir tests que verifiquen la correcta persistencia de `unit_cost`/`total_cost` y el cálculo de `FinishedProduct.costo_total`.
- Añadir endpoints de reporte de costos (por WO, por material, por periodo) si se desea análisis de costos más avanzado.

Comandos útiles para reproducir localmente:

```powershell
# Crear y activar venv con Python 3.12
py -3.12 -m venv .venv312
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv312\Scripts\Activate.ps1

# Actualizar pip y herramientas
python -m pip install -U pip setuptools wheel

# Instalar dependencias
python -m pip install -r requirements.txt

# Ejecutar tests (filtrar solo el test fallido para verificar)
python -m pytest tests/test_integration.py::test_full_flow_material_to_shipment -q
```

Archivos modificados relevantes:

- `app/models/material.py`
- `app/schemas/material.py`
- `app/routers/materials.py`
- `app/routers/work_orders.py`

Si quieres, puedo generar la migración Alembic ahora y/o añadir tests que confirmen el cálculo de costos. Indica qué prefieres como siguiente paso.
