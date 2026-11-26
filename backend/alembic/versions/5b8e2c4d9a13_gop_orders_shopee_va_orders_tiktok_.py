"""gop orders_shopee va orders_tiktok thanh mot bang orders

Chốt 08/11/2026 theo yêu cầu GVHD: một bảng `orders` có cột `platform` thay cho hai bảng riêng từng sàn
Sinh bằng `alembic revision --autogenerate` rồi đọc lại đối chiếu; phần downgrade được dọn
lại cho đọc được (CHECK viết lại dạng `IN (...)`, bỏ tham số thừa) và tạo lại ĐÚNG hai bảng của migration trước.

KHÔNG chuyển dữ liệu cũ: dữ liệu nạp lại được từ CSV (`python -m app.etl.nap_file ...`), nên upgrade xóa hai
bảng cũ cùng dữ liệu của chúng; downgrade tạo lại hai bảng RỖNG. Bảng `sync_runs` (lịch sử) không bị đụng.

Revision ID: 5b8e2c4d9a13
Revises: 27a3e34bc8f4
Create Date: 2026-11-08 22:42:18.068224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '5b8e2c4d9a13'
down_revision: Union[str, Sequence[str], None] = '27a3e34bc8f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('orders',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('platform', sa.String(length=10), nullable=False),
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
    sa.Column('nmv_is_provisional', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_affiliate', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('province', sa.String(length=100), nullable=True),
    sa.Column('province_raw', sa.String(length=100), nullable=True),
    sa.Column('hour_bucket', sa.String(length=20), nullable=True),
    sa.Column('data_source', sa.String(length=10), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('source_file', sa.String(length=255), nullable=True),
    sa.CheckConstraint("data_source IN ('api', 'file')", name='ck_orders_data_source'),
    sa.CheckConstraint("platform IN ('shopee', 'tiktok')", name='ck_orders_platform'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('platform', 'order_id', 'sku', name='uq_orders_platform_order_sku')
    )
    op.create_index('idx_orders_platform_date', 'orders', ['platform', 'order_date'], unique=False)
    op.create_index('idx_orders_platform_product', 'orders', ['platform', 'product_code'], unique=False)
    op.create_index('idx_orders_platform_shop', 'orders', ['platform', 'shop_name'], unique=False)
    op.create_index('idx_orders_platform_sku', 'orders', ['platform', 'sku'], unique=False)
    op.create_index('idx_orders_platform_status', 'orders', ['platform', 'order_status'], unique=False)
    op.drop_index(op.f('idx_tiktok_date'), table_name='orders_tiktok')
    op.drop_index(op.f('idx_tiktok_product'), table_name='orders_tiktok')
    op.drop_index(op.f('idx_tiktok_shop'), table_name='orders_tiktok')
    op.drop_index(op.f('idx_tiktok_sku'), table_name='orders_tiktok')
    op.drop_index(op.f('idx_tiktok_status'), table_name='orders_tiktok')
    op.drop_table('orders_tiktok')
    op.drop_index(op.f('idx_shopee_date'), table_name='orders_shopee')
    op.drop_index(op.f('idx_shopee_product'), table_name='orders_shopee')
    op.drop_index(op.f('idx_shopee_shop'), table_name='orders_shopee')
    op.drop_index(op.f('idx_shopee_sku'), table_name='orders_shopee')
    op.drop_index(op.f('idx_shopee_status'), table_name='orders_shopee')
    op.drop_table('orders_shopee')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('orders_shopee',
    sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
    sa.Column('shop_name', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('order_id', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('sku', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('product_code', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('order_date', sa.DATE(), autoincrement=False, nullable=False),
    sa.Column('order_created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('order_status_raw', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('order_status', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('is_returned', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('product_name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('variation', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('quantity', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('returned_quantity', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('unit_price', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('nmv', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('nmv_after_tax', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('nmv_is_provisional', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('is_affiliate', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('province', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('province_raw', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('hour_bucket', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('data_source', sa.VARCHAR(length=10), autoincrement=False, nullable=False),
    sa.Column('uploaded_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('source_file', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
    sa.CheckConstraint("data_source IN ('api', 'file')", name='ck_shopee_data_source'),
    sa.PrimaryKeyConstraint('id', name=op.f('orders_shopee_pkey')),
    sa.UniqueConstraint('order_id', 'sku', name='uq_shopee_order_sku')
    )
    op.create_index(op.f('idx_shopee_status'), 'orders_shopee', ['order_status'], unique=False)
    op.create_index(op.f('idx_shopee_sku'), 'orders_shopee', ['sku'], unique=False)
    op.create_index(op.f('idx_shopee_shop'), 'orders_shopee', ['shop_name'], unique=False)
    op.create_index(op.f('idx_shopee_product'), 'orders_shopee', ['product_code'], unique=False)
    op.create_index(op.f('idx_shopee_date'), 'orders_shopee', ['order_date'], unique=False)
    op.create_table('orders_tiktok',
    sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
    sa.Column('shop_name', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('order_id', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('sku', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('product_code', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('order_date', sa.DATE(), autoincrement=False, nullable=False),
    sa.Column('order_created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('order_status_raw', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('order_status', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('is_returned', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('product_name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('variation', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('quantity', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('returned_quantity', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('unit_price', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('sku_subtotal_after_discount', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('nmv', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('nmv_after_tax', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('order_amount', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('is_affiliate', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('province', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('province_raw', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('hour_bucket', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('data_source', sa.VARCHAR(length=10), autoincrement=False, nullable=False),
    sa.Column('uploaded_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('source_file', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
    sa.CheckConstraint("data_source IN ('api', 'file')", name='ck_tiktok_data_source'),
    sa.PrimaryKeyConstraint('id', name=op.f('orders_tiktok_pkey')),
    sa.UniqueConstraint('order_id', 'sku', name='uq_tiktok_order_sku')
    )
    op.create_index(op.f('idx_tiktok_status'), 'orders_tiktok', ['order_status'], unique=False)
    op.create_index(op.f('idx_tiktok_sku'), 'orders_tiktok', ['sku'], unique=False)
    op.create_index(op.f('idx_tiktok_shop'), 'orders_tiktok', ['shop_name'], unique=False)
    op.create_index(op.f('idx_tiktok_product'), 'orders_tiktok', ['product_code'], unique=False)
    op.create_index(op.f('idx_tiktok_date'), 'orders_tiktok', ['order_date'], unique=False)
    op.drop_index('idx_orders_platform_status', table_name='orders')
    op.drop_index('idx_orders_platform_sku', table_name='orders')
    op.drop_index('idx_orders_platform_shop', table_name='orders')
    op.drop_index('idx_orders_platform_product', table_name='orders')
    op.drop_index('idx_orders_platform_date', table_name='orders')
    op.drop_table('orders')
    # ### end Alembic commands ###
