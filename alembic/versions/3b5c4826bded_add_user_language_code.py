"""add user language code

Revision ID: 3b5c4826bded
Revises: f4e74d24349f
Create Date: 2026-06-14 19:54:13.385738

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3b5c4826bded"
down_revision: Union[str, None] = "f4e74d24349f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "language_code",
            sa.String(length=10),
            nullable=False,
            server_default="ru",
        ),
    )
    op.create_check_constraint(
        "ck_users_language_code",
        "users",
        "language_code IN ('ru', 'en', 'cs')",
    )
    op.alter_column("users", "language_code", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_users_language_code", "users", type_="check")
    op.drop_column("users", "language_code")
