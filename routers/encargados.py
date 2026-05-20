from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database import Encargado, Task, get_session

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/encargados")
def encargados_list(
    request: Request,
    session: Session = Depends(get_session),
):
    encargados = session.exec(
        select(Encargado).order_by(Encargado.activo.desc(), Encargado.nombre)
    ).all()
    return templates.TemplateResponse(
        "encargados.html",
        {"request": request, "encargados": encargados},
    )


@router.post("/encargados/add")
def encargado_add(
    nombre: str = Form(...),
    email: str = Form(""),
    session: Session = Depends(get_session),
):
    nombre = nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")

    exists = session.exec(select(Encargado).where(Encargado.nombre == nombre)).first()
    if not exists:
        session.add(Encargado(nombre=nombre, email=email.strip()))
        session.commit()

    return RedirectResponse(url="/encargados", status_code=303)


@router.post("/encargados/{encargado_id}/toggle")
def encargado_toggle(
    encargado_id: int,
    session: Session = Depends(get_session),
):
    encargado = session.get(Encargado, encargado_id)
    if not encargado:
        raise HTTPException(status_code=404, detail="Encargado no encontrado")
    encargado.activo = not encargado.activo
    session.add(encargado)
    session.commit()
    return RedirectResponse(url="/encargados", status_code=303)


@router.post("/encargados/{encargado_id}/delete")
def encargado_delete(
    encargado_id: int,
    session: Session = Depends(get_session),
):
    encargado = session.get(Encargado, encargado_id)
    if not encargado:
        raise HTTPException(status_code=404, detail="Encargado no encontrado")

    en_uso = session.exec(
        select(Task).where(Task.encargado == encargado.nombre).limit(1)
    ).first()
    if en_uso:
        encargado.activo = False
        session.add(encargado)
        session.commit()
    else:
        session.delete(encargado)
        session.commit()

    return RedirectResponse(url="/encargados", status_code=303)
