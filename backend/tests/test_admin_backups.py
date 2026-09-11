from decimal import Decimal
from io import BytesIO
import json
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.delivery_area import DeliveryArea
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.market_settings import get_market_settings
from app.services.orders import create_order
from app.services.users import create_user


def test_admin_can_export_backup_with_data_and_uploads(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    upload_dir = use_temp_upload_dir(client, tmp_path)
    admin = create_admin(db_session)
    order = create_sample_order(db_session, image_url="/uploads/products/elma.png")
    (upload_dir / "products").mkdir(parents=True)
    (upload_dir / "products" / "elma.png").write_bytes(b"image-bytes")

    response = client.get(
        "/api/admin/backups/export",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    with ZipFile(BytesIO(response.content)) as archive:
        payload = json.loads(archive.read("backup.json").decode("utf-8"))
        names = archive.namelist()

    assert payload["format"] == "market_order_system_backup"
    assert payload["version"] == 1
    assert payload["tables"]["users"][0]["password_hash"].startswith("$argon2")
    assert payload["tables"]["orders"][0]["order_number"] == order.order_number
    assert payload["tables"]["products"][0]["image_url"] == "/uploads/products/elma.png"
    assert any(
        log["action"] == "BACKUP_EXPORTED"
        for log in payload["tables"]["audit_logs"]
    )
    assert "uploads/products/elma.png" in names


def test_admin_can_restore_backup_with_database_and_uploads(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    upload_dir = use_temp_upload_dir(client, tmp_path)
    admin = create_admin(db_session)
    order = create_sample_order(db_session, image_url="/uploads/products/elma.png")
    product = db_session.query(Product).filter_by(slug="elma-1-kg").one()
    (upload_dir / "products").mkdir(parents=True)
    image_path = upload_dir / "products" / "elma.png"
    image_path.write_bytes(b"image-bytes")

    export_response = client.get(
        "/api/admin/backups/export",
        headers=auth_headers(admin),
    )
    assert export_response.status_code == 200

    product.name = "Bozulmus Urun"
    image_path.unlink()
    db_session.commit()

    restore_response = client.post(
        "/api/admin/backups/restore",
        headers=auth_headers(admin),
        files={
            "file": (
                "market-yedek.zip",
                export_response.content,
                "application/zip",
            )
        },
    )

    assert restore_response.status_code == 200
    data = restore_response.json()
    assert data["table_counts"]["orders"] == 1
    assert data["table_counts"]["products"] == 1

    db_session.expire_all()
    restored_product = db_session.get(Product, product.id)
    restored_order = db_session.get(Order, order.id)
    assert restored_product is not None
    assert restored_product.name == "Elma 1 kg"
    assert restored_order is not None
    assert restored_order.order_number == order.order_number
    assert image_path.read_bytes() == b"image-bytes"
    assert (
        db_session.query(AuditLog)
        .filter_by(action="BACKUP_RESTORED")
        .count()
        == 1
    )


def test_backup_restore_rejects_invalid_zip(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    use_temp_upload_dir(client, tmp_path)
    admin = create_admin(db_session)

    response = client.post(
        "/api/admin/backups/restore",
        headers=auth_headers(admin),
        files={"file": ("broken.zip", b"not a zip", "application/zip")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Yedek dosyasi gecersiz veya bozuk."


def test_employee_cannot_access_admin_backups(
    client: TestClient,
    db_session: Session,
) -> None:
    employee = create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    export_response = client.get(
        "/api/admin/backups/export",
        headers=auth_headers(employee),
    )
    restore_response = client.post(
        "/api/admin/backups/restore",
        headers=auth_headers(employee),
        files={"file": ("empty.zip", b"", "application/zip")},
    )

    assert export_response.status_code == 403
    assert restore_response.status_code == 403


def use_temp_upload_dir(client: TestClient, tmp_path):
    upload_dir = tmp_path / "uploads"
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        jwt_secret="test-secret",
        upload_directory=str(upload_dir),
        max_backup_upload_bytes=10 * 1024 * 1024,
    )
    return upload_dir


def create_sample_order(
    db_session: Session,
    *,
    image_url: str | None = None,
):
    settings = get_market_settings(db_session)
    settings.minimum_order_amount = Decimal("10.00")
    settings.delivery_fee = Decimal("50.00")
    area = DeliveryArea(name="Merkez", slug="merkez", is_active=True)
    product = Product(
        name="Elma 1 kg",
        slug="elma-1-kg",
        image_url=image_url,
        price=Decimal("65.00"),
        stock_quantity=20,
        is_active=True,
    )
    db_session.add_all([area, product])
    db_session.commit()

    return create_order(
        db_session,
        OrderCreate(
            items=[{"product_id": product.id, "quantity": 2}],
            customer_first_name="Sait",
            customer_last_name="Musteri",
            phone="0532 111 22 33",
            delivery_area_id=area.id,
            neighborhood="Merkez Mahallesi",
            street="Market Sokak",
            address_line="Merkez Mahallesi Market Sokak No 10",
            payment_method="CASH_ON_DELIVERY",
            unavailable_policy="CALL_CUSTOMER",
        ),
    )


def create_admin(db_session: Session) -> User:
    return create_user(
        db_session,
        username="admin",
        password="Admin12345",
        full_name="Admin",
        role="ADMIN",
    )


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    return {"Authorization": f"Bearer {token}"}
