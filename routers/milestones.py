from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database import Milestone, Activity, get_session

router = APIRouter(prefix="/api/milestones", tags=["milestones"])


@router.post("/{milestone_id}/toggle")
def toggle_milestone(
    milestone_id: int,
    session: Session = Depends(get_session),
):
    milestone = session.get(Milestone, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Hito no encontrado")

    milestone.completado = not milestone.completado

    if milestone.completado:
        milestone.fecha_completado = datetime.utcnow()
    else:
        milestone.fecha_completado = None

    session.add(milestone)
    session.commit()
    session.refresh(milestone)

    action = "completado" if milestone.completado else "desmarcado"
    activity = Activity(
        project_id=milestone.project_id,
        descripcion=f"Hito {action}: {milestone.nombre}"
    )
    session.add(activity)
    session.commit()

    return {
        "completado": milestone.completado,
        "fecha_completado": milestone.fecha_completado.isoformat() if milestone.fecha_completado else None
    }
