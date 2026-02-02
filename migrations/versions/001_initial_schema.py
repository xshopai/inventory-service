"""Initial schema: inventory_items, reservations, stock_movements

Revision ID: 001_initial
Revises: 
Create Date: 2025-10-21 14:45:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create inventory_items table
    op.create_table(
        'inventory_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('quantity_available', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quantity_reserved', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reorder_level', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('max_stock', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('cost_per_unit', sa.DECIMAL(precision=10, scale=2), server_default='0.0'),
        sa.Column('last_restocked', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku')
    )
    
    # Create indexes for inventory_items
    op.create_index('ix_inventory_items_sku', 'inventory_items', ['sku'], unique=True)
    
    # Create reservations table
    op.create_table(
        'reservations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('order_id', sa.String(length=36), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'CONFIRMED', 'RELEASED', 'EXPIRED', name='reservationstatus'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['sku'], ['inventory_items.sku'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for reservations
    op.create_index('ix_reservations_order_id', 'reservations', ['order_id'])
    op.create_index('ix_reservations_sku', 'reservations', ['sku'])
    op.create_index('ix_reservations_status', 'reservations', ['status'])
    op.create_index('ix_reservations_expires_at', 'reservations', ['expires_at'])
    
    # Create stock_movements table
    op.create_table(
        'stock_movements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('movement_type', sa.Enum('INBOUND', 'OUTBOUND', 'ADJUSTMENT', 'RESERVED', 'RELEASED', 'DAMAGED', 'RETURNED', name='stockmovementtype'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(length=255), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=False, server_default='system'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['sku'], ['inventory_items.sku'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for stock_movements
    op.create_index('ix_stock_movements_sku', 'stock_movements', ['sku'])
    op.create_index('ix_stock_movements_type', 'stock_movements', ['movement_type'])
    op.create_index('ix_stock_movements_reference', 'stock_movements', ['reference'])
    op.create_index('ix_stock_movements_created_at', 'stock_movements', ['created_at'])


def downgrade():
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index('ix_stock_movements_created_at', table_name='stock_movements')
    op.drop_index('ix_stock_movements_reference', table_name='stock_movements')
    op.drop_index('ix_stock_movements_type', table_name='stock_movements')
    op.drop_index('ix_stock_movements_sku', table_name='stock_movements')
    op.drop_table('stock_movements')
    
    op.drop_index('ix_reservations_expires_at', table_name='reservations')
    op.drop_index('ix_reservations_status', table_name='reservations')
    op.drop_index('ix_reservations_sku', table_name='reservations')
    op.drop_index('ix_reservations_order_id', table_name='reservations')
    op.drop_table('reservations')
    
    op.drop_index('ix_inventory_items_sku', table_name='inventory_items')
    op.drop_table('inventory_items')
    
    # Drop enums
    sa.Enum(name='stockmovementtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='reservationstatus').drop(op.get_bind(), checkfirst=True)
