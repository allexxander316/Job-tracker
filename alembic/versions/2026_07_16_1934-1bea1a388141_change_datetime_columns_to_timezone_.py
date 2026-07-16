"""change datetime columns to timezone aware

Revision ID: 1bea1a388141
Revises: 43e0cc59e283
Create Date: 2026-07-16 19:34:51.251943

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "1bea1a388141"
down_revision: Union[str, Sequence[str], None] = "43e0cc59e283"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("vacancies", "created_at", type_=sa.TIMESTAMP(timezone=True))
    op.alter_column("vacancies", "updated_at", type_=sa.TIMESTAMP(timezone=True))


def downgrade() -> None:
    op.alter_column("vacancies", "created_at", type_=sa.TIMESTAMP(timezone=False))
    op.alter_column("vacancies", "updated_at", type_=sa.TIMESTAMP(timezone=False))
