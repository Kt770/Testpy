from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.core.database import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class ContractStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT_FOR_SIGNATURE = "sent_for_signature"
    SIGNED = "signed"
    EXECUTED = "executed"
    TERMINATED = "terminated"


class ProposalStatus(str, Enum):
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    ANALYZED = "analyzed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class VendorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLACKLISTED = "blacklisted"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    contracts = relationship("Contract", back_populates="created_by_user")
    proposals_reviewed = relationship("Proposal", back_populates="reviewed_by_user")


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False)
    phone = Column(String)
    address = Column(Text)
    contact_person = Column(String)
    website = Column(String)
    industry = Column(String)
    company_size = Column(String)
    years_in_business = Column(Integer)
    
    # AI-generated scores
    reliability_score = Column(Float, default=0.0)
    quality_score = Column(Float, default=0.0)
    price_competitiveness = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    
    status = Column(SQLEnum(VendorStatus), default=VendorStatus.ACTIVE)
    certifications = Column(JSON)  # Store certifications as JSON
    specialties = Column(JSON)  # Store specialties as JSON
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    proposals = relationship("Proposal", back_populates="vendor")
    contracts = relationship("Contract", back_populates="vendor")


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text)
    contract_type = Column(String, nullable=False)  # e.g., "service", "product", "employment"
    
    # Financial details
    value = Column(Float)
    currency = Column(String, default="USD")
    
    # Dates
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    signature_deadline = Column(DateTime)
    
    # Status and workflow
    status = Column(SQLEnum(ContractStatus), default=ContractStatus.DRAFT)
    
    # Content
    terms_and_conditions = Column(Text)
    ai_generated_clauses = Column(JSON)  # Store AI-suggested clauses
    custom_fields = Column(JSON)  # Store additional custom fields
    
    # Document management
    document_url = Column(String)  # URL to the contract document
    signature_envelope_id = Column(String)  # DocuSign envelope ID
    
    # Foreign keys
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    created_by = Column(Integer, ForeignKey("users.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="contracts")
    created_by_user = relationship("User", back_populates="contracts")
    workflow_steps = relationship("WorkflowStep", back_populates="contract")


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text)
    
    # Financial details
    proposed_value = Column(Float)
    currency = Column(String, default="USD")
    
    # Timeline
    proposed_start_date = Column(DateTime)
    proposed_end_date = Column(DateTime)
    delivery_timeline = Column(String)
    
    # Content
    proposal_content = Column(Text)
    technical_specifications = Column(JSON)
    deliverables = Column(JSON)
    
    # AI Analysis Results
    ai_summary = Column(Text)
    ai_risk_assessment = Column(JSON)
    ai_compliance_check = Column(JSON)
    ai_score = Column(Float, default=0.0)
    key_benefits = Column(JSON)
    concerns = Column(JSON)
    
    # Status
    status = Column(SQLEnum(ProposalStatus), default=ProposalStatus.RECEIVED)
    
    # File information
    file_path = Column(String)
    file_name = Column(String)
    file_type = Column(String)
    
    # Foreign keys
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="proposals")
    reviewed_by_user = relationship("User", back_populates="proposals_reviewed")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    step_name = Column(String, nullable=False)
    step_order = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # pending, in_progress, completed, rejected
    assigned_to = Column(String)  # email or user ID
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    notes = Column(Text)
    
    # Foreign key
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    contract = relationship("Contract", back_populates="workflow_steps")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)  # contract, proposal, vendor
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # created, updated, deleted, signed, etc.
    description = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))
    ip_address = Column(String)
    user_agent = Column(String)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")


class ContractTemplate(Base):
    __tablename__ = "contract_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    contract_type = Column(String, nullable=False)
    template_content = Column(Text, nullable=False)
    variables = Column(JSON)  # Store template variables
    is_active = Column(Boolean, default=True)
    
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    created_by_user = relationship("User")