from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database import Task, Project, Activity, TaskStatusEnum, get_session

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _parse_fecha(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


@router.post("/api/tasks/add")
def add_task(
    project_id: int = Form(...),
    nombre: str = Form(...),
    encargado: str = Form(""),
    fecha_limite: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    task = Task(
        project_id=project_id,
        nombre=nombre,
        encargado=encargado,
        fecha_limite=_parse_fecha(fecha_limite),
    )
    session.add(task)
    session.commit()

    activity = Activity(
        project_id=project_id,
        descripcion=f"Tarea agregada: {nombre}",
    )
    session.add(activity)
    session.commit()

    return RedirectResponse(url=f"/project/{project_id}", status_code=303)


@router.post("/api/tasks/{task_id}/update")
def update_task(
    task_id: int,
    request: Request,
    status: Optional[str] = Form(None),
    nombre: Optional[str] = Form(None),
    encargado: Optional[str] = Form(None),
    fecha_limite: Optional[str] = Form(None),
    redirect_to: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    if nombre is not None and nombre != "":
        task.nombre = nombre
    if encargado is not None:
        task.encargado = encargado
    if fecha_limite is not None:
        task.fecha_limite = _parse_fecha(fecha_limite)

    if status is not None:
        new_status = TaskStatusEnum(status)
        was_completed = task.status == TaskStatusEnum.COMPLETADA
        task.status = new_status
        if new_status == TaskStatusEnum.COMPLETADA and not was_completed:
            task.completed_at = datetime.utcnow()
            session.add(Activity(
                project_id=task.project_id,
                descripcion=f"Tarea completada: {task.nombre}",
            ))
        elif new_status != TaskStatusEnum.COMPLETADA and was_completed:
            task.completed_at = None

    session.add(task)
    session.commit()

    target = redirect_to or f"/project/{task.project_id}"
    return RedirectResponse(url=target, status_code=303)


@router.post("/api/tasks/{task_id}/delete")
def delete_task(
    task_id: int,
    redirect_to: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    project_id = task.project_id
    nombre = task.nombre
    session.delete(task)
    session.commit()

    session.add(Activity(
        project_id=project_id,
        descripcion=f"Tarea eliminada: {nombre}",
    ))
    session.commit()

    target = redirect_to or f"/project/{project_id}"
    return RedirectResponse(url=target, status_code=303)


@router.get("/tasks")
def tasks_overview(
    request: Request,
    encargado: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    incluir_completadas: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    show_completed = incluir_completadas == "1"

    statement = select(Task).order_by(Task.fecha_limite.is_(None), Task.fecha_limite, Task.created_at)
    tasks = session.exec(statement).all()

    for t in tasks:
        _ = t.project

    if not show_completed:
        tasks = [t for t in tasks if t.status != TaskStatusEnum.COMPLETADA]

    encargados_set = sorted({t.encargado for t in tasks if t.encargado})

    projects = session.exec(select(Project).order_by(Project.nombre)).all()

    if encargado and encargado != "todos":
        tasks = [t for t in tasks if t.encargado == encargado]

    project_id_int: Optional[int] = None
    if project_id and project_id != "todos":
        try:
            project_id_int = int(project_id)
            tasks = [t for t in tasks if t.project_id == project_id_int]
        except ValueError:
            project_id_int = None

    today = datetime.utcnow().date()
    pendientes_count = sum(1 for t in tasks if t.status == TaskStatusEnum.PENDIENTE)
    en_curso_count = sum(1 for t in tasks if t.status == TaskStatusEnum.EN_CURSO)
    vencidas_count = sum(
        1 for t in tasks
        if t.status != TaskStatusEnum.COMPLETADA
        and t.fecha_limite is not None
        and t.fecha_limite.date() < today
    )

    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "tasks": tasks,
            "projects": projects,
            "encargados": encargados_set,
            "statuses": TaskStatusEnum,
            "filter_encargado": encargado or "todos",
            "filter_project": project_id or "todos",
            "show_completed": show_completed,
            "today": today,
            "pendientes_count": pendientes_count,
            "en_curso_count": en_curso_count,
            "vencidas_count": vencidas_count,
        },
    )
