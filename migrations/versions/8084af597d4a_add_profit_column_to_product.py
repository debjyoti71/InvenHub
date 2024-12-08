"""Add profit column to product

Revision ID: 8084af597d4a
Revises: 05f6ab08087d
Create Date: 2024-12-04 23:35:11.955207

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8084af597d4a'
down_revision = '05f6ab08087d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('category', schema=None) as batch_op:
        batch_op.add_column(sa.Column('C_unique_id', sa.String(length=20), nullable=False))
        batch_op.create_unique_constraint(None, ['C_unique_id'])

    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.add_column(sa.Column('P_unique_id', sa.String(length=20), nullable=False))
        batch_op.create_unique_constraint(None, ['P_unique_id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('P_unique_id')

    with op.batch_alter_table('category', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('C_unique_id')

    # ### end Alembic commands ###