from sqlmodel import Session, select
from app.core.database import engine
from app.models.finished_product import FinishedProductShipment

if __name__ == '__main__':
    with Session(engine) as s:
        rows = s.exec(select(FinishedProductShipment)).all()
        print('ROWS COUNT:', len(rows))
        for r in rows:
            print('id=', r.id, 'finished_product_id=', r.finished_product_id, 'cantidad=', r.cantidad, 'dest=', r.destinatario, 'doc=', r.documento_envio, 'obs=', r.observaciones, 'created_at=', r.created_at)
