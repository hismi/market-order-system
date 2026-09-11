from sqlalchemy import Engine, inspect, text


def ensure_sqlite_dev_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "orders" not in inspector.get_table_names():
        return

    order_columns = {column["name"] for column in inspector.get_columns("orders")}
    if "cancellation_reason" in order_columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE orders ADD COLUMN cancellation_reason VARCHAR(160)")
        )
