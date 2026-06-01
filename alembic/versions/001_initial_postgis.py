"""Initial PostGIS migration

Revision ID: 001_initial_postgis
Revises: 
Create Date: 2026-06-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = '001_initial_postgis'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostGIS Extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Create Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 3. Create API Keys Table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key_name', sa.String(length=100), nullable=False),
        sa.Column('hashed_key', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_hashed_key'), 'api_keys', ['hashed_key'], unique=True)

    # 4. Create Urban Zoning Layers Table
    op.create_table(
        'urban_zoning_layers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('zoning_color_code', sa.String(length=20), nullable=False),
        sa.Column('zone_type_name', sa.String(length=255), nullable=False),
        sa.Column('far_limit', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('osr_limit', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('construction_restrictions_text', sa.Text(), nullable=True),
        sa.Column('published_fiscal_year', sa.Integer(), nullable=True),
        sa.Column('source_filename', sa.String(length=500), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('geom', Geometry(geometry_type='MULTIPOLYGON', srid=4326, spatial_index=False, from_text='ST_GeomFromEWKT', name='geometry'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_urban_zoning_layers_zoning_color_code'), 'urban_zoning_layers', ['zoning_color_code'], unique=False)
    op.create_index(op.f('ix_urban_zoning_layers_published_fiscal_year'), 'urban_zoning_layers', ['published_fiscal_year'], unique=False)
    op.create_index(op.f('ix_urban_zoning_layers_is_active'), 'urban_zoning_layers', ['is_active'], unique=False)

    # Add PostGIS spatial index explicitly
    op.create_index('idx_urban_zoning_layers_geom', 'urban_zoning_layers', ['geom'], postgresql_using='gist')

    # 5. Create Land Plots Table
    op.create_table(
        'land_plots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plot_name', sa.String(length=255), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('total_area_sqm', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('address_text', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('geom', Geometry(geometry_type='POLYGON', srid=4326, spatial_index=False, from_text='ST_GeomFromEWKT', name='geometry'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Add spatial index explicitly
    op.create_index('idx_land_plots_geom', 'land_plots', ['geom'], postgresql_using='gist')

    # 6. Create Spatial Audit Logs Table
    op.create_table(
        'spatial_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plot_id', sa.Integer(), nullable=False),
        sa.Column('audit_date', sa.DateTime(), nullable=False),
        sa.Column('intersection_results', sa.JSON(), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=False),
        sa.Column('audited_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['audited_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['plot_id'], ['land_plots.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. Create Zoning Change History Table
    op.create_table(
        'zoning_change_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('layer_id', sa.Integer(), nullable=False),
        sa.Column('change_type', sa.String(length=20), nullable=False),
        sa.Column('old_far_limit', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('new_far_limit', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('old_osr_limit', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('new_osr_limit', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('old_zone_type', sa.String(length=255), nullable=True),
        sa.Column('new_zone_type', sa.String(length=255), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('changed_by', sa.String(length=255), nullable=True),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('change_notes', sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(['layer_id'], ['urban_zoning_layers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('zoning_change_history')
    op.drop_table('spatial_audit_logs')
    
    # Drop spatial index and geometry column before dropping table for clean cleanup
    op.drop_index('idx_land_plots_geom')
    op.drop_table('land_plots')
    
    op.drop_index('idx_urban_zoning_layers_geom')
    op.drop_table('urban_zoning_layers')
    
    op.drop_index(op.f('ix_api_keys_hashed_key'), table_name='api_keys')
    op.drop_table('api_keys')
    
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    op.execute("DROP EXTENSION IF EXISTS postgis;")
