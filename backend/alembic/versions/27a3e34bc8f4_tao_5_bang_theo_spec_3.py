"""tao 5 bang theo SPEC 3

Migration đầu tiên: tạo 5 bảng orders_shopee, orders_tiktok, users, sync_runs,
platform_tokens đúng như CREATE TABLE ở SPEC §3 (bản 12/10/2026, đã bỏ 5 cột).

Sinh bằng `alembic revision --autogenerate` từ app/models/, rồi đọc lại từng
dòng đối chiếu §3. Phần DDL không phải sửa: CHECK, DEFAULT, UNIQUE, index đều
được sinh đủ vì đã khai báo tường minh trong model (chi tiết: TRACKLOG bước 6).
Chỉ sửa tay chú thích. Thứ tự tạo bảng: users trước sync_runs vì
sync_runs.triggered_by là khóa ngoại tới users.id.

Revision ID: 27a3e34bc8f4
Revises:
Create Date: 2026-10-12 23:01:52.793049

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27a3e34bc8f4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Tạo 5 bảng và 10 index của 2 bảng đơn hàng."""
    op.create_table('orders_shopee',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('shop_name', sa.String(length=50), nullable=False),
    sa.Column('order_id', sa.String(length=50), nullable=False),
    sa.Column('sku', sa.String(length=100), nullable=False),
    sa.Column('product_code', sa.String(length=50), nullable=True),
    sa.Column('order_date', sa.Date(), nullable=False),
    sa.Column('order_created_at', sa.DateTime(), nullable=True),
    sa.Column('order_status_raw', sa.Text(), nullable=True),
    sa.Column('order_status', sa.String(length=20), nullable=False),
    sa.Column('is_returned', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('product_name', sa.Text(), nullable=True),
    sa.Column('variation', sa.Text(), nullable=True),
    sa.Column('quantity', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('returned_quantity', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('nmv', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('nmv_after_tax', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('nmv_is_provisional', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_affiliate', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('province', sa.String(length=100), nullable=True),
    sa.Column('province_raw', sa.String(length=100), nullable=True),
    sa.Column('hour_bucket', sa.String(length=20), nullable=True),
    sa.Column('data_source', sa.String(length=10), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('source_file', sa.String(length=255), nullable=True),
    sa.CheckConstraint("data_source IN ('api', 'file')", name='ck_shopee_data_source'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('order_id', 'sku', name='uq_shopee_order_sku')
    )
    op.create_index('idx_shopee_date', 'orders_shopee', ['order_date'], unique=False)
    op.create_index('idx_shopee_product', 'orders_shopee', ['product_code'], unique=False)
    op.create_index('idx_shopee_shop', 'orders_shopee', ['shop_name'], unique=False)
    op.create_index('idx_shopee_sku', 'orders_shopee', ['sku'], unique=False)
    op.create_index('idx_shopee_status', 'orders_shopee', ['order_status'], unique=False)
    op.create_table('orders_tiktok',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('shop_name', sa.String(length=50), nullable=False),
    sa.Column('order_id', sa.String(length=50), nullable=False),
    sa.Column('sku', sa.String(length=100), nullable=False),
    sa.Column('product_code', sa.String(length=50), nullable=True),
    sa.Column('order_date', sa.Date(), nullable=False),
    sa.Column('order_created_at', sa.DateTime(), nullable=True),
    sa.Column('order_status_raw', sa.Text(), nullable=True),
    sa.Column('order_status', sa.String(length=20), nullable=False),
    sa.Column('is_returned', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('product_name', sa.Text(), nullable=True),
    sa.Column('variation', sa.Text(), nullable=True),
    sa.Column('quantity', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('returned_quantity', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('sku_subtotal_after_discount', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('nmv', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('nmv_after_tax', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('order_amount', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('is_affiliate', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('province', sa.String(length=100), nullable=True),
    sa.Column('province_raw', sa.String(length=100), nullable=True),
    sa.Column('hour_bucket', sa.String(length=20), nullable=True),
    sa.Column('data_source', sa.String(length=10), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('source_file', sa.String(length=255), nullable=True),
    sa.CheckConstraint("data_source IN ('api', 'file')", name='ck_tiktok_data_source'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('order_id', 'sku', name='uq_tiktok_order_sku')
    )
    op.create_index('idx_tiktok_date', 'orders_tiktok', ['order_date'], unique=False)
    op.create_index('idx_tiktok_product', 'orders_tiktok', ['product_code'], unique=False)
    op.create_index('idx_tiktok_shop', 'orders_tiktok', ['shop_name'], unique=False)
    op.create_index('idx_tiktok_sku', 'orders_tiktok', ['sku'], unique=False)
    op.create_index('idx_tiktok_status', 'orders_tiktok', ['order_status'], unique=False)
    op.create_table('platform_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('platform', sa.String(length=20), nullable=False),
    sa.Column('shop_name', sa.String(length=50), nullable=False),
    sa.Column('shop_ref', sa.String(length=100), nullable=False),
    sa.Column('access_token', sa.Text(), nullable=False),
    sa.Column('refresh_token', sa.Text(), nullable=False),
    sa.Column('access_expires_at', sa.DateTime(), nullable=False),
    sa.Column('refresh_expires_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("platform IN ('shopee', 'tiktok')", name='ck_platform_tokens_platform'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('platform', 'shop_name', name='uq_token_shop')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=10), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role IN ('admin', 'user')", name='ck_users_role'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('sync_runs',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('platform', sa.String(length=20), nullable=False),
    sa.Column('shop_name', sa.String(length=50), nullable=True),
    sa.Column('source', sa.String(length=15), nullable=False),
    sa.Column('trigger_type', sa.String(length=10), server_default=sa.text("'schedule'"), nullable=False),
    sa.Column('window_from', sa.DateTime(), nullable=True),
    sa.Column('window_to', sa.DateTime(), nullable=True),
    sa.Column('file_name', sa.String(length=255), nullable=True),
    sa.Column('api_calls', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('orders_fetched', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('rows_total', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('rows_inserted', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('rows_updated', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('rows_sku_fallback', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('rows_sku_unknown', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('rows_status_unknown', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('rows_province_unmapped', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('rows_product_unmapped', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('triggered_by', sa.Integer(), nullable=True),
    sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=10), server_default=sa.text("'running'"), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.CheckConstraint("platform IN ('shopee', 'tiktok')", name='ck_sync_runs_platform'),
    sa.CheckConstraint("source IN ('api', 'file_auto', 'file_manual')", name='ck_sync_runs_source'),
    sa.CheckConstraint("status IN ('running', 'success', 'failed')", name='ck_sync_runs_status'),
    sa.CheckConstraint("trigger_type IN ('schedule', 'manual')", name='ck_sync_runs_trigger_type'),
    sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Xóa 5 bảng theo thứ tự ngược: sync_runs trước users (khóa ngoại)."""
    op.drop_table('sync_runs')
    op.drop_table('users')
    op.drop_table('platform_tokens')
    op.drop_index('idx_tiktok_status', table_name='orders_tiktok')
    op.drop_index('idx_tiktok_sku', table_name='orders_tiktok')
    op.drop_index('idx_tiktok_shop', table_name='orders_tiktok')
    op.drop_index('idx_tiktok_product', table_name='orders_tiktok')
    op.drop_index('idx_tiktok_date', table_name='orders_tiktok')
    op.drop_table('orders_tiktok')
    op.drop_index('idx_shopee_status', table_name='orders_shopee')
    op.drop_index('idx_shopee_sku', table_name='orders_shopee')
    op.drop_index('idx_shopee_shop', table_name='orders_shopee')
    op.drop_index('idx_shopee_product', table_name='orders_shopee')
    op.drop_index('idx_shopee_date', table_name='orders_shopee')
    op.drop_table('orders_shopee')
