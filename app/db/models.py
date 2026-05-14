from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))

    role: Mapped[str] = mapped_column(String(20), nullable=False, default="client")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("role IN ('client', 'coach', 'admin')", name="ck_users_role"),
        CheckConstraint("status IN ('pending', 'active', 'blocked')", name="ck_users_status"),
    )


class Coach(Base):
    __tablename__ = "coaches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Prague")

    user = relationship("User")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, nullable=False
    )

    display_name: Mapped[str | None] = mapped_column(String(255))
    goal: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'inactive', 'blocked')", name="ck_clients_status"
        ),
    )


class ClientCoachRelation(Base):
    __tablename__ = "client_coach_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id"), nullable=False)
    coach_id: Mapped[str] = mapped_column(String(36), ForeignKey("coaches.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("client_id", "coach_id", name="uq_client_coach"),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_client_coach_status"),
    )


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    coach_id: Mapped[str] = mapped_column(String(36), ForeignKey("coaches.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'used', 'expired', 'revoked')", name="ck_invite_codes_status"
        ),
        CheckConstraint("max_uses > 0", name="ck_invite_codes_max_uses"),
        CheckConstraint("used_count >= 0", name="ck_invite_codes_used_count"),
    )


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "policy_version", name="uq_user_policy_version"),)


class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    coach_id: Mapped[str] = mapped_column(String(36), ForeignKey("coaches.id"), nullable=False)

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")
    booked_by_client_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("clients.id"))
    booked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("status IN ('available', 'booked', 'cancelled')", name="ck_slots_status"),
        CheckConstraint("ends_at > starts_at", name="ck_slots_time_order"),
        Index("idx_slots_coach_status_start", "coach_id", "status", "starts_at"),
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("availability_slots.id"), unique=True, nullable=False
    )
    coach_id: Mapped[str] = mapped_column(String(36), ForeignKey("coaches.id"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="booked")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reminder_24h_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        CheckConstraint(
            "status IN ('booked', 'cancelled_by_client', \
'cancelled_by_coach', 'completed', 'no_show')",
            name="ck_appointments_status",
        ),
        Index("idx_appointments_coach_client", "coach_id", "client_id"),
    )


class MealCheckin(Base):
    __tablename__ = "meal_checkins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id"), nullable=False)
    coach_id: Mapped[str] = mapped_column(String(36), ForeignKey("coaches.id"), nullable=False)

    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'other')",
            name="ck_checkins_meal_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'completed', 'missed', 'cancelled')",
            name="ck_checkins_status",
        ),
        Index("idx_checkins_client_status_scheduled", "client_id", "status", "scheduled_at"),
    )

class MealCheckinSchedule(Base):
    __tablename__ = "meal_checkin_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    coach_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("coaches.id"),
        nullable=False,
    )

    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)

    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'other')",
            name="ck_checkin_schedules_meal_type",
        ),
        UniqueConstraint(
            "coach_id",
            "meal_type",
            "local_time",
            name="uq_checkin_schedule_coach_meal_time",
        ),
        Index(
            "idx_checkin_schedules_coach_active",
            "coach_id",
            "is_active",
        ),
    )

class MealReport(Base):
    __tablename__ = "meal_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    checkin_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("meal_checkins.id"))
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id"), nullable=False)
    coach_id: Mapped[str] = mapped_column(String(36), ForeignKey("coaches.id"), nullable=False)

    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="submitted")
    client_comment: Mapped[str | None] = mapped_column(Text)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clarification_response: Mapped[str | None] = mapped_column(Text)
    clarification_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'other')",
            name="ck_reports_meal_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'in_review', \
'reviewed', 'needs_clarification', 'archived')",
            name="ck_reports_status",
        ),
        Index("idx_reports_coach_status_submitted", "coach_id", "status", "submitted_at"),
        Index("idx_reports_client_submitted", "client_id", "submitted_at"),
    )


class StoredFile(Base):
    __tablename__ = "stored_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("bucket", "storage_key", name="uq_stored_file_object"),)


class MealReportPhoto(Base):
    __tablename__ = "meal_report_photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meal_reports.id"), nullable=False
    )
    stored_file_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("stored_files.id"))

    telegram_file_id: Mapped[str | None] = mapped_column(Text)
    telegram_file_unique_id: Mapped[str | None] = mapped_column(Text)

    processing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('pending', 'stored', 'failed')",
            name="ck_report_photos_processing",
        ),
        Index("idx_report_photos_report", "report_id"),
    )


class MealReview(Base):
    __tablename__ = "meal_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("meal_reports.id"),
        nullable=False,
    )
    coach_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("coaches.id"),
        nullable=False,
    )

    verdict: Mapped[str] = mapped_column(String(30), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "verdict IN ('ok', 'needs_improvement', 'bad', 'question')",
            name="ck_reviews_verdict",
        ),
        CheckConstraint(
            "rating IS NULL OR (rating BETWEEN 1 AND 5)",
            name="ck_reviews_rating",
        ),
        Index("idx_meal_reviews_report_created", "report_id", "created_at"),
        Index("idx_meal_reviews_coach_created", "coach_id", "created_at"),
    )


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    recipient_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text)

    related_entity_type: Mapped[str | None] = mapped_column(String(100))
    related_entity_id: Mapped[str | None] = mapped_column(String(36))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('sent', 'failed')",
            name="ck_notification_logs_status",
        ),
        Index(
            "idx_notification_logs_recipient_created",
            "recipient_telegram_id",
            "created_at",
        ),
        Index(
            "idx_notification_logs_type_status_created",
            "notification_type",
            "status",
            "created_at",
        ),
        Index(
            "idx_notification_logs_entity",
            "related_entity_type",
            "related_entity_id",
        ),
    )


class DataDeletionRequest(Base):
    __tablename__ = "data_deletion_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    admin_note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processed', 'rejected')",
            name="ck_data_deletion_requests_status",
        ),
        Index("idx_data_deletion_requests_status_requested", "status", "requested_at"),
        Index("idx_data_deletion_requests_user", "user_id"),
    )