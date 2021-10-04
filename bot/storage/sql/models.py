"""
Database models used for SQL-based persisted storage
"""

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    hash = Column(String, unique=True, nullable=False)
    command_name = Column(String, nullable=False)
    command_data = Column(Text, nullable=False)
    context_data = Column(Text, nullable=False)


class MediaPlayer(Base):
    __tablename__ = "media_players"

    id = Column(Integer, primary_key=True)
    hash = Column(String, unique=True, nullable=False)
    player_data = Column(Text, nullable=False)
    context_data = Column(Text, nullable=False)
