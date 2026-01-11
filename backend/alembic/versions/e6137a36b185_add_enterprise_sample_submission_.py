"""add_enterprise_sample_submission_features

Revision ID: e6137a36b185
Revises: b4b3676cc8c3
Create Date: 2026-01-09 07:29:06.317678

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e6137a36b185'
down_revision = 'b4b3676cc8c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums for PostgreSQL
    submission_status = postgresql.ENUM('pending', 'received', 'in_review', 'completed', 'rejected', 'archived', name='submissionstatus', create_type=False)
    notification_type = postgresql.ENUM('new_submission', 'status_change', 'new_reply', 'submission_assigned', 'reminder', name='notificationtype', create_type=False)
    
    submission_status.create(op.get_bind(), checkfirst=True)
    notification_type.create(op.get_bind(), checkfirst=True)
    
    # 1. Update sample_submissions table with new fields
    with op.batch_alter_table('sample_submissions', schema=None) as batch_op:
        # Add reference_number
        batch_op.add_column(sa.Column('reference_number', sa.String(length=50), nullable=True, unique=True))
        
        # Add recipient_user_id
        batch_op.add_column(sa.Column('recipient_user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_sample_submissions_recipient_user', 'users', ['recipient_user_id'], ['id'], ondelete='SET NULL')
        
        # Add status enum
        batch_op.add_column(sa.Column('status', submission_status, nullable=False, server_default='pending'))
        
        # Add read tracking
        batch_op.add_column(sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('read_by_user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_sample_submissions_read_by_user', 'users', ['read_by_user_id'], ['id'], ondelete='SET NULL')
        
        # Add updated_at
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
        
        # Create indexes
        batch_op.create_index('idx_submission_status', ['status', 'created_at'])
        batch_op.create_index('idx_submission_recipient_unread', ['recipient_user_id', 'is_read', 'created_at'])
        batch_op.create_index('idx_submission_sender_status', ['submitted_by_user_id', 'status', 'created_at'])
        batch_op.create_index('idx_submission_reference', ['reference_number'])
        batch_op.create_index(batch_op.f('ix_sample_submissions_recipient_email'), ['recipient_email'])
        batch_op.create_index(batch_op.f('ix_sample_submissions_status'), ['status'])
        batch_op.create_index(batch_op.f('ix_sample_submissions_is_read'), ['is_read'])
    
    # 2. Create message_threads table
    op.create_table('message_threads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_system_message', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['submission_id'], ['sample_submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_message_submission_date', 'message_threads', ['submission_id', 'created_at'])
    op.create_index('idx_message_sender_date', 'message_threads', ['sender_id', 'created_at'])
    op.create_index(op.f('ix_message_threads_id'), 'message_threads', ['id'])
    op.create_index(op.f('ix_message_threads_submission_id'), 'message_threads', ['submission_id'])
    op.create_index(op.f('ix_message_threads_sender_id'), 'message_threads', ['sender_id'])
    op.create_index(op.f('ix_message_threads_created_at'), 'message_threads', ['created_at'])
    
    # 3. Create submission_status_history table
    op.create_table('submission_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('old_status', submission_status, nullable=True),
        sa.Column('new_status', submission_status, nullable=False),
        sa.Column('changed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['submission_id'], ['sample_submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_status_history_submission', 'submission_status_history', ['submission_id', 'changed_at'])
    op.create_index('idx_status_history_user', 'submission_status_history', ['changed_by_user_id', 'changed_at'])
    op.create_index(op.f('ix_submission_status_history_id'), 'submission_status_history', ['id'])
    op.create_index(op.f('ix_submission_status_history_submission_id'), 'submission_status_history', ['submission_id'])
    op.create_index(op.f('ix_submission_status_history_changed_at'), 'submission_status_history', ['changed_at'])
    
    # 4. Create notifications table
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=True),
        sa.Column('notification_type', notification_type, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['submission_id'], ['sample_submissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notification_user_unread', 'notifications', ['user_id', 'is_read', 'created_at'])
    op.create_index('idx_notification_type_date', 'notifications', ['notification_type', 'created_at'])
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'])
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'])
    op.create_index(op.f('ix_notifications_submission_id'), 'notifications', ['submission_id'])
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'])
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'])
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'])
    
    # Generate reference numbers for existing submissions
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE sample_submissions 
        SET reference_number = 'SS-' || to_char(created_at, 'YYYYMMDDHH24MISS') || '-' || upper(substring(md5(random()::text), 1, 6))
        WHERE reference_number IS NULL
    """))
    
    # Make reference_number non-nullable after populating
    with op.batch_alter_table('sample_submissions', schema=None) as batch_op:
        batch_op.alter_column('reference_number', nullable=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('notifications')
    op.drop_table('submission_status_history')
    op.drop_table('message_threads')
    
    # Remove columns from sample_submissions
    with op.batch_alter_table('sample_submissions', schema=None) as batch_op:
        batch_op.drop_index('idx_submission_reference')
        batch_op.drop_index('idx_submission_sender_status')
        batch_op.drop_index('idx_submission_recipient_unread')
        batch_op.drop_index('idx_submission_status')
        batch_op.drop_index(batch_op.f('ix_sample_submissions_is_read'))
        batch_op.drop_index(batch_op.f('ix_sample_submissions_status'))
        batch_op.drop_index(batch_op.f('ix_sample_submissions_recipient_email'))
        
        batch_op.drop_constraint('fk_sample_submissions_read_by_user', type_='foreignkey')
        batch_op.drop_constraint('fk_sample_submissions_recipient_user', type_='foreignkey')
        
        batch_op.drop_column('updated_at')
        batch_op.drop_column('read_by_user_id')
        batch_op.drop_column('read_at')
        batch_op.drop_column('is_read')
        batch_op.drop_column('status')
        batch_op.drop_column('recipient_user_id')
        batch_op.drop_column('reference_number')
    
    # Drop enums
    sa.Enum(name='notificationtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='submissionstatus').drop(op.get_bind(), checkfirst=True)
