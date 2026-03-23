import os
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import Project, Milestone, Document, Activity, Contraparte, get_session

router = APIRouter(prefix="/api/ai_summary", tags=["ai_summary"])


@router.post("/{project_id}")
async def generate_ai_summary(
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
    ).all()

    activities = session.exec(
        select(Activity)
        .where(Activity.project_id == project_id)
        .order_by(Activity.created_at.desc())
    ).all()

    contrapartes = session.exec(
        select(Contraparte)
        .where(Contraparte.project_id == project_id)
    ).all()

    milestones_info = [
        {
            "nombre": m.nombre,
            "completado": m.completado,
            "fecha": m.fecha_completado.isoformat() if m.fecha_completado else None
        }
        for m in milestones
    ]

    documents_info = [
        {"nombre": d.nombre, "tipo": d.tipo.value}
        for d in documents
    ]

    activities_info = [
        {
            "descripcion": a.descripcion,
            "fecha": a.created_at.isoformat()
        }
        for a in activities[:20]
    ]

    contrapartes_info = [
        {
            "empresa": c.nombre_empresa,
            "contacto": c.contacto_nombre,
            "email": c.contacto_email
        }
        for c in contrapartes
    ]

    project_data = f"""
PROYECTO: {project.nombre}
Sector: {project.sector.value}
Monto del Deal: ${project.monto_deal:,.2f} USD
Fee: {project.fee_pct}%
Probabilidad actual: {project.probabilidad}%
Estado: {project.estado.value}
Fecha inicio: {project.fecha_inicio.strftime('%Y-%m-%d') if project.fecha_inicio else 'No definida'}
Fecha cierre estimada: {project.fecha_cierre_estimada.strftime('%Y-%m-%d') if project.fecha_cierre_estimada else 'No definida'}

CONTRAPARTES:
{json.dumps(contrapartes_info, indent=2, ensure_ascii=False) if contrapartes_info else 'Sin contrapartes definidas'}

NOTAS:
{project.notas or 'Sin notas'}

HITOS (10 totales):
{json.dumps(milestones_info, indent=2, ensure_ascii=False)}

DOCUMENTOS:
{json.dumps(documents_info, indent=2, ensure_ascii=False)}

ACTIVIDADES RECIENTES:
{json.dumps(activities_info, indent=2, ensure_ascii=False)}
"""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY no configurada"
        )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = """Eres un analista senior de banca de inversión con más de 15 años de experiencia en M&A y project finance.
Analiza este proyecto de intermediación financiera y proporciona un análisis ejecutivo.
Responde siempre en español.
Tu respuesta DEBE ser un JSON válido con la siguiente estructura exacta:
{
    "executive_summary": "Resumen ejecutivo de 2-3 oraciones",
    "estado_actual": "Descripción del estado actual del proyecto",
    "riesgos": ["Riesgo 1", "Riesgo 2", "Riesgo 3"],
    "proximos_pasos": ["Paso 1", "Paso 2", "Paso 3"],
    "probabilidad_sugerida": 75
}
Solo responde con el JSON, sin texto adicional."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Analiza el siguiente proyecto:\n\n{project_data}"
                }
            ]
        )

        response_text = message.content[0].text

        try:
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text.strip())
        except json.JSONDecodeError:
            result = {
                "executive_summary": response_text[:500],
                "estado_actual": "Ver resumen ejecutivo",
                "riesgos": ["Error al parsear respuesta estructurada"],
                "proximos_pasos": ["Revisar manualmente"],
                "probabilidad_sugerida": project.probabilidad
            }

        activity = Activity(
            project_id=project_id,
            descripcion=f"Resumen IA generado - Probabilidad sugerida: {result.get('probabilidad_sugerida', 'N/A')}%"
        )
        session.add(activity)
        session.commit()

        return result

    except anthropic.APIError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error de API Anthropic: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando resumen: {str(e)}"
        )
