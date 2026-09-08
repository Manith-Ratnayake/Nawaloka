from decimal import Decimal
from datetime import time

from sqlalchemy import ForeignKey, Numeric, String, Text, Time
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    doctors: Mapped[list["Doctor"]] = relationship(back_populates="specialty")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id"), nullable=False)
    qualifications: Mapped[str | None] = mapped_column(String(255))
    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    specialty: Mapped["Specialty"] = relationship(back_populates="doctors")
    channeling_sessions: Mapped[list["ChannelingSession"]] = relationship(back_populates="doctor")


class ChannelingSession(Base):
    __tablename__ = "channeling_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    room_number: Mapped[str] = mapped_column(String(50), nullable=False)
    max_patients: Mapped[int] = mapped_column(nullable=False)
    doctor: Mapped["Doctor"] = relationship(back_populates="channeling_sessions")


class LabTest(Base):
    __tablename__ = "lab_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    test_name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fasting_required_hours: Mapped[int] = mapped_column(default=0)
    preparation_instructions: Mapped[str | None] = mapped_column(Text)
    report_delivery_hours: Mapped[int] = mapped_column(nullable=False)


class HealthPackage(Base):
    __tablename__ = "health_packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    target_audience: Mapped[str | None] = mapped_column(String(100))
    included_tests_and_services: Mapped[str] = mapped_column(Text, nullable=False)


def create_tables(engine):
    Base.metadata.create_all(engine)
