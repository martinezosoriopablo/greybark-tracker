from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database import (
    Project, Milestone, Document, Activity, Contraparte,
    get_session, create_milestones_for_project,
    SectorEnum, EstadoEnum
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
def dashboard(
    request: Request,
    sector: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    statement = select(Project).order_by(Project.updated_at.desc())
    projects = session.exec(statement).all()

    # Load relationships
    for project in projects:
        _ = project.milestones
        _ = project.documents
        _ = project.activities
        _ = project.contrapartes

    # Apply filters
    if sector and sector != "todos":
        projects = [p for p in projects if p.sector.value == sector]

    if estado and estado != "todos":
        projects = [p for p in projects if p.estado.value == estado]

    if search:
        search_lower = search.lower()
        projects = [
            p for p in projects
            if search_lower in p.nombre.lower()
            or any(search_lower in c.nombre_empresa.lower() for c in p.contrapartes)
        ]

    # Calculate KPIs (from filtered projects for activos, but all for totals)
    all_projects = session.exec(select(Project)).all()
    for p in all_projects:
        _ = p.milestones

    activos = [p for p in all_projects if p.estado == EstadoEnum.ACTIVO]
    total_activos = len(activos)

    pipeline_ponderado = sum(p.comision_proyectada for p in activos)

    closing_termsheet = sum(
        1 for p in all_projects
        if p.estado == EstadoEnum.ACTIVO and any(
            m.completado and m.nombre in ["Term Sheet", "Closing"]
            for m in p.milestones
        )
    )

    cerrados = [p for p in all_projects if p.estado == EstadoEnum.CERRADO]
    comision_cerrados = sum(
        p.monto_deal * (p.fee_pct / 100) for p in cerrados
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "projects": projects,
            "total_activos": total_activos,
            "pipeline_ponderado": pipeline_ponderado,
            "closing_termsheet": closing_termsheet,
            "comision_cerrados": comision_cerrados,
            "sectores": SectorEnum,
            "estados": EstadoEnum,
            "filter_sector": sector or "todos",
            "filter_estado": estado or "todos",
            "filter_search": search or "",
        }
    )


@router.get("/project/new")
def project_form_new(request: Request):
    return templates.TemplateResponse(
        "project_form.html",
        {
            "request": request,
            "project": None,
            "sectores": SectorEnum,
            "estados": EstadoEnum,
        }
    )


@router.post("/project/new")
def project_create(
    request: Request,
    nombre: str = Form(...),
    sector: str = Form(...),
    monto_deal: float = Form(0.0),
    fee_pct: float = Form(0.0),
    probabilidad: int = Form(50),
    estado: str = Form("activo"),
    fecha_inicio: Optional[str] = Form(None),
    fecha_cierre_estimada: Optional[str] = Form(None),
    notas: str = Form(""),
    session: Session = Depends(get_session),
):
    fecha_inicio_dt = None
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        except ValueError:
            pass

    fecha_cierre_dt = None
    if fecha_cierre_estimada:
        try:
            fecha_cierre_dt = datetime.strptime(fecha_cierre_estimada, "%Y-%m-%d")
        except ValueError:
            pass

    project = Project(
        nombre=nombre,
        sector=SectorEnum(sector),
        monto_deal=monto_deal,
        fee_pct=fee_pct,
        probabilidad=probabilidad,
        estado=EstadoEnum(estado),
        fecha_inicio=fecha_inicio_dt,
        fecha_cierre_estimada=fecha_cierre_dt,
        notas=notas,
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    create_milestones_for_project(session, project.id)

    activity = Activity(
        project_id=project.id,
        descripcion="Proyecto creado"
    )
    session.add(activity)
    session.commit()

    return RedirectResponse(url=f"/project/{project.id}", status_code=303)


@router.get("/project/{project_id}")
def project_detail(
    request: Request,
    project_id: int,
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    milestones = session.exec(
        select(Milestone)
        .where(Milestone.project_id == project_id)
        .order_by(Milestone.orden)
    ).all()

    documents = session.exec(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.uploaded_at.desc())
    ).all()

    activities = session.exec(
        select(Activity)
        .where(Activity.project_id == project_id)
        .order_by(Activity.created_at.desc())
    ).all()

    contrapartes = session.exec(
        select(Contraparte)
        .where(Contraparte.project_id == project_id)
        .order_by(Contraparte.created_at.desc())
    ).all()

    from database import TipoDocumentoEnum

    return templates.TemplateResponse(
        "project_detail.html",
        {
            "request": request,
            "project": project,
            "milestones": milestones,
            "documents": documents,
            "activities": activities,
            "contrapartes": contrapartes,
            "tipos_documento": TipoDocumentoEnum,
        }
    )


@router.get("/project/{project_id}/edit")
def project_form_edit(
    request: Request,
    project_id: int,
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    return templates.TemplateResponse(
        "project_form.html",
        {
            "request": request,
            "project": project,
            "sectores": SectorEnum,
            "estados": EstadoEnum,
        }
    )


@router.post("/project/{project_id}/edit")
def project_update(
    request: Request,
    project_id: int,
    nombre: str = Form(...),
    sector: str = Form(...),
    monto_deal: float = Form(0.0),
    fee_pct: float = Form(0.0),
    probabilidad: int = Form(50),
    estado: str = Form("activo"),
    fecha_inicio: Optional[str] = Form(None),
    fecha_cierre_estimada: Optional[str] = Form(None),
    notas: str = Form(""),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    fecha_inicio_dt = None
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        except ValueError:
            pass

    fecha_cierre_dt = None
    if fecha_cierre_estimada:
        try:
            fecha_cierre_dt = datetime.strptime(fecha_cierre_estimada, "%Y-%m-%d")
        except ValueError:
            pass

    project.nombre = nombre
    project.sector = SectorEnum(sector)
    project.monto_deal = monto_deal
    project.fee_pct = fee_pct
    project.probabilidad = probabilidad
    project.estado = EstadoEnum(estado)
    project.fecha_inicio = fecha_inicio_dt
    project.fecha_cierre_estimada = fecha_cierre_dt
    project.notas = notas
    project.updated_at = datetime.utcnow()

    session.add(project)
    session.commit()

    activity = Activity(
        project_id=project.id,
        descripcion="Proyecto actualizado"
    )
    session.add(activity)
    session.commit()

    return RedirectResponse(url=f"/project/{project.id}", status_code=303)


@router.post("/project/{project_id}/delete")
def project_delete(
    project_id: int,
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Delete milestones
    milestones = session.exec(
        select(Milestone).where(Milestone.project_id == project_id)
    ).all()
    for m in milestones:
        session.delete(m)

    # Delete documents
    documents = session.exec(
        select(Document).where(Document.project_id == project_id)
    ).all()
    for d in documents:
        session.delete(d)

    # Delete activities
    activities = session.exec(
        select(Activity).where(Activity.project_id == project_id)
    ).all()
    for a in activities:
        session.delete(a)

    # Delete contrapartes
    contrapartes = session.exec(
        select(Contraparte).where(Contraparte.project_id == project_id)
    ).all()
    for c in contrapartes:
        session.delete(c)

    session.delete(project)
    session.commit()

    return RedirectResponse(url="/", status_code=303)
