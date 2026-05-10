"""allow multiple meal reviews

Revision ID: 99c38f4f508c
Revises: 42d8e5d2aaf3
Create Date: 2026-05-10 15:51:36.722624

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99c38f4f508c'
down_revision: Union[str, None] = '42d8e5d2aaf3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "meal_reviews_report_id_key",
        "meal_reviews",
        type_="unique",
    )

    op.create_index(
        "idx_meal_reviews_report_created",
        "meal_reviews",
        ["report_id", "created_at"],
        unique=False,
    )

    op.create_index(
        "idx_meal_reviews_coach_created",
        "meal_reviews",
        ["coach_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_meal_reviews_coach_created",
        table_name="meal_reviews",
    )

    op.drop_index(
        "idx_meal_reviews_report_created",
        table_name="meal_reviews",
    )

    op.create_unique_constraint(
        "meal_reviews_report_id_key",
        "meal_reviews",
        ["report_id"],
    )
