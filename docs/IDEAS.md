IDEAS y mejoras para el mini-ERP

Fecha de creación: 2026-05-14

Propósito: backlog vivo para anotar ideas, mejoras y tareas relacionadas con funcionalidad (costos, inventario, producción, reportes, etc.). Usar como lista priorizada antes de crear issues/migraciones/tests.

Nota: cada ítem incluye **Prioridad** (High / Medium / Low) y **Dificultad** (Easy / Medium / Hard).

2) Endpoints de Reporte de Costos (Prioridad: High, Dificultad: Easy)
- Objetivo: exponer datos útiles para frontend y contabilidad.
- Endpoints sugeridos:
  - `GET /api/costs/work-orders/{wo_id}` — costo total consumido, costo por unidad, desglose por material/lot.
  - `GET /api/costs/materials/{material_id}?start=&end=` — consumo en periodo, costo promedio, desglose por lote.
- Tareas:
  - Implementar agregaciones sobre `InventoryMovement` (`sum(total_cost)`, `avg(unit_cost)`, group by lot).
  - Añadir Pydantic response models con `from_attributes=True`.
  - Tests de integración para validar resultados con datos de ejemplo.

3) Consistencia y concurrencia en consumos (Prioridad: High, Dificultad: Medium)
- Objetivo: evitar condiciones de carrera al reservar/consumir lotes en entornos concurrentes.
- Opciones:
  - Usar transacciones y SELECT ... FOR UPDATE (cuando DB lo soporte).
  - Implementar bloqueo optimista con `version` o control de stock en una única transacción.
- Tareas:
  - Envolver consumo en transacción atómica y bloquear filas de `MaterialLot`.
  - Tests que simulan concurrencia para asegurar integridad.

4) Autenticación y control de accesos (RBAC) (Prioridad: High, Dificultad: Medium)
- Objetivo: controlar quién puede crear lotes, consumir materiales y finalizar WOs.
- Tareas:
  - Implementar auth (JWT) y roles básicos (`admin`, `planner`, `operator`).
  - Añadir checks en routers críticos (`materials`, `work_orders`).

5) Auditoría y trazabilidad (Prioridad: Medium, Dificultad: Easy)
- Objetivo: registrar `created_by`, `updated_by`, timestamps en movimientos y lotes.
- Tareas:
  - Añadir campos y poblar desde el contexto de usuario autenticado.
  - Exportar auditoría a CSV/JSON para contabilidad cuando sea necesario.

6) Métodos de valoración de inventario (FIFO/Promedio/LIFO) (Prioridad: Medium, Dificultad: Medium)
- Objetivo: soportar políticas de valoración configurables por empresa o material.
- Tareas:
  - Implementar estrategia abstracta para seleccionar lotes (FIFO por defecto).
  - Añadir opción para promedio ponderado y (opcional) LIFO.
  - Añadir tests que verifiquen resultados históricos y reportes.

7) Reportes avanzados y alertas (Prioridad: Medium, Dificultad: Medium)
- Objetivo: detectar variaciones y generar reportes periódicos.
- Tareas:
  - Job cron para reportes semanales de variación de costo.
  - Alertas cuando costo por lote difiera más de X% del costo maestro.

8) CI/CD y migraciones automatizadas (Prioridad: Medium, Dificultad: Easy)
- Objetivo: asegurar tests en PRs y mantener migraciones sincronizadas.
- Tareas:
  - Añadir workflow de GitHub Actions (tests en Python 3.12) — ya creado.
  - Añadir job para validar que `alembic upgrade head` aplica en la base de datos de CI (opcional con Postgres service).

9) Frontend MVP (Prioridad: Low, Dificultad: Medium)
- Objetivo: paneles y formularios mínimos para operar inventario y producción.
- Pila sugerida: React + Vite o Vue + Vite; consumir endpoints de la API.

10) Exportes e integración contable (Prioridad: Low, Dificultad: Medium)
- Objetivo: generar archivos para contabilidad o integrar con un sistema contable.
- Tareas:
  - Export CSV/XLSX de movimientos y reportes.
  - API para exportar asientos contables de cierre de periodo (formato configurable).

11) Costeo completo de producción e indirectos (Prioridad: Low, Dificultad: Hard)
- Objetivo: permitir capturar mano de obra, gastos generales y asignarlos por WO.
- Tareas:
  - Modelar recursos y horas por WO.
  - Reglas de asignación de costos indirectos.

12) UI / Dashboard avanzado y KPIs (Prioridad: Low, Dificultad: Medium)
- Objetivo: mostrar margen estimado por producto, KPIs y visualizaciones.

--
Puedes pedirme que transforme cualquier ítem en una lista de tareas más detallada, genere PRs/migraciones/tests para un ítem concreto, o que empiece a implementar el siguiente paso.
