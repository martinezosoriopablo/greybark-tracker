#!/usr/bin/env python3
"""
Migration script to remove "Proyecto" milestone from existing projects
and reorder remaining milestones.

Run this script once after deploying the update.

Usage:
    python migrate_milestones.py
"""

from sqlmodel import Session, select
from database import engine, Milestone, Project


def migrate_milestones():
    with Session(engine) as session:
        # Get all projects
        projects = session.exec(select(Project)).all()
        print(f"Found {len(projects)} projects to migrate")

        for project in projects:
            # Get milestones for this project
            milestones = session.exec(
                select(Milestone)
                .where(Milestone.project_id == project.id)
                .order_by(Milestone.orden)
            ).all()

            print(f"\nProject: {project.nombre} - {len(milestones)} milestones")

            # Find and delete "Proyecto" milestone
            proyecto_milestone = None
            for m in milestones:
                if m.nombre == "Proyecto":
                    proyecto_milestone = m
                    break

            if proyecto_milestone:
                print(f"  Deleting milestone: {proyecto_milestone.nombre}")
                session.delete(proyecto_milestone)
                session.commit()

                # Reorder remaining milestones
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
                print(f"  Reordered {len(remaining)} milestones")
            else:
                print(f"  No 'Proyecto' milestone found (already migrated)")

        print("\nMigration complete!")


if __name__ == "__main__":
    migrate_milestones()
