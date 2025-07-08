from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, default="user")  # admin, manager, user
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    organization = Column(String)
    department = Column(String)
    phone = Column(String)
    avatar = Column(String)
    preferences = Column(Text)  # JSON string for user preferences
    last_login = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"