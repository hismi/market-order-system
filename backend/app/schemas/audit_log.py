from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: int | None
    actor_username_snapshot: str | None
    action: str
    target_type: str
    target_id: int | None
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
