"""create identity tables"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(50), unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100)),
        sa.Column('last_name', sa.String(100)),
        sa.Column('phone_number', sa.String(20)),
        sa.Column('date_of_birth', sa.Date()),
        sa.Column('country_code', sa.String(2)),
        sa.Column('timezone', sa.String(50), server_default='UTC'),
        sa.Column('language', sa.String(10), server_default='en'),
        sa.Column('profile_picture_url', sa.String(500)),
        sa.Column('account_type', sa.String(20), server_default='standard'),
        sa.Column('account_status', sa.String(20), server_default='active'),
        sa.Column('email_verified', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('email_verification_token', sa.String(100)),
        sa.Column('password_reset_token', sa.String(100)),
        sa.Column('password_reset_expires_at', sa.DateTime()),
        sa.Column('last_login_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('is_system_role', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('hierarchy_level', sa.Integer(), server_default='0'),
        sa.Column('parent_role_id', sa.String(36), sa.ForeignKey('roles.id')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_role_hierarchy', 'roles', ['parent_role_id', 'hierarchy_level'])

    op.create_table(
        'permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(150), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('resource', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_permission_resource', 'permissions', ['resource', 'action'])

    op.create_table(
        'role_permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('role_id', sa.String(36), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('permission_id', sa.String(36), sa.ForeignKey('permissions.id'), nullable=False),
        sa.Column('granted_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('granted_by', sa.String(36), sa.ForeignKey('users.id')),
    )
    op.create_index('idx_role_perms', 'role_permissions', ['role_id'])
    op.create_index('idx_perm_roles', 'role_permissions', ['permission_id'])

    op.create_table(
        'user_roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role_id', sa.String(36), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('assigned_by', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1')),
    )
    op.create_index('idx_user_roles', 'user_roles', ['user_id', 'is_active'])
    op.create_index('idx_role_users', 'user_roles', ['role_id', 'is_active'])

    op.create_table(
        'api_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('token_name', sa.String(100), nullable=False),
        sa.Column('token_type', sa.String(20), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('role_restrictions', sa.JSON(), server_default='{}'),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('last_used_at', sa.DateTime()),
        sa.Column('is_revoked', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'kyc_verifications',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kyc_level', sa.String(20), nullable=False, server_default='basic'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('submitted_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('reviewed_at', sa.DateTime()),
        sa.Column('reviewed_by', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('rejection_reason', sa.Text()),
        sa.Column('compliance_score', sa.Integer()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'kyc_documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('kyc_verification_id', sa.String(36), sa.ForeignKey('kyc_verifications.id'), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('encryption_key_id', sa.String(100), nullable=False),
        sa.Column('ocr_data', sa.JSON()),
        sa.Column('validation_status', sa.String(20), server_default='pending'),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'permission_audit_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource', sa.String(100), nullable=False),
        sa.Column('permission_checked', sa.String(100)),
        sa.Column('access_granted', sa.Boolean(), nullable=False),
        sa.Column('role_context', sa.JSON()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_audit_user', 'permission_audit_log', ['user_id', 'created_at'])
    op.create_index('idx_audit_resource', 'permission_audit_log', ['resource', 'created_at'])


def downgrade() -> None:
    op.drop_index('idx_audit_resource', table_name='permission_audit_log')
    op.drop_index('idx_audit_user', table_name='permission_audit_log')
    op.drop_table('permission_audit_log')
    op.drop_table('kyc_documents')
    op.drop_table('kyc_verifications')
    op.drop_table('api_tokens')
    op.drop_index('idx_role_users', table_name='user_roles')
    op.drop_index('idx_user_roles', table_name='user_roles')
    op.drop_table('user_roles')
    op.drop_index('idx_perm_roles', table_name='role_permissions')
    op.drop_index('idx_role_perms', table_name='role_permissions')
    op.drop_table('role_permissions')
    op.drop_index('idx_permission_resource', table_name='permissions')
    op.drop_table('permissions')
    op.drop_index('idx_role_hierarchy', table_name='roles')
    op.drop_table('roles')
    op.drop_table('users')
