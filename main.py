from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import create_db_and_tables
from routers import projects, documents, activities, ai_summary, milestones, contrapartes

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
app.include_router(milestones.router)
app.include_router(documents.router)
app.include_router(activities.router)
app.include_router(ai_summary.router)
app.include_router(contrapartes.router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


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
