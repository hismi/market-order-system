from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.delivery_area import DeliveryArea


def test_public_delivery_areas_only_show_active_areas(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            DeliveryArea(name="Merkez", slug="merkez", display_order=20, is_active=True),
            DeliveryArea(
                name="Kapali Bolge",
                slug="kapali-bolge",
                display_order=10,
                is_active=False,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/delivery-areas")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Merkez",
            "slug": "merkez",
            "display_order": 20,
        }
    ]
