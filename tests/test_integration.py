import os
import sys
import importlib
from pathlib import Path

from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_app_with_sqlite(tmp_path):
    db_path = tmp_path / "mini_erp_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["ALGORITHM"] = "HS256"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "1440"

    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

    # Clear any previously loaded app modules to ensure a fresh DB engine per test
    for name in list(sys.modules.keys()):
        if name.startswith("app"):
            del sys.modules[name]

    app_main = importlib.import_module("app.main")
    return app_main.app


def _register_and_login(client, email, password, full_name, role):
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role,
        },
    )
    assert register_response.status_code == 200, register_response.text

    login_response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_flow_material_to_shipment(tmp_path):
    app = _load_app_with_sqlite(tmp_path)

    with TestClient(app) as client:
        headers = _register_and_login(
            client,
            "admin@example.com",
            "Admin123!",
            "Admin Test",
            "admin",
        )

        material_response = client.post(
            "/api/materials",
            json={
                "codigo": "MAT-001",
                "nombre": "Acero Inoxidable",
                "descripcion": "Lote para prueba",
                "unidad": "kg",
                "stock_minimo": 10,
                "costo_unitario": 25.5,
            },
            headers=headers,
        )
        assert material_response.status_code == 200, material_response.text
        material_id = material_response.json()["id"]

        lot_response = client.post(
            f"/api/materials/{material_id}/lotes",
            json={
                "codigo_lote": "MAT-001-L001",
                "cantidad": 100,
                "fecha_caducidad": None,
                "ubicacion": "A1",
                "notas": "Lote inicial",
            },
            headers=headers,
        )
        assert lot_response.status_code == 200, lot_response.text
        lot_id = lot_response.json()["id"]

        wo_response = client.post(
            "/api/work-orders",
            json={
                "numero_orden": "WO-001",
                "descripcion": "Producción de prueba",
                "cantidad_a_producir": 50,
                "items": [
                    {
                        "material_id": material_id,
                        "cantidad_requerida": 20,
                        "lotes_seleccionados": [
                            {"material_lot_id": lot_id, "cantidad": 20}
                        ],
                    }
                ],
            },
            headers=headers,
        )
        assert wo_response.status_code == 200, wo_response.text
        wo_id = wo_response.json()["id"]

        surtido_response = client.put(
            f"/api/work-orders/{wo_id}/status",
            json={"status": "surtido"},
            headers=headers,
        )
        assert surtido_response.status_code == 200, surtido_response.text
        assert surtido_response.json()["status"] == "surtido"

        finalizado_response = client.put(
            f"/api/work-orders/{wo_id}/status",
            json={"status": "finalizado"},
            headers=headers,
        )
        assert finalizado_response.status_code == 200, finalizado_response.text
        assert finalizado_response.json()["status"] == "finalizado"

        finished_products_response = client.get("/api/finished-products", headers=headers)
        assert finished_products_response.status_code == 200, finished_products_response.text
        finished_products = finished_products_response.json()
        assert len(finished_products) == 1
        assert finished_products[0]["work_order_id"] == wo_id
        assert finished_products[0]["cantidad_disponible"] == 50

        shipment_response = client.post(
            "/api/finished-products/shipments",
            json={
                "finished_product_id": finished_products[0]["id"],
                "cantidad": 10,
                "destinatario": "Cliente Demo",
                "documento_envio": "ENV-001",
                "observaciones": "Salida de prueba",
            },
            headers=headers,
        )
        assert shipment_response.status_code == 200, shipment_response.text

        updated_product_response = client.get(
            f"/api/finished-products/{finished_products[0]['id']}",
            headers=headers,
        )
        assert updated_product_response.status_code == 200, updated_product_response.text
        assert updated_product_response.json()["cantidad_disponible"] == 40

        movements_response = client.get(
            "/api/materials/movimientos/reporte",
            headers=headers,
        )
        assert movements_response.status_code == 200, movements_response.text
        report = movements_response.json()
        assert report["summary"]["total_movements"] >= 1


def test_lectura_cannot_create_material(tmp_path):
    app = _load_app_with_sqlite(tmp_path)

    with TestClient(app) as client:
        headers = _register_and_login(
            client,
            "reader@example.com",
            "Reader123!",
            "Reader Test",
            "lectura",
        )

        response = client.post(
            "/api/materials",
            json={
                "codigo": "MAT-002",
                "nombre": "Material Bloqueado",
                "descripcion": "No debe crear",
                "unidad": "kg",
                "stock_minimo": 1,
                "costo_unitario": 1.0,
            },
            headers=headers,
        )
        assert response.status_code == 403


