from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class SignatureStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    VIEWED = "viewed"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class SignatureMethod(enum.Enum):
    DOCUSIGN = "docusign"
    ADOBE_SIGN = "adobe_sign"
    MANUAL = "manual"
    DIGITAL_CERT = "digital_cert"

class Signature(Base):
    __tablename__ = "signatures"
    
    id = Column(Integer, primary_key=True, index=True)
    envelope_id = Column(String, unique=True, index=True)  # External service ID
    
    # Contract Reference
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    
    # Signature Details
    status = Column(Enum(SignatureStatus), default=SignatureStatus.PENDING)
    method = Column(Enum(SignatureMethod), default=SignatureMethod.DOCUSIGN)
    
    # Signers Information
    signers = Column(JSON)  # List of signers with their details
    signing_order = Column(JSON)  # Order of signing if sequential
    
    # Document Information
    document_name = Column(String, nullable=False)
    document_path = Column(String)
    signed_document_path = Column(String)
    
    # E-signature Service Details
    provider_envelope_id = Column(String)  # DocuSign/Adobe envelope ID
    provider_status = Column(String)
    provider_response = Column(JSON)  # Full response from provider
    
    # Signing Process
    sent_date = Column(DateTime)
    reminder_count = Column(Integer, default=0)
    last_reminder_date = Column(DateTime)
    expiry_date = Column(DateTime)
    
    # Completion
    completed_date = Column(DateTime)
    all_signed = Column(Boolean, default=False)
    certificate_path = Column(String)  # Signature certificate
    
    # Workflow
    initiated_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Security and Audit
    ip_addresses = Column(JSON)  # IP addresses of signers
    authentication_methods = Column(JSON)  # How signers were authenticated
    audit_trail = Column(JSON)  # Complete audit trail
    
    # Notifications
    email_subject = Column(String)
    email_message = Column(Text)
    notification_settings = Column(JSON)
    
    # Error Handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_error_date = Column(DateTime)
    
    # Metadata
    tags = Column(JSON)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    contract = relationship("Contract", back_populates="signatures")
    initiated_by = relationship("User")