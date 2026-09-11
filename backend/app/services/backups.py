from __future__ import annotations

import json
from datetime import UTC, datetime, time
from decimal import Decimal
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.delivery_area import DeliveryArea
from app.models.market_settings import MarketSettings
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User

BACKUP_FORMAT = "market_order_system_backup"
BACKUP_VERSION = 1
BACKUP_JSON_PATH = "backup.json"
UPLOADS_ARCHIVE_PREFIX = "uploads"
BACKUP_RESTORE_ACTION = "BACKUP_RESTORED"


def build_backup_archive(db: Session, *, upload_dir: Path) -> bytes:
    payload = build_backup_payload(db)
    buffer = BytesIO()

    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            BACKUP_JSON_PATH,
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        for file_path in iter_upload_files(upload_dir):
            archive.write(file_path, build_archive_upload_path(file_path, upload_dir))

    return buffer.getvalue()


def restore_backup_archive(
    db: Session,
    *,
    upload: UploadFile,
    upload_dir: Path,
    max_bytes: int,
    actor_username: str,
) -> dict[str, object]:
    archive_bytes = read_backup_upload(upload, max_bytes)
    try:
        with ZipFile(BytesIO(archive_bytes), mode="r") as archive:
            payload = read_backup_payload(archive)
            restore_database(db, payload, actor_username=actor_username)
            restore_upload_files(archive, upload_dir)
    except BadZipFile as error:
        raise ValueError("Yedek dosyasi gecersiz veya bozuk.") from error

    return {
        "restored_at": datetime.now(UTC).isoformat(),
        "table_counts": count_backup_rows(payload),
    }


def build_backup_payload(db: Session) -> dict[str, object]:
    return {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "tables": {
            "market_settings": [
                serialize_market_settings(item)
                for item in db.scalars(select(MarketSettings).order_by(MarketSettings.id))
            ],
            "categories": [
                serialize_category(item)
                for item in db.scalars(select(Category).order_by(Category.id))
            ],
            "delivery_areas": [
                serialize_delivery_area(item)
                for item in db.scalars(select(DeliveryArea).order_by(DeliveryArea.id))
            ],
            "products": [
                serialize_product(item)
                for item in db.scalars(select(Product).order_by(Product.id))
            ],
            "users": [
                serialize_user(item)
                for item in db.scalars(select(User).order_by(User.id))
            ],
            "orders": [
                serialize_order(item)
                for item in db.scalars(
                    select(Order)
                    .options(selectinload(Order.items))
                    .order_by(Order.id)
                )
            ],
            "order_items": [
                serialize_order_item(item)
                for item in db.scalars(select(OrderItem).order_by(OrderItem.id))
            ],
            "audit_logs": [
                serialize_audit_log(item)
                for item in db.scalars(select(AuditLog).order_by(AuditLog.id))
            ],
        },
    }


