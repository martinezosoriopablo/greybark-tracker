from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import create_db_and_tables
from routers import projects, documents, milestones, contrapartes, portfolios, tasks, encargados

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
app.include_router(contrapartes.router)
app.include_router(tasks.router)
app.include_router(encargados.router)


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


@app.get("/migrate-v2")
def migrate_v2():
    """Migración idempotente para el schema v2.

    Postgres (Supabase):
      - Agrega project.tipo_financiamiento (nullable VARCHAR).
      - Hace project.probabilidad nullable.
      - Hace nullable las columnas legacy (contraparte, contacto_nombre, contacto_email).
      - Crea tabla encargado si no existe.

    SQLite: agrega project.tipo_financiamiento y crea tabla encargado.
    Para hacer nullable las columnas existentes en SQLite hay que recrear la tabla
    (ver script en /Users/pablomartinez/greybark-tracker para la copia local).
    """
    from sqlalchemy import text
    from database import engine

    results = []
    dialect = engine.dialect.name

    def run(sql: str, label: str):
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
            results.append(f"OK: {label}")
        except Exception as e:
            results.append(f"SKIP {label}: {type(e).__name__}: {str(e).splitlines()[0]}")

    if dialect == "postgresql":
        run(
            "ALTER TABLE project ADD COLUMN IF NOT EXISTS tipo_financiamiento VARCHAR",
            "project.tipo_financiamiento agregada",
        )
        run(
            "ALTER TABLE project ALTER COLUMN probabilidad DROP NOT NULL",
            "project.probabilidad nullable",
        )
        for col in ("contraparte", "contacto_nombre", "contacto_email"):
            run(
                f"ALTER TABLE project ALTER COLUMN {col} DROP NOT NULL",
                f"project.{col} nullable (legacy)",
            )
        run(
            "CREATE TABLE IF NOT EXISTS encargado ("
            "id SERIAL PRIMARY KEY, "
            "nombre VARCHAR NOT NULL, "
            "email VARCHAR NOT NULL DEFAULT '', "
            "activo BOOLEAN NOT NULL DEFAULT TRUE, "
            "created_at TIMESTAMP NOT NULL DEFAULT NOW())",
            "tabla encargado",
        )
    else:
        run(
            "ALTER TABLE project ADD COLUMN tipo_financiamiento VARCHAR",
            "project.tipo_financiamiento agregada",
        )
        run(
            "CREATE TABLE IF NOT EXISTS encargado ("
            "id INTEGER PRIMARY KEY, "
            "nombre VARCHAR NOT NULL, "
            "email VARCHAR NOT NULL DEFAULT '', "
            "activo BOOLEAN NOT NULL DEFAULT 1, "
            "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)",
            "tabla encargado",
        )
        results.append("NOTA sqlite: para columnas legacy/probabilidad nullable, recrear tabla project manualmente.")

    return {"status": "complete", "dialect": dialect, "results": results}


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
