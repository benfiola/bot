import alembic
import sqlalchemy

import bot.storage.sql.models

config = alembic.context.config

target_metadata = bot.storage.sql.models.Base.metadata
database_url = config.get_main_option("database_url")


def run_migrations_offline():
    alembic.context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with alembic.context.begin_transaction():
        alembic.context.run_migrations()


def run_migrations_online():
    connectable = sqlalchemy.engine.create_engine(database_url)

    with connectable.connect() as connection:
        alembic.context.configure(connection=connection, target_metadata=target_metadata)

        with alembic.context.begin_transaction():
            alembic.context.run_migrations()


if alembic.context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
