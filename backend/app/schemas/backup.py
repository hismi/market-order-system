from datetime import datetime

from pydantic import BaseModel


class BackupRestoreRead(BaseModel):
    restored_at: datetime
    table_counts: dict[str, int]
