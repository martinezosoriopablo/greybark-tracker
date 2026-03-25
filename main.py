from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import create_db_and_tables
from routers import projects, documents, activities, ai_summary, milestones, contrapartes, portfolios

app = FastAPI(
    title="Greybark Deal Tracker",
    description="Gestión de proyectos de intermediación financiera",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


app.include_router(projects.router)
app.include_router(portfolios.router)
app.include_router(milestones.router)
app.include_router(documents.router)
app.include_router(activities.router)
app.include_router(ai_summary.router)
app.include_router(contrapartes.router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/debug")
def debug_check():
    """Debug endpoint to check database tables"""
    from sqlmodel import Session, select, text
    from database import engine, Project, Contraparte

    try:
        with Session(engine) as session:
            # Check tables exist
            projects = session.exec(select(Project)).all()
            contrapartes = session.exec(select(Contraparte)).all()

            return {
                "status": "ok",
                "projects_count": len(projects),
                "contrapartes_count": len(contrapartes),
                "projects": [p.nombre for p in projects],
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/debug-dashboard")
def debug_dashboard():
    """Debug endpoint to test dashboard"""
    from sqlmodel import Session, select
    from database import engine, Project, Contraparte, Portfolio

    try:
        with Session(engine) as session:
            projects = session.exec(select(Project)).all()

            # Test loading relationships
            for p in projects:
                _ = p.milestones
                _ = p.contrapartes
                _ = p.portfolio

            contrapartes = session.exec(select(Contraparte)).all()
            portfolios = session.exec(select(Portfolio)).all()

            return {
                "status": "ok",
                "projects": len(projects),
                "contrapartes": len(contrapartes),
                "portfolios": len(portfolios),
            }
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@app.get("/debug-create")
def debug_create():
    """Debug endpoint to test project creation"""
    from sqlmodel import Session
    from database import engine, Project, Activity, SectorEnum, EstadoEnum, create_milestones_for_project

    try:
        with Session(engine) as session:
            project = Project(
                nombre="TEST DEBUG",
                sector=SectorEnum.OTRO,
                monto_deal=1000.0,
                fee_pct=2.0,
                probabilidad=50,
                estado=EstadoEnum.ACTIVO,
                notas="Test project",
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

            return {"status": "ok", "project_id": project.id, "nombre": project.nombre}
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@app.get("/migrate-milestones")
def migrate_milestones():
    """One-time migration to remove 'Proyecto' milestone from existing projects"""
    from sqlmodel import Session, select
    from database import engine, Milestone, Project

    results = []
    with Session(engine) as session:
        projects = session.exec(select(Project)).all()

        for project in projects:
            milestones = session.exec(
                select(Milestone)
                .where(Milestone.project_id == project.id)
                .order_by(Milestone.orden)
            ).all()

            proyecto_milestone = None
            for m in milestones:
                if m.nombre == "Proyecto":
                    proyecto_milestone = m
                    break

            if proyecto_milestone:
                session.delete(proyecto_milestone)
                session.commit()

                remaining = session.exec(
                    select(Milestone)
                    .where(Milestone.project_id == project.id)
                    .order_by(Milestone.orden)
                ).all()

                for idx, m in enumerate(remaining):
                    if m.orden != idx:
                        m.orden = idx
                        session.add(m)
                session.commit()

                results.append(f"{project.nombre}: migrated to 10 milestones")
            else:
                results.append(f"{project.nombre}: already migrated")

    return {"status": "complete", "results": results}
