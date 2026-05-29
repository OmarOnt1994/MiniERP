#!/usr/bin/env python
"""
Script de prueba para la API ERP Mini
Ejecutar: python test_api.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api"
TOKEN = ""

def print_response(response, label="Response"):
    """Imprime respuesta formateada"""
    print(f"\n{'='*60}")
    print(f"📌 {label}")
    print(f"{'='*60}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)
    print(f"Status: {response.status_code}\n")

def test_api():
    global TOKEN
    
    print("\n🔧 INICIANDO PRUEBAS DE API ERP MINI\n")
    
    # 1. Registro
    print("\n1️⃣ Registrando usuario...")
    resp = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": "test@fabrica.com",
            "password": "Test123!",
            "full_name": "Usuario Prueba",
            "role": "admin"
        }
    )
    print_response(resp, "Registro")
    
    # 2. Login
    print("\n2️⃣ Iniciando sesión...")
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": "test@fabrica.com",
            "password": "Test123!"
        }
    )
    if resp.status_code == 200:
        TOKEN = resp.json()["access_token"]
        print(f"✅ Token obtenido: {TOKEN[:50]}...")
    print_response(resp, "Login")
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # 3. Crear material 1
    print("\n3️⃣ Creando material 1 (Acero)...")
    resp = requests.post(
        f"{BASE_URL}/materials",
        json={
            "codigo": "ACE-001",
            "nombre": "Acero Inoxidable",
            "descripcion": "Acero 304",
            "unidad": "kg",
            "stock_minimo": 50.0,
            "costo_unitario": 20.0,
            "ubicacion": "Almacen A"
        },
        headers=headers
    )
    material1_id = resp.json()["id"] if resp.status_code == 200 else 1
    print_response(resp, "Crear Material 1")
    
    # 4. Entrada de material 1
    print("\n4️⃣ Registrando entrada de Acero...")
    resp = requests.post(
        f"{BASE_URL}/materials/{material1_id}/entrada",
        json={
            "cantidad": 500.0,
            "tipo": "entrada",
            "razon": "Compra proveedor"
        },
        headers=headers
    )
    print_response(resp, "Entrada Material 1")
    
    # 5. Crear material 2
    print("\n5️⃣ Creando material 2 (Pintura)...")
    resp = requests.post(
        f"{BASE_URL}/materials",
        json={
            "codigo": "PIN-001",
            "nombre": "Pintura Epoica",
            "descripcion": "Pintura industrial",
            "unidad": "litro",
            "stock_minimo": 20.0,
            "costo_unitario": 15.0,
            "ubicacion": "Almacen B"
        },
        headers=headers
    )
    material2_id = resp.json()["id"] if resp.status_code == 200 else 2
    print_response(resp, "Crear Material 2")
    
    # 6. Entrada de material 2
    print("\n6️⃣ Registrando entrada de Pintura...")
    resp = requests.post(
        f"{BASE_URL}/materials/{material2_id}/entrada",
        json={
            "cantidad": 200.0,
            "tipo": "entrada",
            "razon": "Compra mensual"
        },
        headers=headers
    )
    print_response(resp, "Entrada Material 2")
    
    # 7. Crear Work Order
    print("\n7️⃣ Creando Work Order...")
    resp = requests.post(
        f"{BASE_URL}/work-orders",
        json={
            "numero_orden": f"WO-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "descripcion": "Producción de prueba",
            "cantidad_a_producir": 1000.0,
            "notas": "Prueba de sistema",
            "items": [
                {"material_id": material1_id, "cantidad_requerida": 100.0},
                {"material_id": material2_id, "cantidad_requerida": 50.0}
            ]
        },
        headers=headers
    )
    wo_id = resp.json()["id"] if resp.status_code == 200 else 1
    print_response(resp, "Crear Work Order")
    
    # 8. Listar Work Orders
    print("\n8️⃣ Listando Work Orders...")
    resp = requests.get(f"{BASE_URL}/work-orders", headers=headers)
    print_response(resp, "Listar Work Orders")
    
    # 9. Cambiar a "surtido"
    print("\n9️⃣ Cambiando WO a 'surtido' (descuenta stock)...")
    resp = requests.put(
        f"{BASE_URL}/work-orders/{wo_id}/status",
        json={"status": "surtido"},
        headers=headers
    )
    print_response(resp, "Cambiar Status → Surtido")
    
    # 10. Verificar stock
    print("\n🔟 Verificando stock actualizado...")
    resp = requests.get(f"{BASE_URL}/materials/{material1_id}", headers=headers)
    material1 = resp.json()
    print(f"Stock Acero: {material1['stock_actual']} (fue 500, se descontó 100)")
    print_response(resp, "Verificar Stock")
    
    # 11. Cambiar a "en_proceso"
    print("\n1️⃣1️⃣ Cambiando WO a 'en_proceso'...")
    resp = requests.put(
        f"{BASE_URL}/work-orders/{wo_id}/status",
        json={"status": "en_proceso"},
        headers=headers
    )
    print_response(resp, "Cambiar Status → En Proceso")
    
    # 12. Cambiar a "finalizado"
    print("\n1️⃣2️⃣ Cambiando WO a 'finalizado'...")
    resp = requests.put(
        f"{BASE_URL}/work-orders/{wo_id}/status",
        json={"status": "finalizado"},
        headers=headers
    )
    print_response(resp, "Cambiar Status → Finalizado")
    
    # 13. Crear producto terminado
    print("\n1️⃣3️⃣ Registrando producto terminado...")
    resp = requests.post(
        f"{BASE_URL}/finished-products",
        json={
            "codigo": f"PROD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "nombre": "Piezas de Acero",
            "descripcion": "Lote completo",
            "cantidad_producida": 1000.0,
            "costo_total": 3500.0,
            "work_order_id": wo_id
        },
        headers=headers
    )
    print_response(resp, "Crear Producto Terminado")
    
    # 14. Listar productos
    print("\n1️⃣4️⃣ Listando productos terminados...")
    resp = requests.get(f"{BASE_URL}/finished-products", headers=headers)
    print_response(resp, "Listar Productos Terminados")
    
    print("\n✅ PRUEBAS COMPLETADAS\n")

if __name__ == "__main__":
    try:
        test_api()
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        print("Asegúrate que la API está corriendo: uvicorn app.main:app --reload")
