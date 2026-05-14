"""allow archived meal report photos

Revision ID: f4e74d24349f
Revises: f0b9dc74d5a4
Create Date: 2026-05-14 10:41:02.917502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4e74d24349f'
down_revision: Union[str, None] = 'f0b9dc74d5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_report_photos_processing",
        "meal_report_photos",
        type_="check",
    )
    op.create_check_constraint(
        "ck_report_photos_processing",
        "meal_report_photos",
        "processing_status IN ('pending', 'stored', 'failed', 'archived')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_report_photos_processing",
        "meal_report_photos",
        type_="check",
    )
    op.create_check_constraint(
        "ck_report_photos_processing",
        "meal_report_photos",
        "processing_status IN ('pending', 'stored', 'failed')",
    )
