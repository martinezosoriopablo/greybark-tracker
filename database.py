import os
from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlmodel import Field, SQLModel, Relationship, create_engine, Session
from dotenv import load_dotenv

load_dotenv()


class SectorEnum(str, Enum):
    ENERGIA = "energía"
    INFRAESTRUCTURA = "infraestructura"
    REAL_ESTATE = "real_estate"
    OTRO = "otro"


class EstadoEnum(str, Enum):
    ACTIVO = "activo"
    PAUSA = "pausa"
    CERRADO = "cerrado"


class TipoDocumentoEnum(str, Enum):
    EVALUACION = "evaluación"
    PRESENTACION = "presentación"
    LEGAL = "legal"
    OTRO = "otro"


MILESTONE_NAMES = [
    "NDA",
    "Teaser",
    "Acuerdo Comercial",
    "Reunión Inversionista",
    "Data Room",
    "Due Diligence",
    "LOI",
    "Negociación",
    "Term Sheet",
    "Closing",
]


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)
    sector: SectorEnum = Field(default=SectorEnum.OTRO)
    monto_deal: float = Field(default=0.0)
    fee_pct: float = Field(default=0.0)
    probabilidad: int = Field(default=50, ge=0, le=100)
    estado: EstadoEnum = Field(default=EstadoEnum.ACTIVO)
    fecha_inicio: Optional[datetime] = Field(default=None)
    fecha_cierre_estimada: Optional[datetime] = Field(default=None)
    notas: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    milestones: List["Milestone"] = Relationship(back_populates="project")
    documents: List["Document"] = Relationship(back_populates="project")
    activities: List["Activity"] = Relationship(back_populates="project")
    contrapartes: List["Contraparte"] = Relationship(back_populates="project")

    @property
    def comision_proyectada(self) -> float:
        return self.monto_deal * (self.fee_pct / 100) * (self.probabilidad / 100)

    @property
    def hitos_completados(self) -> int:
        return sum(1 for m in self.milestones if m.completado)

    @property
    def dias_restantes(self) -> Optional[int]:
        if self.fecha_cierre_estimada:
            delta = self.fecha_cierre_estimada - datetime.utcnow()
            return max(0, delta.days)
        return None


class Milestone(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    nombre: str
    orden: int = Field(default=0)
    completado: bool = Field(default=False)
    fecha_completado: Optional[datetime] = Field(default=None)

    project: Optional[Project] = Relationship(back_populates="milestones")


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    nombre: str
    url_drive: str = Field(default="")
    tipo: TipoDocumentoEnum = Field(default=TipoDocumentoEnum.OTRO)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    project: Optional[Project] = Relationship(back_populates="documents")


class Activity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    descripcion: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Optional[Project] = Relationship(back_populates="activities")


class Contraparte(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    nombre_empresa: str
    contacto_nombre: str = Field(default="")
    contacto_email: str = Field(default="")
    contacto_telefono: str = Field(default="")
    notas: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Optional[Project] = Relationship(back_populates="contrapartes")


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./greybark.db")

# Convert to psycopg3 driver for Supabase compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "supabase" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Add SSL for Supabase
if "supabase" in DATABASE_URL:
    if "?" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"
    elif "sslmode" not in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"

    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
    )
else:
    engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def create_milestones_for_project(session: Session, project_id: int):
    for orden, nombre in enumerate(MILESTONE_NAMES):
        milestone = Milestone(project_id=project_id, nombre=nombre, orden=orden)
        session.add(milestone)
    session.commit()
