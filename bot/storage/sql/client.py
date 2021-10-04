import asyncio
import contextlib
import logging
import pathlib
from typing import ContextManager, Optional, List

import alembic.command
import alembic.config
import alembic.script
import pydantic
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from bot.commands import Command
from bot.media import Media, MediaPlayer
from bot.platforms import CommandContext, Platform, MediaPlayerContext
from bot.storage import base
from bot.storage.sql import models
from bot.storage.sql import migrations


logger = logging.getLogger(__name__)


class Storage(base.Storage):
    """
    SQLAlchemy/SQL based implementation of persistent data storage.
    """

    name: str = "sql"
    sessionmaker: sessionmaker

    def __init__(self, database_url: str):
        engine = create_engine(database_url)
        self.sessionmaker = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @contextlib.contextmanager
    def context(self) -> ContextManager[Session]:
        """
        Helper that wraps database operations within a transaction.
        :return:
        """
        session = self.sessionmaker()

        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def initialize(self):
        logger.debug(f"initialize: applying migrations")

        # determine alembic env.py script location
        script_directory = pathlib.Path(migrations.__file__).parent

        # determine sqlalchemy database_url
        engine = self.sessionmaker.kw.get("bind")
        database_url = engine.url

        # create alembic configuration
        config = alembic.config.Config()
        config.set_main_option("script_location", str(script_directory))
        config.set_main_option("database_url", str(database_url))

        # migrate to head
        alembic.command.upgrade(config, "head")

    async def load_conversation(self, context: CommandContext) -> Optional[Command]:
        def inner():
            with self.context() as session:
                # perform query
                conversation_hash = context.data.hash()
                query = session.query(models.Conversation)
                query = query.filter_by(hash=context.data.hash())
                exists = query.one_or_none()

                if not exists:
                    # entity not found - do nothing
                    logger.debug(f"conversation load: not found ({conversation_hash})")
                    return None

                # create new command
                logger.debug(f"conversation load: found ({conversation_hash})")
                command = Command.get_command(exists.command_name)()

                # update command and context with database data
                command.data = command.data.parse_raw(exists.command_data)
                context.data.update_from_persist_str(exists.context_data)

                # return command
                return command

        return await asyncio.get_event_loop().run_in_executor(None, inner)

    async def save_conversation(self, context: CommandContext, command: Command):
        def inner():
            with self.context() as session:
                # perform query
                conversation_hash = context.data.hash()
                query = session.query(models.Conversation)
                query = query.filter_by(hash=conversation_hash)
                db_model = query.one_or_none()

                # serialize data
                command_data = command.data.json(sort_keys=True)
                context_data = context.data.persist_str()

                if not db_model:
                    # create new entity
                    logger.debug(f"conversation save: insert ({conversation_hash})")
                    db_model = models.Conversation(
                        hash=conversation_hash,
                        command_name=command.name,
                        command_data=command_data,
                        context_data=context_data,
                    )
                else:
                    logger.debug(f"conversation save: update ({conversation_hash})")

                # perform update
                db_model.command_data = command_data
                db_model.context_data = context_data

                # commit update
                session.add(db_model)
                session.commit()

        return await asyncio.get_event_loop().run_in_executor(None, inner)

    async def delete_conversation(self, context: CommandContext):
        def inner():
            with self.context() as session:
                # perform query
                conversation_hash = context.data.hash()
                query = session.query(models.Conversation)
                query = query.filter_by(hash=conversation_hash)
                db_model = query.one_or_none()

                if not db_model:
                    # entity not found - do nothing
                    logger.debug(f"conversation delete: not found ({conversation_hash})")
                    return

                # delete entity
                logger.debug(f"conversation delete: found ({conversation_hash})")
                session.delete(db_model)
                session.commit()

        return await asyncio.get_event_loop().run_in_executor(None, inner)

    async def load_all_media_players(self, platform: Platform) -> List[MediaPlayer]:
        with self.context() as session:
            # perform query
            query = session.query(models.MediaPlayer)
            db_models = query.all()

            logger.debug(f"media players load: loading all ({len(db_models)})")
            media_players = []
            for db_model in db_models:
                # deserialize data
                data = platform.media_player_data_cls.parse_raw(db_model.context_data)

                # create media player
                context = MediaPlayerContext(data=data, platform=platform)
                media_player = await platform.get_media_player(context)

                media_players.append(media_player)

        # NOTE: not wrapped in executor because of reliance upon async methods
        return media_players

    async def load_media_player(self, media_player: MediaPlayer):
        def inner():
            with self.context() as session:
                # perform query
                media_player_hash = media_player.context.data.hash()
                query = session.query(models.MediaPlayer)
                query = query.filter_by(hash=media_player_hash)
                db_model = query.one_or_none()

                if not db_model:
                    # entity not found - do nothing
                    logger.debug(f"media player load: not found ({media_player_hash})")
                    return

                # update `media_player` with database data
                logger.debug(f"media player load: found ({media_player_hash})")
                media_player.data.update_from_persist_str(db_model.player_data)
                media_player.context.data.update_from_persist_str(db_model.context_data)

        return await asyncio.get_event_loop().run_in_executor(None, inner)

    async def save_media_player(self, media_player: MediaPlayer):
        def inner():
            with self.context() as session:
                # perform query
                media_player_hash = media_player.context.data.hash()
                query = session.query(models.MediaPlayer)
                query = query.filter_by(hash=media_player_hash)
                db_model = query.one_or_none()

                # serialize data
                player_data = media_player.data.persist_str()
                context_data = media_player.context.data.persist_str()

                if not db_model:
                    # create new database entity
                    logger.debug(f"media player save: insert ({media_player_hash})")
                    db_model = models.MediaPlayer(
                        hash=media_player_hash, player_data=player_data, context_data=context_data
                    )
                else:
                    logger.debug(f"media player save: update ({media_player_hash})")

                # update data on model
                db_model.player_data = player_data
                db_model.context_data = context_data

                # commit
                session.add(db_model)
                session.commit()

        return await asyncio.get_event_loop().run_in_executor(None, inner)

    async def delete_media_player(self, media_player: MediaPlayer):
        def inner():
            with self.context() as session:
                # perform query
                media_player_hash = media_player.context.data.hash()
                query = session.query(models.MediaPlayer)
                query = query.filter_by(hash=media_player_hash)
                db_model = query.one_or_none()

                if not db_model:
                    # entity not found - do nothing
                    logger.debug(f"media player delete: not found ({media_player_hash})")
                    return

                # delete entity
                logger.debug(f"media player delete: found ({media_player_hash})")
                session.delete(db_model)
                session.commit()

        return await asyncio.get_event_loop().run_in_executor(None, inner)