def restore_database(
    db: Session,
    payload: dict[str, object],
    *,
    actor_username: str,
) -> None:
    validate_backup_payload(payload)
    tables = payload["tables"]
    if not isinstance(tables, dict):
        raise ValueError("Yedek dosyasinda tablo bilgisi bulunamadi.")

    try:
        db.query(AuditLog).delete(synchronize_session=False)
        db.query(OrderItem).delete(synchronize_session=False)
        db.query(Order).delete(synchronize_session=False)
        db.query(Product).delete(synchronize_session=False)
        db.query(Category).delete(synchronize_session=False)
        db.query(DeliveryArea).delete(synchronize_session=False)
        db.query(MarketSettings).delete(synchronize_session=False)
        db.query(User).delete(synchronize_session=False)
        db.expunge_all()

        db.add_all(
            MarketSettings(**deserialize_market_settings(item))
            for item in get_backup_table(tables, "market_settings")
        )
        db.add_all(
            Category(**deserialize_category(item))
            for item in get_backup_table(tables, "categories")
        )
        db.add_all(
            DeliveryArea(**deserialize_delivery_area(item))
            for item in get_backup_table(tables, "delivery_areas")
        )
        db.add_all(
            User(**deserialize_user(item))
            for item in get_backup_table(tables, "users")
        )
        db.add_all(
            Product(**deserialize_product(item))
            for item in get_backup_table(tables, "products")
        )
        db.add_all(
            Order(**deserialize_order(item))
            for item in get_backup_table(tables, "orders")
        )
        db.add_all(
            OrderItem(**deserialize_order_item(item))
            for item in get_backup_table(tables, "order_items")
        )
        db.add_all(
            AuditLog(**deserialize_audit_log(item))
            for item in get_backup_table(tables, "audit_logs")
        )
        db.add(
            AuditLog(
                actor_user_id=None,
                actor_username_snapshot=actor_username,
                action=BACKUP_RESTORE_ACTION,
                target_type="backups",
                target_id=None,
                description=f"{actor_username} yedekten geri yukleme yapti.",
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise


def read_backup_upload(upload: UploadFile, max_bytes: int) -> bytes:
    contents = upload.file.read(max_bytes + 1)
    if not contents:
        raise ValueError("Bos yedek dosyasi yuklenemez.")

    if len(contents) > max_bytes:
        max_mb = max_bytes / 1024 / 1024
        raise ValueError(f"Yedek dosyasi en fazla {max_mb:g} MB olabilir.")

    return contents


def read_backup_payload(archive: ZipFile) -> dict[str, object]:
    if BACKUP_JSON_PATH not in archive.namelist():
        raise ValueError("Yedek dosyasinda backup.json bulunamadi.")

    try:
        payload = json.loads(archive.read(BACKUP_JSON_PATH).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Yedek icerigi okunamadi.") from error

    if not isinstance(payload, dict):
        raise ValueError("Yedek icerigi gecersiz.")

    validate_backup_payload(payload)
    return payload


def validate_backup_payload(payload: dict[str, object]) -> None:
    if payload.get("format") != BACKUP_FORMAT:
        raise ValueError("Bu dosya market sistemi yedegi degil.")

    if payload.get("version") != BACKUP_VERSION:
        raise ValueError("Yedek dosyasi surumu desteklenmiyor.")

    tables = payload.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Yedek dosyasinda tablo bilgisi bulunamadi.")

    for table_name in expected_table_names():
        if not isinstance(tables.get(table_name), list):
            raise ValueError(f"Yedek dosyasinda {table_name} tablosu eksik.")


def restore_upload_files(archive: ZipFile, upload_dir: Path) -> None:
    upload_root = upload_dir.resolve()
    upload_root.mkdir(parents=True, exist_ok=True)

    for info in archive.infolist():
        if info.is_dir() or not info.filename.startswith(f"{UPLOADS_ARCHIVE_PREFIX}/"):
            continue

        relative_path = get_safe_upload_relative_path(info.filename)
        target_path = (upload_root / relative_path).resolve()
        target_path.relative_to(upload_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(archive.read(info.filename))


def get_safe_upload_relative_path(archive_path: str) -> Path:
    pure_path = PurePosixPath(archive_path)
    parts = pure_path.parts
    if len(parts) < 2 or parts[0] != UPLOADS_ARCHIVE_PREFIX:
        raise ValueError("Yedek dosyasinda gecersiz dosya yolu var.")

    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Yedek dosyasinda gecersiz dosya yolu var.")

    return Path(*parts[1:])


def iter_upload_files(upload_dir: Path) -> list[Path]:
    if not upload_dir.exists():
        return []

    return [
        path
        for path in sorted(upload_dir.rglob("*"))
        if path.is_file()
    ]


def build_archive_upload_path(file_path: Path, upload_dir: Path) -> str:
    relative_path = file_path.relative_to(upload_dir).as_posix()
    return f"{UPLOADS_ARCHIVE_PREFIX}/{relative_path}"


def count_backup_rows(payload: dict[str, object]) -> dict[str, int]:
    tables = payload.get("tables", {})
    if not isinstance(tables, dict):
        return {}

    return {
        table_name: len(rows) if isinstance(rows, list) else 0
        for table_name, rows in tables.items()
    }


def expected_table_names() -> tuple[str, ...]:
    return (
        "market_settings",
        "categories",
        "delivery_areas",
        "products",
        "users",
        "orders",
        "order_items",
        "audit_logs",
    )


def get_backup_table(tables: dict[str, object], table_name: str) -> list[dict[str, object]]:
    rows = tables[table_name]
    if not isinstance(rows, list):
        raise ValueError(f"Yedek dosyasinda {table_name} tablosu gecersiz.")

    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Yedek dosyasinda {table_name} satirlari gecersiz.")

    return rows


def serialize_market_settings(item: MarketSettings) -> dict[str, object]:
    return {
        "id": item.id,
        "market_name": item.market_name,
        "phone": item.phone,
        "whatsapp_number": item.whatsapp_number,
        "is_open": item.is_open,
        "opening_time": serialize_time(item.opening_time),
        "closing_time": serialize_time(item.closing_time),
        "minimum_order_amount": serialize_decimal(item.minimum_order_amount),
        "delivery_fee": serialize_decimal(item.delivery_fee),
        "created_at": serialize_datetime(item.created_at),
        "updated_at": serialize_datetime(item.updated_at),
    }


def deserialize_market_settings(row: dict[str, object]) -> dict[str, object]:
    return {
        **row,
        "opening_time": parse_time(row.get("opening_time")),
        "closing_time": parse_time(row.get("closing_time")),
        "minimum_order_amount": Decimal(str(row["minimum_order_amount"])),
        "delivery_fee": Decimal(str(row["delivery_fee"])),
        "created_at": parse_datetime(row.get("created_at")),
        "updated_at": parse_datetime(row.get("updated_at")),
    }


def serialize_category(item: Category) -> dict[str, object]:
    return {
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        "description": item.description,
        "display_order": item.display_order,
        "is_active": item.is_active,
        "created_at": serialize_datetime(item.created_at),
        "updated_at": serialize_datetime(item.updated_at),
    }


def deserialize_category(row: dict[str, object]) -> dict[str, object]:
    return {
        **row,
        "created_at": parse_datetime(row.get("created_at")),
        "updated_at": parse_datetime(row.get("updated_at")),
    }


def serialize_delivery_area(item: DeliveryArea) -> dict[str, object]:
    return {
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        "display_order": item.display_order,
        "is_active": item.is_active,
        "created_at": serialize_datetime(item.created_at),
        "updated_at": serialize_datetime(item.updated_at),
    }


def deserialize_delivery_area(row: dict[str, object]) -> dict[str, object]:
    return {
        **row,
        "created_at": parse_datetime(row.get("created_at")),
        "updated_at": parse_datetime(row.get("updated_at")),
    }


def serialize_product(item: Product) -> dict[str, object]:
    return {
        "id": item.id,
        "category_id": item.category_id,
        "name": item.name,
        "slug": item.slug,
        "description": item.description,
        "sku": item.sku,
        "image_url": item.image_url,
        "price": serialize_decimal(item.price),
        "stock_quantity": item.stock_quantity,
        "is_active": item.is_active,
        "created_at": serialize_datetime(item.created_at),
        "updated_at": serialize_datetime(item.updated_at),
    }


def deserialize_product(row: dict[str, object]) -> dict[str, object]:
    return {
        **row,
        "price": Decimal(str(row["price"])),
        "created_at": parse_datetime(row.get("created_at")),
        "updated_at": parse_datetime(row.get("updated_at")),
    }


def serialize_user(item: User) -> dict[str, object]:
    return {
        "id": item.id,
        "username": item.username,
        "full_name": item.full_name,
        "role": item.role,
        "password_hash": item.password_hash,
        "is_active": item.is_active,
        "created_at": serialize_datetime(item.created_at),
        "updated_at": serialize_datetime(item.updated_at),
    }


def deserialize_user(row: dict[str, object]) -> dict[str, object]:
    return {
        **row,
        "created_at": parse_datetime(row.get("created_at")),
        "updated_at": parse_datetime(row.get("updated_at")),
    }


def serialize_order(item: Order) -> dict[str, object]:
    return {
        "id": item.id,
        "order_number": item.order_number,
        "status": item.status,
        "customer_first_name": item.customer_first_name,
        "customer_last_name": item.customer_last_name,
        "phone": item.phone,
        "delivery_area_id": item.delivery_area_id,
        "delivery_area_name_snapshot": item.delivery_area_name_snapshot,
        "neighborhood": item.neighborhood,
        "street": item.street,
        "apartment": item.apartment,
        "flat": item.flat,
        "address_line": item.address_line,
        "address_directions": item.address_directions,
        "order_note": item.order_note,
        "payment_method": item.payment_method,
        "unavailable_policy": item.unavailable_policy,
        "cancellation_reason": item.cancellation_reason,
        "subtotal": serialize_decimal(item.subtotal),
        "delivery_fee": serialize_decimal(item.delivery_fee),
        "grand_total": serialize_decimal(item.grand_total),
        "created_at": serialize_datetime(item.created_at),
        "updated_at": serialize_datetime(item.updated_at),
    }


def deserialize_order(row: dict[str, object]) -> dict[str, object]:
    return {
        **row,
        "subtotal": Decimal(str(row["subtotal"])),
        "delivery_fee": Decimal(str(row["delivery_fee"])),
        "grand_total": Decimal(str(row["grand_total"])),
        "created_at": parse_datetime(row.get("created_at")),
        "updated_at": parse_datetime(row.get("updated_at")),
    }


def serialize_order_item(item: OrderItem) -> dict[str, object]:
    return {
        "id": item.id,
        "order_id": item.order_id,
        "product_id": item.product_id,
        "product_name_snapshot": item.product_name_snapshot,
        "unit_price_snapshot": serialize_decimal(item.unit_price_snapshot),
        "quantity": item.quantity,
        "line_total": serialize_decimal(item.line_total),
        "created_at": serialize_datetime(item.created_at),
    }


def deserialize_order_item(row: dict[str, object]) -> dict[str, object]:
    return {
        **row,
        "unit_price_snapshot": Decimal(str(row["unit_price_snapshot"])),
        "line_total": Decimal(str(row["line_total"])),
        "created_at": parse_datetime(row.get("created_at")),
    }


def serialize_audit_log(item: AuditLog) -> dict[str, object]:
    return {
        "id": item.id,
        "actor_user_id": item.actor_user_id,
        "actor_username_snapshot": item.actor_username_snapshot,
        "action": item.action,
        "target_type": item.target_type,
        "target_id": item.target_id,
        "description": item.description,
        "created_at": serialize_datetime(item.created_at),
    }


def deserialize_audit_log(row: dict[str, object]) -> dict[str, object]:
    return {
        **row,
        "created_at": parse_datetime(row.get("created_at")),
    }


def serialize_decimal(value: Decimal) -> str:
    return f"{value:.2f}"


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def serialize_time(value: time | None) -> str | None:
    return value.isoformat() if value else None


def parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError("Yedek dosyasinda gecersiz tarih var.")


def parse_time(value: object) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        return time.fromisoformat(value)
    raise ValueError("Yedek dosyasinda gecersiz saat var.")
