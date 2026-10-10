"""initial_schema

Revision ID: 3eee3d340ae9
Revises:
Create Date: 2026-10-10 17:00:44.628801

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3eee3d340ae9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all core V1 database tables."""
    # 1. Sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_token', sa.String(length=64), nullable=False, comment='Cryptographically random secret — never treat session_id as auth'),
        sa.Column('language', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('private_mode', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sessions_session_token'), 'sessions', ['session_token'], unique=True)

    # 2. Reminders table
    op.create_table(
        'reminders',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('remind_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False, comment='pending | notified | completed | cancelled'),
        sa.Column('language', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_reminders_session_status', 'reminders', ['session_id', 'status'], unique=False)
    op.create_index(
        'idx_reminders_due',
        'reminders',
        ['remind_at'],
        unique=False,
        postgresql_where=sa.text("status = 'pending'")
    )

    # 3. Notes table
    op.create_table(
        'notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('source_type', sa.String(length=30), nullable=True, comment='manual | pdf_summary | research'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notes_session_id'), 'notes', ['session_id'], unique=False)

    # 4. Uploaded files table
    op.create_table(
        'uploaded_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False, comment='Filesystem path — deletion service must remove this file'),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_uploaded_files_session_id'), 'uploaded_files', ['session_id'], unique=False)

    # 5. Usage logs table
    op.create_table(
        'usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Nullified on session deletion — retains anonymized metrics'),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False, comment='chat | reminder | research | tts | asr'),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, comment='success | error | timeout'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_usage_session', 'usage_logs', ['session_id'], unique=False)
    op.create_index('idx_usage_created', 'usage_logs', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_index('idx_usage_created', table_name='usage_logs')
    op.drop_index('idx_usage_session', table_name='usage_logs')
    op.drop_table('usage_logs')

    op.drop_index(op.f('ix_uploaded_files_session_id'), table_name='uploaded_files')
    op.drop_table('uploaded_files')

    op.drop_index(op.f('ix_notes_session_id'), table_name='notes')
    op.drop_table('notes')

    op.drop_index('idx_reminders_due', table_name='reminders')
    op.drop_index('idx_reminders_session_status', table_name='reminders')
    op.drop_table('reminders')

    op.drop_index(op.f('ix_sessions_session_token'), table_name='sessions')
    op.drop_table('sessions')
