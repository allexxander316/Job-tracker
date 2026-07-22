"""change experience column to varchar

Revision ID: 4360d10ab58f
Revises: 1bea1a388141
Create Date: 2026-07-16 19:38:12.026075

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4360d10ab58f"  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = (
    "1bea1a388141"  # pragma: allowlist secret
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "vacancies",
        "experience",
        type_=sa.VARCHAR(),
        postgresql_using="experience::varchar",
    )


def downgrade() -> None:
    op.alter_column(
        "vacancies",
        "experience",
        type_=sa.INTEGER(),
        postgresql_using="experience::integer",
    )
