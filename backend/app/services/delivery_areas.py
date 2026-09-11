from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.delivery_area import DeliveryArea
from app.models.user import User
from app.schemas.delivery_area import DeliveryAreaWrite
from app.services.audit import write_audit_log
from app.services.slugs import slugify


def seed_delivery_areas_if_empty(db: Session) -> None:
    existing_area = db.scalar(select(DeliveryArea.id).limit(1))
    if existing_area is not None:
        return

    db.add_all(
        [
            DeliveryArea(name="Merkez", slug="merkez", display_order=10),
            DeliveryArea(name="Sakarya", slug="sakarya", display_order=20),
            DeliveryArea(name="Karakol", slug="karakol", display_order=30),
            DeliveryArea(name="Maras", slug="maras", display_order=40),
        ]
    )
    db.commit()


def list_active_delivery_areas(db: Session) -> list[DeliveryArea]:
    return list(
        db.scalars(
            select(DeliveryArea)
            .where(DeliveryArea.is_active.is_(True))
            .order_by(DeliveryArea.display_order, DeliveryArea.name)
        )
    )


def get_active_delivery_area(db: Session, delivery_area_id: int) -> DeliveryArea | None:
    return db.scalar(
        select(DeliveryArea)
        .where(DeliveryArea.id == delivery_area_id)
        .where(DeliveryArea.is_active.is_(True))
        .limit(1)
    )


def list_admin_delivery_areas(db: Session) -> list[DeliveryArea]:
    return list(
        db.scalars(
            select(DeliveryArea).order_by(
                DeliveryArea.display_order,
                DeliveryArea.name,
                DeliveryArea.id,
            )
        )
    )


def create_delivery_area(
    db: Session,
    *,
    payload: DeliveryAreaWrite,
    actor: User,
) -> DeliveryArea:
    slug = resolve_unique_delivery_area_slug(db, payload.slug or slugify(payload.name))
    area = DeliveryArea(
        name=payload.name,
        slug=slug,
        display_order=payload.display_order,
        is_active=payload.is_active,
    )
    db.add(area)
    db.flush()
    write_audit_log(
        db,
        actor=actor,
        action="DELIVERY_AREA_CREATED",
        target_type="delivery_areas",
        target_id=area.id,
        description=f"{actor.username} teslimat bolgesi olusturdu: {area.name}",
    )
    db.commit()
    db.refresh(area)
    return area


def update_delivery_area(
    db: Session,
    *,
    delivery_area_id: int,
    payload: DeliveryAreaWrite,
    actor: User,
) -> DeliveryArea:
    area = db.get(DeliveryArea, delivery_area_id)
    if area is None:
        raise ValueError("Teslimat bolgesi bulunamadi.")

    slug = resolve_unique_delivery_area_slug(
        db,
        payload.slug or slugify(payload.name),
        current_id=area.id,
    )
    area.name = payload.name
    area.slug = slug
    area.display_order = payload.display_order
    area.is_active = payload.is_active
    write_audit_log(
        db,
        actor=actor,
        action="DELIVERY_AREA_UPDATED",
        target_type="delivery_areas",
        target_id=area.id,
        description=f"{actor.username} teslimat bolgesi guncelledi: {area.name}",
    )
    db.commit()
    db.refresh(area)
    return area


def resolve_unique_delivery_area_slug(
    db: Session,
    slug: str,
    *,
    current_id: int | None = None,
) -> str:
    normalized_slug = slugify(slug)
    existing = db.scalar(
        select(DeliveryArea).where(DeliveryArea.slug == normalized_slug).limit(1)
    )
    if existing is not None and existing.id != current_id:
        raise ValueError("Bu teslimat bolgesi slug degeri zaten kullaniliyor.")
    return normalized_slug
