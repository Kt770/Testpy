from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class ProposalStatus(enum.Enum):
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    AI_ANALYZING = "ai_analyzing"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    ARCHIVED = "archived"

class ProposalType(enum.Enum):
    RFP_RESPONSE = "rfp_response"
    UNSOLICITED = "unsolicited"
    QUOTE = "quote"
    BID = "bid"
    TENDER = "tender"

class Proposal(Base):
    __tablename__ = "proposals"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    proposal_number = Column(String, unique=True, index=True)
    proposal_type = Column(Enum(ProposalType), nullable=False)
    status = Column(Enum(ProposalStatus), default=ProposalStatus.RECEIVED)
    
    # Basic Information
    description = Column(Text)
    scope_of_work = Column(Text)
    deliverables = Column(Text)
    
    # Financial
    proposed_amount = Column(Float, nullable=False)
    currency = Column(String, default="SAR")
    payment_schedule = Column(Text)
    cost_breakdown = Column(JSON)  # Detailed cost structure
    
    # Timeline
    proposed_start_date = Column(DateTime)
    proposed_end_date = Column(DateTime)
    duration_months = Column(Integer)
    key_milestones = Column(JSON)
    
    # Vendor Information
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    
    # Documents
    original_file_path = Column(String)
    supporting_documents = Column(JSON)  # List of file paths
    
    # AI Analysis Results
    ai_analysis_completed = Column(Boolean, default=False)
    ai_overall_score = Column(Float)  # 0-1 overall AI assessment
    ai_technical_score = Column(Float)
    ai_financial_score = Column(Float)
    ai_risk_score = Column(Float)
    ai_compliance_score = Column(Float)
    
    # AI Extracted Information
    ai_key_points = Column(JSON)  # Key proposal highlights
    ai_risks = Column(JSON)  # Identified risks
    ai_advantages = Column(JSON)  # Competitive advantages
    ai_missing_items = Column(JSON)  # Missing requirements
    ai_summary = Column(Text)
    ai_recommendation = Column(Text)
    
    # Evaluation
    technical_evaluation = Column(Text)
    financial_evaluation = Column(Text)
    risk_assessment = Column(Text)
    compliance_check = Column(Text)
    evaluator_notes = Column(Text)
    
    # Decision Making
    decision_rationale = Column(Text)
    rejection_reason = Column(Text)
    feedback_to_vendor = Column(Text)
    
    # Workflow
    received_by_id = Column(Integer, ForeignKey("users.id"))
    assigned_to_id = Column(Integer, ForeignKey("users.id"))
    evaluated_by_id = Column(Integer, ForeignKey("users.id"))
    approved_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Related Contract
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    
    # Metadata
    tags = Column(JSON)
    priority = Column(String, default="medium")
    confidentiality_level = Column(String, default="internal")
    
    # Timestamps
    received_date = Column(DateTime, default=func.now())
    due_date = Column(DateTime)
    evaluation_completed_date = Column(DateTime)
    decision_date = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    vendor = relationship("Vendor", back_populates="proposals")
    contract = relationship("Contract", back_populates="proposals")
    received_by = relationship("User", foreign_keys=[received_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    evaluated_by = relationship("User", foreign_keys=[evaluated_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])