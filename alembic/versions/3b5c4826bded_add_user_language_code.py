"""add user language code

Revision ID: 3b5c4826bded
Revises: f4e74d24349f
Create Date: 2026-06-14 19:54:13.385738

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b5c4826bded'
down_revision: Union[str, None] = 'f4e74d24349f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
