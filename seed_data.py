#!/usr/bin/env python3
"""
Seed script to populate the database with sample projects.
Run this script after setting up the database.

Usage:
    python seed_data.py
"""

from datetime import datetime, timedelta
from sqlmodel import Session, select

from database import (
    engine, create_db_and_tables, create_milestones_for_project,
    Project, Milestone, Document, Activity,
    SectorEnum, EstadoEnum, TipoDocumentoEnum, MILESTONE_NAMES
)


def seed_database():
    create_db_and_tables()

    with Session(engine) as session:
        # Check if data already exists
        existing = session.exec(select(Project)).first()
        if existing:
            print("Database already has data. Skipping seed.")
            return

        # Project 1: Parque Solar Atacama
        project1 = Project(
            nombre="Parque Solar Atacama",
            sector=SectorEnum.ENERGIA,
            contraparte="Energía Renovable Chile S.A.",
            contacto_nombre="María González",
            contacto_email="mgonzalez@energiarenovable.cl",
            monto_deal=45000000.0,
            fee_pct=1.5,
            probabilidad=65,
            estado=EstadoEnum.ACTIVO,
            fecha_inicio=datetime.now() - timedelta(days=90),
            fecha_cierre_estimada=datetime.now() + timedelta(days=120),
            notas="Proyecto de energía solar fotovoltaica en el Desierto de Atacama. "
                  "Capacidad instalada de 150MW. Inversionistas interesados de Europa y Asia."
        )
        session.add(project1)
        session.commit()
        session.refresh(project1)

        # Create milestones for project 1
        for orden, nombre in enumerate(MILESTONE_NAMES):
            completado = orden < 4  # First 4 completed
            milestone = Milestone(
                project_id=project1.id,
                nombre=nombre,
                orden=orden,
                completado=completado,
                fecha_completado=datetime.now() - timedelta(days=30-orden*7) if completado else None
            )
            session.add(milestone)

        # Add documents for project 1
        session.add(Document(
            project_id=project1.id,
            nombre="Evaluación Técnica Solar",
            url_drive="https://drive.google.com/file/d/example1",
            tipo=TipoDocumentoEnum.EVALUACION
        ))
        session.add(Document(
            project_id=project1.id,
            nombre="Teaser Inversionistas",
            url_drive="https://drive.google.com/file/d/example2",
            tipo=TipoDocumentoEnum.PRESENTACION
        ))

        # Add activities for project 1
        session.add(Activity(project_id=project1.id, descripcion="Proyecto creado"))
        session.add(Activity(project_id=project1.id, descripcion="NDA firmado con inversionista japonés"))
        session.add(Activity(project_id=project1.id, descripcion="Reunión con banco de desarrollo"))
        session.commit()

        # Project 2: Terminal Portuario Sur
        project2 = Project(
            nombre="Terminal Portuario Sur",
            sector=SectorEnum.INFRAESTRUCTURA,
            contraparte="Puertos del Pacífico SpA",
            contacto_nombre="Carlos Mendoza",
            contacto_email="cmendoza@puertospacifico.com",
            monto_deal=120000000.0,
            fee_pct=0.75,
            probabilidad=40,
            estado=EstadoEnum.ACTIVO,
            fecha_inicio=datetime.now() - timedelta(days=45),
            fecha_cierre_estimada=datetime.now() + timedelta(days=200),
            notas="Expansión del terminal de contenedores. Proyecto de infraestructura crítica. "
                  "Requiere aprobación ambiental y permisos de la autoridad marítima."
        )
        session.add(project2)
        session.commit()
        session.refresh(project2)

        # Create milestones for project 2
        for orden, nombre in enumerate(MILESTONE_NAMES):
            completado = orden < 2  # First 2 completed
            milestone = Milestone(
                project_id=project2.id,
                nombre=nombre,
                orden=orden,
                completado=completado,
                fecha_completado=datetime.now() - timedelta(days=20-orden*10) if completado else None
            )
            session.add(milestone)

        # Add documents for project 2
        session.add(Document(
            project_id=project2.id,
            nombre="Estudio de Impacto Ambiental",
            url_drive="https://drive.google.com/file/d/example3",
            tipo=TipoDocumentoEnum.LEGAL
        ))

        # Add activities for project 2
        session.add(Activity(project_id=project2.id, descripcion="Proyecto creado"))
        session.add(Activity(project_id=project2.id, descripcion="NDA firmado"))
        session.commit()

        # Project 3: Edificio Corporativo Las Condes
        project3 = Project(
            nombre="Edificio Corporativo Las Condes",
            sector=SectorEnum.REAL_ESTATE,
            contraparte="Inmobiliaria Premium SpA",
            contacto_nombre="Andrea Silva",
            contacto_email="asilva@inmobpremium.cl",
            monto_deal=85000000.0,
            fee_pct=1.0,
            probabilidad=80,
            estado=EstadoEnum.PAUSA,
            fecha_inicio=datetime.now() - timedelta(days=180),
            fecha_cierre_estimada=datetime.now() + timedelta(days=60),
            notas="Torre de oficinas clase A+ en el sector financiero de Santiago. "
                  "En pausa por revisión de condiciones de financiamiento. "
                  "Pre-arrendamiento al 65%."
        )
        session.add(project3)
        session.commit()
        session.refresh(project3)

        # Create milestones for project 3
        for orden, nombre in enumerate(MILESTONE_NAMES):
            completado = orden < 7  # First 7 completed
            milestone = Milestone(
                project_id=project3.id,
                nombre=nombre,
                orden=orden,
                completado=completado,
                fecha_completado=datetime.now() - timedelta(days=120-orden*15) if completado else None
            )
            session.add(milestone)

        # Add documents for project 3
        session.add(Document(
            project_id=project3.id,
            nombre="Due Diligence Legal",
            url_drive="https://drive.google.com/file/d/example4",
            tipo=TipoDocumentoEnum.LEGAL
        ))
        session.add(Document(
            project_id=project3.id,
            nombre="Modelo Financiero",
            url_drive="https://drive.google.com/file/d/example5",
            tipo=TipoDocumentoEnum.EVALUACION
        ))
        session.add(Document(
            project_id=project3.id,
            nombre="Presentación Inversionistas",
            url_drive="https://drive.google.com/file/d/example6",
            tipo=TipoDocumentoEnum.PRESENTACION
        ))

        # Add activities for project 3
        session.add(Activity(project_id=project3.id, descripcion="Proyecto creado"))
        session.add(Activity(project_id=project3.id, descripcion="Due diligence completado"))
        session.add(Activity(project_id=project3.id, descripcion="LOI recibido de fondo de inversión"))
        session.add(Activity(project_id=project3.id, descripcion="Proyecto en pausa - revisión condiciones"))
        session.commit()

        print("Database seeded successfully with 3 sample projects!")
        print("- Parque Solar Atacama (Energía, Activo, 4/11 hitos)")
        print("- Terminal Portuario Sur (Infraestructura, Activo, 2/11 hitos)")
        print("- Edificio Corporativo Las Condes (Real Estate, Pausa, 7/11 hitos)")


if __name__ == "__main__":
    seed_database()
