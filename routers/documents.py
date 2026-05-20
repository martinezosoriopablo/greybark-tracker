from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from database import Document, get_session, TipoDocumentoEnum

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/add")
def add_document(
    project_id: int = Form(...),
    nombre: str = Form(...),
    url_drive: str = Form(""),
    tipo: str = Form("otro"),
    session: Session = Depends(get_session),
):
    document = Document(
        project_id=project_id,
        nombre=nombre,
        url_drive=url_drive,
        tipo=TipoDocumentoEnum(tipo),
    )
    session.add(document)
    session.commit()

    return RedirectResponse(url=f"/project/{project_id}", status_code=303)


@router.post("/{document_id}/delete")
def delete_document(
    document_id: int,
    session: Session = Depends(get_session),
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    project_id = document.project_id

    session.delete(document)
    session.commit()

    return RedirectResponse(url=f"/project/{project_id}", status_code=303)
