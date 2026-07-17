"""add_rest_seconds_to_exercise_sets

Adds rest_seconds to exercise_sets: the actual rest taken BEFORE each set,
derived from the gap between consecutive sets' created_at within the same
session_exercise (ordered by set_number).

Existing rows are backfilled in-place from their timestamps so past sessions
show rest immediately. Backfill rules mirror the write-time logic in
ExerciseSetService.add_set:
  - The first set of an exercise has no preceding set -> stays NULL.
  - Dropset rows (parent_set_id NOT NULL) are back-to-back -> stay NULL.
  - Implausible gaps (> 3600s, i.e. a paused/abandoned-then-resumed session)
    are left NULL rather than recorded as a real multi-hour "rest".

Revision ID: b1c2d3e4f5a6
Revises: a7b8c9d0e1f2
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'exercise_sets',
        sa.Column('rest_seconds', sa.Integer(), nullable=True),
    )

    # Backfill existing rows from created_at gaps. LAG gives each set the
    # created_at of the immediately-preceding set (by set_number) in the same
    # exercise; the difference is the rest taken before it.
    op.execute(
        """
        WITH ordered AS (
            SELECT
                id,
                created_at,
                parent_set_id,
                LAG(created_at) OVER (
                    PARTITION BY session_exercise_id
                    ORDER BY set_number
                ) AS prev_created_at
            FROM exercise_sets
        )
        UPDATE exercise_sets AS es
        SET rest_seconds =
            EXTRACT(EPOCH FROM (o.created_at - o.prev_created_at))::int
        FROM ordered AS o
        WHERE es.id = o.id
          AND o.parent_set_id IS NULL
          AND o.prev_created_at IS NOT NULL
          AND o.created_at >= o.prev_created_at
          AND o.created_at - o.prev_created_at <= INTERVAL '3600 seconds';
        """
    )


def downgrade() -> None:
    op.drop_column('exercise_sets', 'rest_seconds')
