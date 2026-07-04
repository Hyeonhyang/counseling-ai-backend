from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Client, Session
from app.schemas import ClientCreate, ClientResponse
from app.auth import get_current_counselor_id

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("")
def list_clients(search: str = "", counselor_id: int = Depends(get_current_counselor_id), db: DBSession = Depends(get_db)):
    """내 내담자 목록만 조회 + 최신 위기 레벨"""
    query = db.query(Client).filter(Client.counselor_id == counselor_id)
    if search:
        query = query.filter(Client.name.contains(search))
    clients = query.order_by(Client.created_at.desc()).all()

    result = []
    for c in clients:
        latest_session = db.query(Session).filter(
            Session.client_id == c.id
        ).order_by(Session.session_number.desc()).first()

        client_data = {
            "id": c.id,
            "name": c.name,
            "age": c.age,
            "gender": c.gender,
            "presenting_issue": c.presenting_issue or "",
            "notes": c.notes or "",
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "latest_risk_level": latest_session.risk_level if latest_session and latest_session.risk_level else "none",
        }
        result.append(client_data)

    return result


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, counselor_id: int = Depends(get_current_counselor_id), db: DBSession = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id, Client.counselor_id == counselor_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("", response_model=ClientResponse)
def create_client(data: ClientCreate, counselor_id: int = Depends(get_current_counselor_id), db: DBSession = Depends(get_db)):
    client = Client(**data.model_dump(), counselor_id=counselor_id)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(client_id: int, data: ClientCreate, counselor_id: int = Depends(get_current_counselor_id), db: DBSession = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id, Client.counselor_id == counselor_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    for key, val in data.model_dump().items():
        setattr(client, key, val)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}")
def delete_client(client_id: int, counselor_id: int = Depends(get_current_counselor_id), db: DBSession = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id, Client.counselor_id == counselor_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.query(Session).filter(Session.client_id == client_id).delete()
    db.delete(client)
    db.commit()
    return {"success": True}


@router.get("/{client_id}/summary")
def get_client_summary(client_id: int, counselor_id: int = Depends(get_current_counselor_id), db: DBSession = Depends(get_db)):
    """내담자 요약"""
    client = db.query(Client).filter(Client.id == client_id, Client.counselor_id == counselor_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    sessions = db.query(Session).filter(
        Session.client_id == client_id
    ).order_by(Session.session_number).all()

    return {
        "total_sessions": len(sessions),
        "sessions": [
            {
                "session_number": s.session_number,
                "depression": s.depression_score,
                "anxiety": s.anxiety_score,
                "anger": s.anger_score,
                "self_esteem": s.self_esteem_score,
                "date": s.session_date.isoformat() if s.session_date else None,
                "technique": s.technique_used,
            }
            for s in sessions
        ]
    }
