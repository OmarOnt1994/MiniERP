from pathlib import Path
import os
import sys
import importlib
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


def test_costs_report_endpoints(tmp_path):
    app = _load_app_with_sqlite(tmp_path)

    with TestClient(app) as client:
        headers = _register_and_login(
            client, "admin_report@example.com", "Admin123!", "Admin Report", "admin"
        )

        # Crear material y lote
        material_resp = client.post(
            "/api/materials",
            json={
                "codigo": "MAT-R-001",
                "nombre": "Material Report",
                "unidad": "kg",
                "stock_minimo": 0,
                "costo_unitario": 5.0,
            },
            headers=headers,
        )
        assert material_resp.status_code == 200, material_resp.text
        material_id = material_resp.json()["id"]

        lot_resp = client.post(
            f"/api/materials/{material_id}/lotes",
            json={
                "codigo_lote": "MAT-R-001-L001",
                "cantidad": 30,
                "costo_unitario": 6.0,
            },
            headers=headers,
        )
        assert lot_resp.status_code == 200, lot_resp.text
        lot_id = lot_resp.json()["id"]

        # Crear Work Order que consume 10 unidades
        wo_resp = client.post(
            "/api/work-orders",
            json={
                "numero_orden": "WO-R-001",
                "descripcion": "WO for report test",
                "cantidad_a_producir": 10,
                "items": [
                    {
                        "material_id": material_id,
                        "cantidad_requerida": 10,
                        "lotes_seleccionados": [{"material_lot_id": lot_id, "cantidad": 10}],
                    }
                ],
            },
            headers=headers,
        )
        assert wo_resp.status_code == 200, wo_resp.text
        wo_id = wo_resp.json()["id"]

        # Surtir y finalizar WO para registrar consumos
        surtido = client.put(f"/api/work-orders/{wo_id}/status", json={"status": "surtido"}, headers=headers)
        assert surtido.status_code == 200, surtido.text
        finalizado = client.put(f"/api/work-orders/{wo_id}/status", json={"status": "finalizado"}, headers=headers)
        assert finalizado.status_code == 200, finalizado.text

        # Llamar endpoint de WO
        wo_costs = client.get(f"/api/costs/work-orders/{wo_id}", headers=headers)
        assert wo_costs.status_code == 200, wo_costs.text
        wo_json = wo_costs.json()
        assert wo_json["work_order_id"] == wo_id
        assert wo_json["total_cost"] is not None
        assert len(wo_json["by_material"]) >= 1

        # Llamar endpoint de material
        mat_costs = client.get(f"/api/costs/materials/{material_id}", headers=headers)
        assert mat_costs.status_code == 200, mat_costs.text
        mat_json = mat_costs.json()
        assert mat_json["material_id"] == material_id
        assert mat_json["period_total_cost"] is not None
        assert isinstance(mat_json["by_lot"], list)
