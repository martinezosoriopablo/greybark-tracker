from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from database import Activity, get_session

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.post("/add")
def add_activity(
    project_id: int = Form(...),
    descripcion: str = Form(...),
    session: Session = Depends(get_session),
):
    activity = Activity(
        project_id=project_id,
        descripcion=descripcion,
    )
    session.add(activity)
    session.commit()

    return RedirectResponse(url=f"/project/{project_id}", status_code=303)
