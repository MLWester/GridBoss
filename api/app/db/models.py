from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class LeagueRole(enum.StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    STEWARD = "STEWARD"
    DRIVER = "DRIVER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    email: Mapped[str | None] = mapped_column(String, unique=True)
    discord_id: Mapped[str | None] = mapped_column(String, unique=True)
    discord_username: Mapped[str | None] = mapped_column(String)
    avatar_url: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_founder: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    leagues_owned: Mapped[list[League]] = relationship(back_populates="owner")
    memberships: Mapped[list[Membership]] = relationship(back_populates="user")
    billing_account: Mapped[BillingAccount | None] = relationship(
        back_populates="owner", uselist=False
    )
    drivers: Mapped[list[Driver]] = relationship(back_populates="user")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="actor")


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    owner_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'FREE'"))
    driver_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("20"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User | None] = relationship(back_populates="leagues_owned")
    memberships: Mapped[list[Membership]] = relationship(back_populates="league")
    teams: Mapped[list[Team]] = relationship(back_populates="league")
    drivers: Mapped[list[Driver]] = relationship(back_populates="league")
    seasons: Mapped[list[Season]] = relationship(back_populates="league")
    events: Mapped[list[Event]] = relationship(back_populates="league")
    points_schemes: Mapped[list[PointsScheme]] = relationship(back_populates="league")
    integrations: Mapped[list[DiscordIntegration]] = relationship(back_populates="league")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="league")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("league_id", "user_id", name="uq_memberships_league_user"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    league_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[LeagueRole] = mapped_column(
        Enum(LeagueRole, name="league_role", validate_strings=True), nullable=False
    )

    league: Mapped[League] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("league_id", "name", name="uq_teams_league_name"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    league_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)

    league: Mapped[League] = relationship(back_populates="teams")
    drivers: Mapped[list[Driver]] = relationship(back_populates="team")


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (
        UniqueConstraint("league_id", "display_name", name="uq_drivers_league_display"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    league_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    discord_id: Mapped[str | None] = mapped_column(String)
    team_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )

    league: Mapped[League] = relationship(back_populates="drivers")
    user: Mapped[User | None] = relationship(back_populates="drivers")
    team: Mapped[Team | None] = relationship(back_populates="drivers")
    results: Mapped[list[Result]] = relationship(back_populates="driver")


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    league_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    league: Mapped[League] = relationship(back_populates="seasons")
    events: Mapped[list[Event]] = relationship(back_populates="season")
    points_schemes: Mapped[list[PointsScheme]] = relationship(back_populates="season")


class EventStatus(enum.StrEnum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    league_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )
    season_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seasons.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    track: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    laps: Mapped[int | None] = mapped_column(Integer)
    distance_km: Mapped[float | None] = mapped_column(Numeric(6, 2))
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'SCHEDULED'"), index=False
    )

    league: Mapped[League] = relationship(back_populates="events")
    season: Mapped[Season | None] = relationship(back_populates="events")
    results: Mapped[list[Result]] = relationship(back_populates="event")


Index("ix_events_league_start_time", Event.league_id, Event.start_time)
Index(
    "ix_events_status_scheduled",
    Event.status,
    postgresql_where=Event.status == EventStatus.SCHEDULED.value,
)


class PointsScheme(Base):
    __tablename__ = "points_schemes"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    league_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )
    season_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seasons.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    league: Mapped[League] = relationship(back_populates="points_schemes")
    season: Mapped[Season | None] = relationship(back_populates="points_schemes")
    rules: Mapped[list[PointsRule]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )


class PointsRule(Base):
    __tablename__ = "points_rules"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    scheme_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("points_schemes.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)

    scheme: Mapped[PointsScheme] = relationship(back_populates="rules")


class ResultStatus(enum.StrEnum):
    FINISHED = "FINISHED"
    DNF = "DNF"
    DNS = "DNS"
    DSQ = "DSQ"


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (UniqueConstraint("event_id", "driver_id", name="uq_results_event_driver"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    driver_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False
    )
    finish_position: Mapped[int] = mapped_column(Integer, nullable=False)
    started_position: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'FINISHED'"), index=False
    )
    bonus_points: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    penalty_points: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    total_points: Mapped[int] = mapped_column(Integer, nullable=False)

    event: Mapped[Event] = relationship(back_populates="results")
    driver: Mapped[Driver] = relationship(back_populates="results")


Index("ix_results_event_finish", Result.event_id, Result.finish_position)


class DiscordIntegration(Base):
    __tablename__ = "integrations_discord"
    __table_args__ = (
        UniqueConstraint("league_id", "guild_id", name="uq_integrations_discord_guild"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    league_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )
    guild_id: Mapped[str] = mapped_column(String, nullable=False)
    channel_id: Mapped[str | None] = mapped_column(String)
    installed_by_user: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    league: Mapped[League] = relationship(back_populates="integrations")
    installer: Mapped[User | None] = relationship("User", foreign_keys=[installed_by_user])


class BillingAccount(Base):
    __tablename__ = "billing_accounts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String, unique=True)
    plan: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'FREE'"))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan_grace_plan: Mapped[str | None] = mapped_column(String)
    plan_grace_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User] = relationship(back_populates="billing_account")
    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="billing_account")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    billing_account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("billing_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(String, unique=True)
    plan: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    billing_account: Mapped[BillingAccount] = relationship(back_populates="subscriptions")


class StripeEvent(Base):
    __tablename__ = "stripe_events"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    event_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    league_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), nullable=True
    )
    entity: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String)
    action: Mapped[str] = mapped_column(String, nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSON)
    after_state: Mapped[dict | None] = mapped_column(JSON)

    actor: Mapped[User | None] = relationship(back_populates="audit_logs")
    league: Mapped[League | None] = relationship(back_populates="audit_logs")
