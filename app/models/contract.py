from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class ContractStatus(enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    UNDER_NEGOTIATION = "under_negotiation"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    ARCHIVED = "archived"

class ContractType(enum.Enum):
    SERVICE_AGREEMENT = "service_agreement"
    VENDOR_CONTRACT = "vendor_contract"
    NDA = "nda"
    EMPLOYMENT = "employment"
    LICENSING = "licensing"
    PARTNERSHIP = "partnership"
    CONSULTING = "consulting"
    CUSTOM = "custom"

class Contract(Base):
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    contract_number = Column(String, unique=True, index=True)
    contract_type = Column(Enum(ContractType), nullable=False)
    status = Column(Enum(ContractStatus), default=ContractStatus.DRAFT)
    
    # Parties
    party_a_name = Column(String, nullable=False)  # Our organization
    party_b_name = Column(String, nullable=False)  # Counterparty
    party_a_email = Column(String)
    party_b_email = Column(String)
    
    # Financial
    contract_value = Column(Float)
    currency = Column(String, default="SAR")
    payment_terms = Column(Text)
    
    # Dates
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    signature_date = Column(DateTime)
    
    # Content
    description = Column(Text)
    terms_and_conditions = Column(Text)
    special_clauses = Column(Text)
    ai_generated_content = Column(Text)  # AI-generated parts
    
    # Files
    original_file_path = Column(String)
    signed_file_path = Column(String)
    
    # AI Analysis
    ai_risk_score = Column(Float)  # 0-1 risk score
    ai_summary = Column(Text)
    ai_key_terms = Column(Text)  # JSON string
    
    # Workflow
    created_by_id = Column(Integer, ForeignKey("users.id"))
    assigned_to_id = Column(Integer, ForeignKey("users.id"))
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    
    # Metadata
    tags = Column(Text)  # JSON array as string
    priority = Column(String, default="medium")  # low, medium, high, urgent
    is_template = Column(Boolean, default=False)
    template_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    vendor = relationship("Vendor", back_populates="contracts")
    signatures = relationship("Signature", back_populates="contract")
    proposals = relationship("Proposal", back_populates="contract")