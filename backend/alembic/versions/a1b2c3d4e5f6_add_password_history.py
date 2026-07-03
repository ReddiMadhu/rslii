"""add password_history column to users table

Revision ID: a1b2c3d4e5f6
Revises: 5ebcf5ec6e5b
Create Date: 2026-07-03 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5ebcf5ec6e5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_history', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'password_history')
