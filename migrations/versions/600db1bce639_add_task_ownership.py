
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "600db1bce639"
down_revision: Union[str, Sequence[str], None] = "b31ab9461076"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add user_id as nullable temporarily.
    op.add_column(
        "tasks",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )

    # 2. Create the index.
    op.create_index(
        "ix_tasks_user_id",
        "tasks",
        ["user_id"],
        unique=False,
    )

    # 3. Add the foreign key.
    op.create_foreign_key(
        "fk_tasks_user_id_users",
        "tasks",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 4. Preserve existing tasks by assigning them to
    # the first registered user, if one exists.
    connection = op.get_bind()

    first_user_id = connection.execute(
        sa.text("SELECT id FROM users ORDER BY id LIMIT 1")
    ).scalar()

    if first_user_id is not None:
        connection.execute(
            sa.text(
                "UPDATE tasks SET user_id = :user_id "
                "WHERE user_id IS NULL"
            ),
            {"user_id": first_user_id},
        )

    # 5. Enforce ownership only after backfilling.
    remaining_unassigned = connection.execute(
        sa.text("SELECT COUNT(*) FROM tasks WHERE user_id IS NULL")
    ).scalar_one()

    if remaining_unassigned:
        raise RuntimeError(
            "Some tasks have no owner. Create a user and assign "
            "these tasks before applying this migration."
        )

    op.alter_column(
        "tasks",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tasks_user_id_users",
        "tasks",
        type_="foreignkey",
    )

    op.drop_index("ix_tasks_user_id", table_name="tasks")

    op.drop_column("tasks", "user_id")