def test_costs_persistence(tmp_path):
    app = _load_app_with_sqlite(tmp_path)

    with TestClient(app) as client:
        headers = _register_and_login(
            client, "admin_costs@example.com", "Admin123!", "Admin Costs", "admin"
        )

        # Crear material con costo maestro
        material_resp = client.post(
            "/api/materials",
            json={
                "codigo": "MAT-C-001",
                "nombre": "Material Cost Test",
                "unidad": "kg",
                "stock_minimo": 0,
                "costo_unitario": 10.0,
            },
            headers=headers,
        )
        assert material_resp.status_code == 200, material_resp.text
        material_id = material_resp.json()["id"]

        # Crear lote con costo específico
        lot_resp = client.post(
            f"/api/materials/{material_id}/lotes",
            json={
                "codigo_lote": "MAT-C-001-L001",
                "cantidad": 20,
                "costo_unitario": 12.0,
                "ubicacion": "T1",
            },
            headers=headers,
        )
        assert lot_resp.status_code == 200, lot_resp.text
        lot_id = lot_resp.json()["id"]

        # Crear Work Order que consume 5 unidades y produce 5
        wo_resp = client.post(
            "/api/work-orders",
            json={
                "numero_orden": "WO-COST-001",
                "descripcion": "WO for cost test",
                "cantidad_a_producir": 5,
                "items": [
                    {
                        "material_id": material_id,
                        "cantidad_requerida": 5,
                        "lotes_seleccionados": [{"material_lot_id": lot_id, "cantidad": 5}],
                    }
                ],
            },
            headers=headers,
        )
        assert wo_resp.status_code == 200, wo_resp.text
        wo_id = wo_resp.json()["id"]

        # Surtir WO
        surtido = client.put(f"/api/work-orders/{wo_id}/status", json={"status": "surtido"}, headers=headers)
        assert surtido.status_code == 200, surtido.text

        # Finalizar WO
        finalizado = client.put(f"/api/work-orders/{wo_id}/status", json={"status": "finalizado"}, headers=headers)
        assert finalizado.status_code == 200, finalizado.text

        # Verificar producto terminado y su costo total
        fps = client.get("/api/finished-products", headers=headers)
        assert fps.status_code == 200, fps.text
        fps_json = fps.json()
        assert len(fps_json) == 1
        fp = fps_json[0]
        assert fp["work_order_id"] == wo_id
        # costo esperado = 5 * 12.0
        assert fp["costo_total"] == 5 * 12.0

        # Verificar movimientos usando el endpoint de reporte: debe existir consumo con unit_cost y total_cost
        movs = client.get("/api/materials/movimientos/reporte", headers=headers)
        assert movs.status_code == 200, movs.text
        report = movs.json()
        movements = report.get("movements", [])
        consumo_movs = [m for m in movements if m["movement_type"] == "consumo" and m.get("material_lot_id") == lot_id]
        assert len(consumo_movs) >= 1
        found = False
        for m in consumo_movs:
            if m.get("unit_cost") is not None:
                assert abs(m.get("unit_cost") - 12.0) < 1e-6
                assert abs((m.get("total_cost") or 0.0) - 60.0) < 1e-6
                found = True
        assert found, "No se encontró movimiento de consumo con costos registrados"


def test_partial_finished_product_flow(tmp_path):
    app = _load_app_with_sqlite(tmp_path)

    with TestClient(app) as client:
        headers = _register_and_login(
            client,
            "partial@example.com",
            "Admin123!",
            "Partial Production",
            "admin",
        )

        material_response = client.post(
            "/api/materials",
            json={
                "codigo": "MAT-P-001",
                "nombre": "Material Parcial",
                "unidad": "kg",
                "stock_minimo": 0,
                "costo_unitario": 15.0,
            },
            headers=headers,
        )
        assert material_response.status_code == 200, material_response.text
        material_id = material_response.json()["id"]

        lot_response = client.post(
            f"/api/materials/{material_id}/lotes",
            json={
                "codigo_lote": "MAT-P-001-L001",
                "cantidad": 100,
                "ubicacion": "P1",
            },
            headers=headers,
        )
        assert lot_response.status_code == 200, lot_response.text
        lot_id = lot_response.json()["id"]

        wo_response = client.post(
            "/api/work-orders",
            json={
                "numero_orden": "WO-PARTIAL-001",
                "descripcion": "Orden grande por etapas",
                "cantidad_a_producir": 50,
                "items": [
                    {
                        "material_id": material_id,
                        "cantidad_requerida": 20,
                        "lotes_seleccionados": [
                            {"material_lot_id": lot_id, "cantidad": 20}
                        ],
                    }
                ],
            },
            headers=headers,
        )
        assert wo_response.status_code == 200, wo_response.text
        wo_id = wo_response.json()["id"]

        surtido_response = client.put(
            f"/api/work-orders/{wo_id}/status",
            json={"status": "surtido"},
            headers=headers,
        )
        assert surtido_response.status_code == 200, surtido_response.text

        partial_1 = client.post(
            f"/api/work-orders/{wo_id}/finished-products",
            json={
                "codigo": "FP-PARTIAL-001",
                "nombre": "Producto Parcial",
                "cantidad_producida": 20,
                "cantidad_disponible": 20,
            },
            headers=headers,
        )
        assert partial_1.status_code == 200, partial_1.text

        summary_response = client.get(f"/api/work-orders/{wo_id}/production-summary", headers=headers)
        assert summary_response.status_code == 200, summary_response.text
        summary = summary_response.json()
        assert summary["cantidad_producida"] == 20
        assert summary["cantidad_pendiente"] == 30
        assert summary["esta_completa"] is False

        finalizado_prematuro = client.put(
            f"/api/work-orders/{wo_id}/status",
            json={"status": "finalizado"},
            headers=headers,
        )
        assert finalizado_prematuro.status_code == 400, finalizado_prematuro.text

        partial_2 = client.post(
            f"/api/work-orders/{wo_id}/finished-products",
            json={
                "codigo": "FP-PARTIAL-002",
                "nombre": "Producto Parcial",
                "cantidad_producida": 30,
                "cantidad_disponible": 30,
            },
            headers=headers,
        )
        assert partial_2.status_code == 200, partial_2.text

        finalizado_response = client.put(
            f"/api/work-orders/{wo_id}/status",
            json={"status": "finalizado"},
            headers=headers,
        )
        assert finalizado_response.status_code == 200, finalizado_response.text
        assert finalizado_response.json()["status"] == "finalizado"

        fps_response = client.get("/api/finished-products", headers=headers)
        assert fps_response.status_code == 200, fps_response.text
        fps = [fp for fp in fps_response.json() if fp["work_order_id"] == wo_id]
        assert len(fps) == 2
