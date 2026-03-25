from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database import (
    Project, Milestone, Document, Activity, Contraparte, Portfolio,
    get_session, create_milestones_for_project,
    SectorEnum, EstadoEnum, MILESTONE_NAMES
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_current_stage(milestones):
    """Get the name of the last completed milestone (current stage)"""
    completed = [m for m in sorted(milestones, key=lambda x: x.orden) if m.completado]
    if completed:
        return completed[-1].nombre
    return None


@router.get("/")
def dashboard(
    request: Request,
    sector: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    contraparte: Optional[str] = Query(None),
    etapa: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    debug: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    try:
        statement = select(Project).order_by(Project.updated_at.desc())
        projects = session.exec(statement).all()

        # Load relationships
        for project in projects:
            _ = project.milestones
            _ = project.documents
            _ = project.activities
            _ = project.contrapartes

        # Get all unique contrapartes for filter dropdown
        all_contrapartes = session.exec(select(Contraparte)).all()
        unique_contrapartes = sorted(set(c.nombre_empresa for c in all_contrapartes))

        # Apply filters
        if sector and sector != "todos":
            projects = [p for p in projects if p.sector.value == sector]

        if estado and estado != "todos":
            projects = [p for p in projects if p.estado.value == estado]

        if contraparte and contraparte != "todos":
            projects = [
                p for p in projects
                if any(c.nombre_empresa == contraparte for c in p.contrapartes)
            ]

        if etapa and etapa != "todos":
            if etapa == "sin_iniciar":
                projects = [p for p in projects if get_current_stage(p.milestones) is None]
            else:
                projects = [p for p in projects if get_current_stage(p.milestones) == etapa]

        if search:
            search_lower = search.lower()
            projects = [
                p for p in projects
                if search_lower in p.nombre.lower()
                or any(search_lower in c.nombre_empresa.lower() for c in p.contrapartes)
            ]

        # Calculate KPIs (from all projects, not filtered)
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
                "contrapartes_list": unique_contrapartes,
                "etapas_list": MILESTONE_NAMES,
                "filter_sector": sector or "todos",
                "filter_estado": estado or "todos",
                "filter_contraparte": contraparte or "todos",
                "filter_etapa": etapa or "todos",
                "filter_search": search or "",
            }
        )
    except Exception as e:
        if debug:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}
        raise


@router.get("/project/new")
def project_form_new(
    request: Request,
    session: Session = Depends(get_session),
):
    portfolios = session.exec(select(Portfolio)).all()
    return templates.TemplateResponse(
        "project_form.html",
        {
            "request": request,
            "project": None,
            "sectores": SectorEnum,
            "estados": EstadoEnum,
            "portfolios": portfolios,
        }
    )


@router.post("/project/new")
def project_create(
    request: Request,
    nombre: str = Form(...),
    sector: str = Form(...),
    portfolio_id: str = Form(""),
    monto_deal: str = Form("0"),
    fee_pct: str = Form("0"),
    probabilidad: str = Form("50"),
    estado: str = Form("activo"),
    fecha_inicio: Optional[str] = Form(None),
    fecha_cierre_estimada: Optional[str] = Form(None),
    notas: str = Form(""),
    session: Session = Depends(get_session),
):
    # Parse numeric fields (handle empty strings)
    monto_deal_float = float(monto_deal) if monto_deal else 0.0
    fee_pct_float = float(fee_pct) if fee_pct else 0.0
    probabilidad_int = int(probabilidad) if probabilidad else 50
    portfolio_id_int = int(portfolio_id) if portfolio_id else None

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
        portfolio_id=portfolio_id_int,
        monto_deal=monto_deal_float,
        fee_pct=fee_pct_float,
        probabilidad=probabilidad_int,
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

    portfolios = session.exec(select(Portfolio)).all()

    return templates.TemplateResponse(
        "project_form.html",
        {
            "request": request,
            "project": project,
            "sectores": SectorEnum,
            "estados": EstadoEnum,
            "portfolios": portfolios,
        }
    )


@router.post("/project/{project_id}/edit")
def project_update(
    request: Request,
    project_id: int,
    nombre: str = Form(...),
    sector: str = Form(...),
    portfolio_id: str = Form(""),
    monto_deal: str = Form("0"),
    fee_pct: str = Form("0"),
    probabilidad: str = Form("50"),
    estado: str = Form("activo"),
    fecha_inicio: Optional[str] = Form(None),
    fecha_cierre_estimada: Optional[str] = Form(None),
    notas: str = Form(""),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Parse numeric fields (handle empty strings)
    monto_deal_float = float(monto_deal) if monto_deal else 0.0
    fee_pct_float = float(fee_pct) if fee_pct else 0.0
    probabilidad_int = int(probabilidad) if probabilidad else 50
    portfolio_id_int = int(portfolio_id) if portfolio_id else None

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
    project.portfolio_id = portfolio_id_int
    project.monto_deal = monto_deal_float
    project.fee_pct = fee_pct_float
    project.probabilidad = probabilidad_int
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
