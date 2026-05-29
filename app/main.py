from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import create_db_and_tables
from app.routers import auth, materials, work_orders, requisitions, storage
from app.routers import costs

app = FastAPI(title="MiniERP - Sistema de Gestión de Fábrica")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: especificar orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(materials.router, prefix="/api", tags=["materials"])
app.include_router(work_orders.router, prefix="/api", tags=["work-orders"])
app.include_router(work_orders.finished_router, prefix="/api", tags=["finished-products"])
app.include_router(costs.router, prefix="/api", tags=["costs"])
app.include_router(requisitions.router, prefix="/api", tags=["requisitions"])
app.include_router(storage.router, prefix="/api", tags=["storage"])

@app.get("/")
def root():
    return {"message": "MiniERP - API corriendo", "version": "1.0"}