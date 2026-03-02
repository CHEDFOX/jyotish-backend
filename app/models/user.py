from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    birth_data = relationship("BirthData", back_populates="user", uselist=False)
    kundli = relationship("Kundli", back_populates="user", uselist=False)
    chat_messages = relationship("ChatMessage", back_populates="user")
    partners = relationship("Partner", back_populates="user")


class BirthData(Base):
    __tablename__ = "birth_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    birth_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    birth_time = Column(String(5), nullable=False)   # HH:MM
    timezone_offset = Column(Float, nullable=False, default=5.5)
    
    birth_place = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    gender = Column(String(10))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="birth_data")


class Kundli(Base):
    __tablename__ = "kundli"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    kundli_data = Column(Text, nullable=False)  # JSON string
    formatted_for_ai = Column(Text)  # Pre-formatted string for AI context
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="kundli")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    
    is_voice = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="chat_messages")


class Partner(Base):
    __tablename__ = "partners"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    
    name = Column(String(100), nullable=False)
    
    birth_date = Column(String(10), nullable=False)
    birth_time = Column(String(5), nullable=False)
    timezone_offset = Column(Float, nullable=False, default=5.5)
    
    birth_place = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    gender = Column(String(10))
    
    kundli_data = Column(Text)  # JSON string
    matching_result = Column(Text)  # JSON string
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="partners")
