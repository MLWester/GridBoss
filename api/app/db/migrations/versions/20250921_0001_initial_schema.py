from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20250921_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    league_role = sa.Enum("OWNER", "ADMIN", "STEWARD", "DRIVER", name="league_role")

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("discord_id", sa.String(), nullable=True),
        sa.Column("discord_username", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("discord_id", name="uq_users_discord_id"),
    )

    op.create_table(
        "leagues",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), server_default=sa.text("'FREE'"), nullable=False),
        sa.Column("driver_limit", sa.Integer(), server_default=sa.text("20"), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_leagues_owner_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_leagues"),
        sa.UniqueConstraint("slug", name="uq_leagues_slug"),
    )

    op.create_table(
        "memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("league_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", league_role, nullable=False),
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name="fk_memberships_league_id_leagues",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_memberships_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
        sa.UniqueConstraint("league_id", "user_id", name="uq_memberships_league_user"),
    )

    op.create_table(
        "teams",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("league_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["league_id"], ["leagues.id"], name="fk_teams_league_id_leagues", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_teams"),
        sa.UniqueConstraint("league_id", "name", name="uq_teams_league_name"),
    )

    op.create_table(
        "drivers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("league_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("discord_id", sa.String(), nullable=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["league_id"], ["leagues.id"], name="fk_drivers_league_id_leagues", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name="fk_drivers_team_id_teams", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_drivers_user_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_drivers"),
        sa.UniqueConstraint("league_id", "display_name", name="uq_drivers_league_display"),
    )

    op.create_table(
        "seasons",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("league_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["league_id"], ["leagues.id"], name="fk_seasons_league_id_leagues", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_seasons"),
    )

    op.create_table(
        "events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("league_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("season_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("track", sa.String(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("laps", sa.Integer(), nullable=True),
        sa.Column("distance_km", sa.Numeric(6, 2), nullable=True),
        sa.Column("status", sa.String(), server_default=sa.text("'SCHEDULED'"), nullable=False),
        sa.ForeignKeyConstraint(
            ["league_id"], ["leagues.id"], name="fk_events_league_id_leagues", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["season_id"], ["seasons.id"], name="fk_events_season_id_seasons", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
    )
    op.create_index("ix_events_league_start_time", "events", ["league_id", "start_time"])
    op.create_index(
        "ix_events_status_scheduled",
        "events",
        ["status"],
        postgresql_where=sa.text("status = 'SCHEDULED'"),
    )

    op.create_table(
        "points_schemes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("league_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("season_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name="fk_points_schemes_league_id_leagues",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["season_id"],
            ["seasons.id"],
            name="fk_points_schemes_season_id_seasons",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_points_schemes"),
    )

    op.create_table(
        "points_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scheme_id"],
            ["points_schemes.id"],
            name="fk_points_rules_scheme_id_points_schemes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_points_rules"),
    )

    op.create_table(
        "results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finish_position", sa.Integer(), nullable=False),
        sa.Column("started_position", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), server_default=sa.text("'FINISHED'"), nullable=False),
        sa.Column("bonus_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("penalty_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_points", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["driver_id"], ["drivers.id"], name="fk_results_driver_id_drivers", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.id"], name="fk_results_event_id_events", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_results"),
        sa.UniqueConstraint("event_id", "driver_id", name="uq_results_event_driver"),
    )
    op.create_index("ix_results_event_finish", "results", ["event_id", "finish_position"])

    op.create_table(
        "integrations_discord",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("league_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guild_id", sa.String(), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=True),
        sa.Column("installed_by_user", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["installed_by_user"],
            ["users.id"],
            name="fk_integrations_discord_installed_by_user_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name="fk_integrations_discord_league_id_leagues",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_integrations_discord"),
        sa.UniqueConstraint("league_id", "guild_id", name="uq_integrations_discord_guild"),
    )

    op.create_table(
        "billing_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("plan", sa.String(), server_default=sa.text("'FREE'"), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_billing_accounts_owner_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_billing_accounts"),
        sa.UniqueConstraint("stripe_customer_id", name="uq_billing_accounts_stripe_customer_id"),
    )

    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("billing_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("plan", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["billing_account_id"],
            ["billing_accounts.id"],
            name="fk_subscriptions_billing_account_id_billing_accounts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
        sa.UniqueConstraint(
            "stripe_subscription_id", name="uq_subscriptions_stripe_subscription_id"
        ),
    )

    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("league_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_audit_logs_actor_id_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name="fk_audit_logs_league_id_leagues",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("subscriptions")
    op.drop_table("billing_accounts")
    op.drop_table("integrations_discord")
    op.drop_index("ix_results_event_finish", table_name="results")
    op.drop_table("results")
    op.drop_table("points_rules")
    op.drop_table("points_schemes")
    op.drop_index("ix_events_status_scheduled", table_name="events")
    op.drop_index("ix_events_league_start_time", table_name="events")
    op.drop_table("events")
    op.drop_table("seasons")
    op.drop_table("drivers")
    op.drop_table("teams")
    op.drop_table("memberships")
    op.drop_table("leagues")
    op.drop_table("users")
    league_role = sa.Enum(name="league_role")
    league_role.drop(op.get_bind(), checkfirst=True)
