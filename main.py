from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import create_db_and_tables
from routers import projects, documents, activities, ai_summary, milestones

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


@app.get("/health")
def health_check():
    return {"status": "healthy"}
