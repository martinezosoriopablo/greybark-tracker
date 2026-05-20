#!/usr/bin/env python3
"""
Seed script to populate the database with sample projects.
Usage:
    python seed_data.py
"""

from datetime import datetime, timedelta
from sqlmodel import Session, select

from database import (
    engine, create_db_and_tables, create_milestones_for_project,
    Project, Milestone, Document, Contraparte, Encargado,
    SectorEnum, EstadoEnum, TipoDocumentoEnum, TipoFinanciamientoEnum,
    MILESTONE_NAMES,
)


def seed_database():
    create_db_and_tables()

    with Session(engine) as session:
        existing = session.exec(select(Project)).first()
        if existing:
            print("Database already has data. Skipping seed.")
            return

        for nombre in ["Pablo Martínez", "Equipo Comercial", "Legal Externo"]:
            session.add(Encargado(nombre=nombre))
        session.commit()

        project1 = Project(
            nombre="Parque Solar Atacama",
            sector=SectorEnum.ENERGIA,
            tipo_financiamiento=TipoFinanciamientoEnum.MIXTO,
            monto_deal=45000000.0,
            fee_pct=1.5,
            probabilidad=65,
            estado=EstadoEnum.ACTIVO,
            fecha_inicio=datetime.now() - timedelta(days=90),
            fecha_cierre_estimada=datetime.now() + timedelta(days=120),
            notas="Proyecto de energía solar fotovoltaica en el Desierto de Atacama. "
                  "Capacidad instalada de 150MW.",
        )
        session.add(project1)
        session.commit()
        session.refresh(project1)

        for orden, nombre in enumerate(MILESTONE_NAMES):
            completado = orden < 4
            session.add(Milestone(
                project_id=project1.id,
                nombre=nombre,
                orden=orden,
                completado=completado,
                fecha_completado=datetime.now() - timedelta(days=30 - orden * 7) if completado else None,
            ))

        session.add(Contraparte(
            project_id=project1.id,
            tipo="inversionista",
            nombre_empresa="Energía Renovable Chile S.A.",
            contacto_nombre="María González",
            contacto_email="mgonzalez@energiarenovable.cl",
        ))

        session.add(Document(
            project_id=project1.id,
            nombre="Evaluación Técnica Solar",
            url_drive="https://drive.google.com/file/d/example1",
            tipo=TipoDocumentoEnum.EVALUACION,
        ))
        session.commit()

        project2 = Project(
            nombre="Terminal Portuario Sur",
            sector=SectorEnum.INFRAESTRUCTURA,
            tipo_financiamiento=TipoFinanciamientoEnum.DEUDA,
            monto_deal=120000000.0,
            fee_pct=0.75,
            probabilidad=None,
            estado=EstadoEnum.ACTIVO,
            fecha_inicio=datetime.now() - timedelta(days=45),
            fecha_cierre_estimada=None,
            notas="Expansión del terminal de contenedores.",
        )
        session.add(project2)
        session.commit()
        session.refresh(project2)

        for orden, nombre in enumerate(MILESTONE_NAMES):
            completado = orden < 2
            session.add(Milestone(
                project_id=project2.id,
                nombre=nombre,
                orden=orden,
                completado=completado,
                fecha_completado=datetime.now() - timedelta(days=20 - orden * 10) if completado else None,
            ))

        session.add(Contraparte(
            project_id=project2.id,
            tipo="broker",
            nombre_empresa="Puertos del Pacífico SpA",
            contacto_nombre="Carlos Mendoza",
        ))
        session.commit()

        print("Database seeded successfully.")


if __name__ == "__main__":
    seed_database()
