# app/models.py
from __future__ import annotations

from datetime import date, time
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    Time,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    location = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    stand_number = Column(String(50), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    event_pin = Column(String(50), nullable=True)  # optionaler PIN

    slots = relationship("Slot", back_populates="event", cascade="all, delete-orphan")
    signups = relationship("Signup", back_populates="event", cascade="all, delete-orphan")


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(200), nullable=False)
    date = Column(Date, nullable=False)
    time_start = Column(Time, nullable=False)
    time_end = Column(Time, nullable=False)

    event = relationship("Event", back_populates="slots")
    signup_links = relationship("SignupSlot", back_populates="slot", cascade="all, delete-orphan")


class Signup(Base):
    __tablename__ = "signups"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    contact = Column(String(200), nullable=True)
    note = Column(Text, nullable=True)

    event = relationship("Event", back_populates="signups")
    slots = relationship("SignupSlot", back_populates="signup", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("event_id", "name", name="uq_signup_event_name"),
    )


class SignupSlot(Base):
    __tablename__ = "signup_slots"

    id = Column(Integer, primary_key=True, index=True)
    signup_id = Column(Integer, ForeignKey("signups.id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(Integer, ForeignKey("slots.id", ondelete="CASCADE"), nullable=False)

    signup = relationship("Signup", back_populates="slots")
    slot = relationship("Slot", back_populates="signup_links")

    __table_args__ = (
        UniqueConstraint("signup_id", "slot_id", name="uq_signup_slot"),
    )
