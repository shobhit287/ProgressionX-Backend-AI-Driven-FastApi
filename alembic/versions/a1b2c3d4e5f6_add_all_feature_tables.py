"""add split_exercises, workout_sessions, session_exercises, exercise_sets, weight_logs tables

Revision ID: a1b2c3d4e5f6
Revises: fc9302b4ca2c
Create Date: 2026-03-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'fc9302b4ca2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define enums as postgresql ENUM with create_type=False so we control creation
exercise_type_enum = ENUM('STANDARD', 'SUPERSET', 'DROPSET', 'GIANT_SET', name='exercise_type_enum', create_type=False)
session_status_enum = ENUM('IN_PROGRESS', 'COMPLETED', 'ABANDONED', name='session_status_enum', create_type=False)


def upgrade() -> None:
    """Upgrade schema."""

    # Create enums via raw SQL with IF NOT EXISTS
    op.execute("DO $$ BEGIN CREATE TYPE exercise_type_enum AS ENUM ('STANDARD', 'SUPERSET', 'DROPSET', 'GIANT_SET'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE session_status_enum AS ENUM ('IN_PROGRESS', 'COMPLETED', 'ABANDONED'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # 1. split_exercises
    op.create_table('split_exercises',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('split_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('default_sets', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('exercise_type', exercise_type_enum, nullable=False, server_default='STANDARD'),
        sa.Column('superset_group', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('rest_seconds', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['split_id'], ['workout_splits.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_split_exercises_split_id_display_order', 'split_exercises', ['split_id', 'display_order'])

    # 2. workout_sessions
    op.create_table('workout_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('split_id', sa.UUID(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', session_status_enum, nullable=False, server_default='IN_PROGRESS'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['split_id'], ['workout_splits.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workout_sessions_user_id'), 'workout_sessions', ['user_id'])
    op.create_index('ix_workout_sessions_user_started', 'workout_sessions', ['user_id', 'started_at'])
    op.create_index('ix_workout_sessions_user_split', 'workout_sessions', ['user_id', 'split_id'])

    # 3. session_exercises
    op.create_table('session_exercises',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('split_exercise_id', sa.UUID(), nullable=True),
        sa.Column('exercise_name', sa.String(length=150), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('exercise_type', exercise_type_enum, nullable=False, server_default='STANDARD'),
        sa.Column('superset_group', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['workout_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['split_exercise_id'], ['split_exercises.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_session_exercises_session_display', 'session_exercises', ['session_id', 'display_order'])

    # 4. exercise_sets
    op.create_table('exercise_sets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_exercise_id', sa.UUID(), nullable=False),
        sa.Column('set_number', sa.Integer(), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('reps', sa.Integer(), nullable=False),
        sa.Column('reps_in_reserve', sa.Integer(), nullable=True),
        sa.Column('is_warmup', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_dropset', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_exercise_id'], ['session_exercises.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_exercise_sets_session_exercise_set', 'exercise_sets', ['session_exercise_id', 'set_number'])

    # 5. weight_logs
    op.create_table('weight_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('waist_cm', sa.Float(), nullable=True),
        sa.Column('body_fat_pct', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logged_at', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'logged_at', name='uq_user_logged_at'),
    )
    op.create_index(op.f('ix_weight_logs_user_id'), 'weight_logs', ['user_id'])
    op.create_index('ix_weight_logs_user_logged_at', 'weight_logs', ['user_id', 'logged_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_weight_logs_user_logged_at', table_name='weight_logs')
    op.drop_index(op.f('ix_weight_logs_user_id'), table_name='weight_logs')
    op.drop_table('weight_logs')

    op.drop_index('ix_exercise_sets_session_exercise_set', table_name='exercise_sets')
    op.drop_table('exercise_sets')

    op.drop_index('ix_session_exercises_session_display', table_name='session_exercises')
    op.drop_table('session_exercises')

    op.drop_index('ix_workout_sessions_user_split', table_name='workout_sessions')
    op.drop_index('ix_workout_sessions_user_started', table_name='workout_sessions')
    op.drop_index(op.f('ix_workout_sessions_user_id'), table_name='workout_sessions')
    op.drop_table('workout_sessions')

    op.drop_index('ix_split_exercises_split_id_display_order', table_name='split_exercises')
    op.drop_table('split_exercises')

    op.execute("DROP TYPE IF EXISTS session_status_enum")
    op.execute("DROP TYPE IF EXISTS exercise_type_enum")
