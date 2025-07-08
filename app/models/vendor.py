from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Vendor(Base):
    __tablename__ = "vendors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    legal_name = Column(String)
    vendor_code = Column(String, unique=True, index=True)
    
    # Contact Information
    email = Column(String, nullable=False)
    phone = Column(String)
    website = Column(String)
    
    # Address
    address_line1 = Column(String)
    address_line2 = Column(String)
    city = Column(String)
    state_province = Column(String)
    country = Column(String, default="Saudi Arabia")
    postal_code = Column(String)
    
    # Business Information
    industry = Column(String)
    business_type = Column(String)  # corporation, llc, partnership, etc.
    tax_id = Column(String)
    registration_number = Column(String)
    established_date = Column(DateTime)
    
    # Financial
    annual_revenue = Column(Float)
    employee_count = Column(Integer)
    credit_rating = Column(String)
    
    # Vendor Assessment
    overall_rating = Column(Float)  # 1-5 scale
    quality_rating = Column(Float)
    delivery_rating = Column(Float)
    cost_rating = Column(Float)
    communication_rating = Column(Float)
    
    # AI-powered vendor intelligence
    ai_risk_assessment = Column(Text)
    ai_capabilities_analysis = Column(Text)
    ai_market_position = Column(Text)
    ai_recommendation_score = Column(Float)  # 0-1 scale
    
    # Compliance and Certifications
    certifications = Column(JSON)  # List of certifications
    compliance_status = Column(String, default="pending")  # verified, pending, non-compliant
    insurance_verified = Column(Boolean, default=False)
    security_clearance = Column(String)
    
    # Status and Categories
    status = Column(String, default="active")  # active, inactive, blacklisted, pending
    categories = Column(JSON)  # Services/products categories
    preferred_vendor = Column(Boolean, default=False)
    
    # Contract History
    total_contracts = Column(Integer, default=0)
    total_contract_value = Column(Float, default=0.0)
    avg_contract_duration = Column(Integer)  # days
    last_contract_date = Column(DateTime)
    
    # Documents
    documents = Column(JSON)  # List of document references
    
    # Notes and Comments
    notes = Column(Text)
    internal_comments = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_interaction = Column(DateTime)
    
    # Relationships
    contracts = relationship("Contract", back_populates="vendor")
    proposals = relationship("Proposal", back_populates="vendor")