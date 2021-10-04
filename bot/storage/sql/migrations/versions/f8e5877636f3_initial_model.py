"""initial model

Revision ID: f8e5877636f3
Revises: 
Create Date: 2021-09-28 23:24:10.055207

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f8e5877636f3"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("command_name", sa.String(), nullable=False),
        sa.Column("command_data", sa.Text(), nullable=False),
        sa.Column("context_data", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hash"),
    )
    op.create_table(
        "media_players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("player_data", sa.Text(), nullable=False),
        sa.Column("context_data", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hash"),
    )


def downgrade():
    op.drop_table("media_players")
    op.drop_table("conversations")
