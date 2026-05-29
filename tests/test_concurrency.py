import os
import sys
import importlib
from pathlib import Path
from threading import Thread, Barrier
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


def test_concurrent_consumption(tmp_path):
    app = _load_app_with_sqlite(tmp_path)

    with TestClient(app) as client:
        headers = _register_and_login(client, "conc@example.com", "Admin123!", "Conc Test", "admin")

        # Crear material y lote con 5 unidades
        m = client.post(
            "/api/materials",
            json={"codigo": "MAT-CONC-1", "nombre": "Conc", "unidad": "u", "stock_minimo": 0},
            headers=headers,
        )
        material_id = m.json()["id"]

        lot = client.post(
            f"/api/materials/{material_id}/lotes",
            json={"codigo_lote": "L-1", "cantidad": 5},
            headers=headers,
        )
        lot_id = lot.json()["id"]

        # Barrier to synchronize threads
        b = Barrier(2)
        results = []

        def worker():
            b.wait()
            resp = client.post(f"/api/materials/{material_id}/lotes/{lot_id}/usar", params={"cantidad": 3}, headers=headers)
            results.append(resp)

        t1 = Thread(target=worker)
        t2 = Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactly one should succeed, the other should fail with 400 (insufficient)
        statuses = [r.status_code for r in results]
        assert statuses.count(200) == 1
        assert statuses.count(400) == 1

        # Verify final lot quantity is 2
        get_lots = client.get(f"/api/materials/{material_id}/lotes", headers=headers)
        assert get_lots.status_code == 200
        remaining = [l for l in get_lots.json() if l["id"] == lot_id][0]["cantidad"]
        assert remaining == 2
