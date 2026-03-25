from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database import Portfolio, Project, get_session

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/portfolios")
def portfolios_list(
    request: Request,
    session: Session = Depends(get_session),
):
    portfolios = session.exec(
        select(Portfolio).order_by(Portfolio.updated_at.desc())
    ).all()

    # Load projects for each portfolio
    for portfolio in portfolios:
        _ = portfolio.projects

    return templates.TemplateResponse(
        "portfolios.html",
        {
            "request": request,
            "portfolios": portfolios,
        }
    )


@router.get("/portfolio/new")
def portfolio_form_new(request: Request):
    return templates.TemplateResponse(
        "portfolio_form.html",
        {
            "request": request,
            "portfolio": None,
        }
    )


@router.post("/portfolio/new")
def portfolio_create(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    session: Session = Depends(get_session),
):
    portfolio = Portfolio(
        nombre=nombre,
        descripcion=descripcion,
    )
    session.add(portfolio)
    session.commit()
    session.refresh(portfolio)

    return RedirectResponse(url=f"/portfolio/{portfolio.id}", status_code=303)


@router.get("/portfolio/{portfolio_id}")
def portfolio_detail(
    request: Request,
    portfolio_id: int,
    session: Session = Depends(get_session),
):
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portafolio no encontrado")

    projects = session.exec(
        select(Project)
        .where(Project.portfolio_id == portfolio_id)
        .order_by(Project.updated_at.desc())
    ).all()

    # Load relationships for each project
    for project in projects:
        _ = project.milestones
        _ = project.contrapartes

    # Get projects without portfolio for adding
    available_projects = session.exec(
        select(Project).where(Project.portfolio_id == None)
    ).all()

    return templates.TemplateResponse(
        "portfolio_detail.html",
        {
            "request": request,
            "portfolio": portfolio,
            "projects": projects,
            "available_projects": available_projects,
        }
    )


@router.get("/portfolio/{portfolio_id}/edit")
def portfolio_form_edit(
    request: Request,
    portfolio_id: int,
    session: Session = Depends(get_session),
):
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portafolio no encontrado")

    return templates.TemplateResponse(
        "portfolio_form.html",
        {
            "request": request,
            "portfolio": portfolio,
        }
    )


@router.post("/portfolio/{portfolio_id}/edit")
def portfolio_update(
    request: Request,
    portfolio_id: int,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    session: Session = Depends(get_session),
):
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portafolio no encontrado")

    portfolio.nombre = nombre
    portfolio.descripcion = descripcion
    portfolio.updated_at = datetime.utcnow()

    session.add(portfolio)
    session.commit()

    return RedirectResponse(url=f"/portfolio/{portfolio.id}", status_code=303)


@router.post("/portfolio/{portfolio_id}/delete")
def portfolio_delete(
    portfolio_id: int,
    session: Session = Depends(get_session),
):
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portafolio no encontrado")

    # Remove portfolio_id from projects (don't delete projects)
    projects = session.exec(
        select(Project).where(Project.portfolio_id == portfolio_id)
    ).all()
    for project in projects:
        project.portfolio_id = None
        session.add(project)

    session.delete(portfolio)
    session.commit()

    return RedirectResponse(url="/portfolios", status_code=303)


@router.post("/portfolio/{portfolio_id}/add-project")
def portfolio_add_project(
    portfolio_id: int,
    project_id: int = Form(...),
    session: Session = Depends(get_session),
):
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portafolio no encontrado")

    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    project.portfolio_id = portfolio_id
    session.add(project)
    session.commit()

    return RedirectResponse(url=f"/portfolio/{portfolio_id}", status_code=303)


@router.post("/portfolio/{portfolio_id}/remove-project/{project_id}")
def portfolio_remove_project(
    portfolio_id: int,
    project_id: int,
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    project.portfolio_id = None
    session.add(project)
    session.commit()

    return RedirectResponse(url=f"/portfolio/{portfolio_id}", status_code=303)
