from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from database import Contraparte, Activity, get_session

router = APIRouter(prefix="/api/contrapartes", tags=["contrapartes"])


@router.post("/add")
def add_contraparte(
    project_id: int = Form(...),
    nombre_empresa: str = Form(...),
    contacto_nombre: str = Form(""),
    contacto_email: str = Form(""),
    contacto_telefono: str = Form(""),
    notas: str = Form(""),
    session: Session = Depends(get_session),
):
    contraparte = Contraparte(
        project_id=project_id,
        nombre_empresa=nombre_empresa,
        contacto_nombre=contacto_nombre,
        contacto_email=contacto_email,
        contacto_telefono=contacto_telefono,
        notas=notas,
    )
    session.add(contraparte)
    session.commit()

    activity = Activity(
        project_id=project_id,
        descripcion=f"Contraparte agregada: {nombre_empresa}"
    )
    session.add(activity)
    session.commit()

    return RedirectResponse(url=f"/project/{project_id}", status_code=303)


@router.post("/{contraparte_id}/delete")
def delete_contraparte(
    contraparte_id: int,
    session: Session = Depends(get_session),
):
    contraparte = session.get(Contraparte, contraparte_id)
    if not contraparte:
        raise HTTPException(status_code=404, detail="Contraparte no encontrada")

    project_id = contraparte.project_id
    nombre = contraparte.nombre_empresa

    session.delete(contraparte)
    session.commit()

    activity = Activity(
        project_id=project_id,
        descripcion=f"Contraparte eliminada: {nombre}"
    )
    session.add(activity)
    session.commit()

    return RedirectResponse(url=f"/project/{project_id}", status_code=303)
