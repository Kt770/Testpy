import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.services.genai.openai_service import OpenAIService
from app.models.models import Vendor, Proposal, Contract
from app.models.schemas import VendorSelectionRequest, VendorSelectionResult
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class VendorSelector:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.scaler = StandardScaler()

    async def select_vendors(self, selection_request: VendorSelectionRequest, db: Session) -> Dict[str, Any]:
        """
        Select and rank vendors based on project requirements using AI and scoring algorithms.
        """
        try:
            # Get all active vendors
            vendors = db.query(Vendor).filter(Vendor.status == "active").all()
            
            if not vendors:
                return {
                    "success": False,
                    "error": "No active vendors found",
                    "recommended_vendors": []
                }

            # Convert vendors to dictionary format
            vendor_data = []
            for vendor in vendors:
                vendor_dict = {
                    "id": vendor.id,
                    "name": vendor.name,
                    "email": vendor.email,
                    "industry": vendor.industry,
                    "years_in_business": vendor.years_in_business or 0,
                    "specialties": vendor.specialties or [],
                    "overall_score": vendor.overall_score,
                    "reliability_score": vendor.reliability_score,
                    "quality_score": vendor.quality_score,
                    "price_competitiveness": vendor.price_competitiveness,
                    "certifications": vendor.certifications or [],
                    "company_size": vendor.company_size,
                    "address": vendor.address,
                    "contact_person": vendor.contact_person
                }
                vendor_data.append(vendor_dict)

            # Score vendors using multiple criteria
            scored_vendors = await self._score_vendors(
                vendor_data, 
                selection_request.dict(), 
                db
            )

            # Use AI for intelligent vendor selection
            ai_selection = await self.openai_service.select_vendors(
                selection_request.project_description,
                scored_vendors,
                selection_request.dict()
            )

            # Combine AI insights with algorithmic scoring
            final_recommendations = await self._combine_ai_and_algorithmic_scores(
                scored_vendors, 
                ai_selection,
                selection_request
            )

            return {
                "success": True,
                "selection_criteria": selection_request.dict(),
                "total_vendors_evaluated": len(vendors),
                "ai_selection": ai_selection,
                "recommended_vendors": final_recommendations[:5],  # Top 5 vendors
                "scoring_breakdown": self._get_scoring_breakdown(scored_vendors[:5])
            }

        except Exception as e:
            logger.error(f"Error selecting vendors: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "recommended_vendors": []
            }

    async def _score_vendors(self, vendors: List[Dict[str, Any]], criteria: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """
        Score vendors based on multiple criteria including historical performance.
        """
        scored_vendors = []
        
        for vendor in vendors:
            # Calculate base scores
            base_score = vendor["overall_score"] or 0
            reliability = vendor["reliability_score"] or 0
            quality = vendor["quality_score"] or 0
            price_comp = vendor["price_competitiveness"] or 0

            # Calculate experience score
            experience_score = min(100, (vendor["years_in_business"] / 20) * 100)

            # Calculate specialty match score
            specialty_score = await self._calculate_specialty_match(
                vendor["specialties"], 
                criteria.get("required_skills", [])
            )

            # Calculate historical performance score
            historical_score = await self._calculate_historical_performance(vendor["id"], db)

            # Calculate location score
            location_score = await self._calculate_location_score(
                vendor.get("address", ""), 
                criteria.get("preferred_location", "")
            )

            # Calculate certification score
            certification_score = self._calculate_certification_score(
                vendor.get("certifications", [])
            )

            # Weight different factors
            weights = {
                "base": 0.25,
                "reliability": 0.20,
                "quality": 0.20,
                "price": 0.15,
                "experience": 0.10,
                "specialty": 0.05,
                "historical": 0.03,
                "location": 0.01,
                "certification": 0.01
            }

            # Calculate weighted total score
            total_score = (
                base_score * weights["base"] +
                reliability * weights["reliability"] +
                quality * weights["quality"] +
                price_comp * weights["price"] +
                experience_score * weights["experience"] +
                specialty_score * weights["specialty"] +
                historical_score * weights["historical"] +
                location_score * weights["location"] +
                certification_score * weights["certification"]
            )

            # Add detailed scoring breakdown
            vendor_with_score = vendor.copy()
            vendor_with_score.update({
                "calculated_score": round(total_score, 2),
                "score_breakdown": {
                    "base_score": base_score,
                    "reliability_score": reliability,
                    "quality_score": quality,
                    "price_competitiveness": price_comp,
                    "experience_score": round(experience_score, 2),
                    "specialty_match_score": round(specialty_score, 2),
                    "historical_performance_score": round(historical_score, 2),
                    "location_score": round(location_score, 2),
                    "certification_score": round(certification_score, 2),
                    "total_weighted_score": round(total_score, 2)
                }
            })
            
            scored_vendors.append(vendor_with_score)

        # Sort by calculated score
        scored_vendors.sort(key=lambda x: x["calculated_score"], reverse=True)
        
        return scored_vendors

    async def _calculate_specialty_match(self, vendor_specialties: List[str], required_skills: List[str]) -> float:
        """Calculate how well vendor specialties match required skills."""
        if not vendor_specialties or not required_skills:
            return 50.0  # Neutral score

        # Convert to lowercase for comparison
        vendor_specs = [spec.lower() for spec in vendor_specialties]
        required = [skill.lower() for skill in required_skills]

        # Calculate direct matches
        direct_matches = sum(1 for skill in required if any(skill in spec for spec in vendor_specs))
        
        if not required:
            return 50.0
            
        match_percentage = (direct_matches / len(required)) * 100
        return min(100.0, match_percentage)

    async def _calculate_historical_performance(self, vendor_id: int, db: Session) -> float:
        """Calculate vendor's historical performance based on past contracts and proposals."""
        try:
            # Get completed contracts
            completed_contracts = db.query(Contract).filter(
                Contract.vendor_id == vendor_id,
                Contract.status.in_(["signed", "executed"])
            ).all()

            if not completed_contracts:
                return 50.0  # Neutral score for new vendors

            # Calculate metrics
            total_contracts = len(completed_contracts)
            total_value = sum(contract.value for contract in completed_contracts if contract.value)
            avg_value = total_value / total_contracts if total_contracts > 0 else 0

            # Get proposal acceptance rate
            total_proposals = db.query(Proposal).filter(Proposal.vendor_id == vendor_id).count()
            accepted_proposals = db.query(Proposal).filter(
                Proposal.vendor_id == vendor_id,
                Proposal.status == "accepted"
            ).count()

            acceptance_rate = (accepted_proposals / total_proposals * 100) if total_proposals > 0 else 0

            # Calculate historical score
            # Factors: number of contracts (experience), average contract value, proposal acceptance rate
            experience_factor = min(100, (total_contracts / 10) * 100)  # Max score at 10 contracts
            value_factor = min(100, (avg_value / 50000) * 100)  # Max score at $50k average
            acceptance_factor = acceptance_rate

            historical_score = (experience_factor + value_factor + acceptance_factor) / 3
            
            return historical_score

        except Exception as e:
            logger.error(f"Error calculating historical performance: {str(e)}")
            return 50.0

    async def _calculate_location_score(self, vendor_address: str, preferred_location: str) -> float:
        """Calculate location compatibility score."""
        if not vendor_address or not preferred_location:
            return 50.0  # Neutral score

        vendor_addr = vendor_address.lower()
        preferred = preferred_location.lower()

        # Simple location matching
        if preferred in vendor_addr:
            return 100.0
        elif any(word in vendor_addr for word in preferred.split()):
            return 75.0
        else:
            return 25.0

    def _calculate_certification_score(self, certifications: List[str]) -> float:
        """Calculate certification score based on number and quality of certifications."""
        if not certifications:
            return 0.0

        # Award points for each certification
        base_points = len(certifications) * 10
        
        # Award bonus points for specific high-value certifications
        high_value_certs = ["iso", "soc", "hipaa", "gdpr", "pci", "cmmi"]
        bonus_points = sum(10 for cert in certifications 
                          if any(hv_cert in cert.lower() for hv_cert in high_value_certs))

        total_score = base_points + bonus_points
        return min(100.0, total_score)

    async def _combine_ai_and_algorithmic_scores(self, 
                                               algorithmic_vendors: List[Dict[str, Any]], 
                                               ai_selection: Dict[str, Any],
                                               criteria: VendorSelectionRequest) -> List[Dict[str, Any]]:
        """Combine AI recommendations with algorithmic scoring for final recommendations."""
        try:
            ai_vendors = ai_selection.get("recommended_vendors", [])
            
            # Create a mapping of vendor IDs to AI recommendations
            ai_vendor_map = {vendor.get("vendor_id"): vendor for vendor in ai_vendors}
            
            final_vendors = []
            
            for vendor in algorithmic_vendors:
                vendor_id = vendor["id"]
                final_vendor = vendor.copy()
                
                # Add AI insights if available
                if vendor_id in ai_vendor_map:
                    ai_vendor = ai_vendor_map[vendor_id]
                    final_vendor.update({
                        "ai_rank": ai_vendor.get("rank", 999),
                        "ai_score": ai_vendor.get("score", 0),
                        "ai_strengths": ai_vendor.get("strengths", []),
                        "ai_fit_reasoning": ai_vendor.get("fit_reasoning", ""),
                        "has_ai_recommendation": True
                    })
                    
                    # Combine algorithmic and AI scores
                    combined_score = (
                        final_vendor["calculated_score"] * 0.7 +  # 70% algorithmic
                        ai_vendor.get("score", 0) * 0.3          # 30% AI
                    )
                    final_vendor["final_score"] = round(combined_score, 2)
                else:
                    final_vendor.update({
                        "ai_rank": 999,
                        "ai_score": 0,
                        "ai_strengths": [],
                        "ai_fit_reasoning": "No AI analysis available",
                        "has_ai_recommendation": False,
                        "final_score": final_vendor["calculated_score"]
                    })
                
                final_vendors.append(final_vendor)
            
            # Sort by final score
            final_vendors.sort(key=lambda x: x["final_score"], reverse=True)
            
            return final_vendors
            
        except Exception as e:
            logger.error(f"Error combining AI and algorithmic scores: {str(e)}")
            return algorithmic_vendors

    def _get_scoring_breakdown(self, vendors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get detailed scoring breakdown for analysis."""
        if not vendors:
            return {}
        
        breakdown = {
            "criteria_weights": {
                "base_score": "25%",
                "reliability": "20%", 
                "quality": "20%",
                "price_competitiveness": "15%",
                "experience": "10%",
                "specialty_match": "5%",
                "historical_performance": "3%",
                "location_match": "1%",
                "certifications": "1%"
            },
            "top_vendors_analysis": []
        }
        
        for i, vendor in enumerate(vendors[:3], 1):
            analysis = {
                "rank": i,
                "vendor_name": vendor["name"],
                "final_score": vendor.get("final_score", vendor["calculated_score"]),
                "score_breakdown": vendor.get("score_breakdown", {}),
                "ai_insights": {
                    "ai_score": vendor.get("ai_score", "N/A"),
                    "strengths": vendor.get("ai_strengths", []),
                    "reasoning": vendor.get("ai_fit_reasoning", "N/A")
                }
            }
            breakdown["top_vendors_analysis"].append(analysis)
        
        return breakdown

    async def update_vendor_scores(self, vendor_id: int, db: Session) -> Dict[str, Any]:
        """Update a vendor's scores based on recent performance."""
        try:
            vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
            if not vendor:
                return {"success": False, "error": "Vendor not found"}

            # Recalculate scores based on recent data
            historical_score = await self._calculate_historical_performance(vendor_id, db)
            
            # Get recent proposals for quality assessment
            recent_proposals = db.query(Proposal).filter(
                Proposal.vendor_id == vendor_id,
                Proposal.ai_score.isnot(None)
            ).order_by(Proposal.created_at.desc()).limit(10).all()

            if recent_proposals:
                avg_proposal_score = sum(p.ai_score for p in recent_proposals) / len(recent_proposals)
                vendor.quality_score = round(avg_proposal_score, 2)

            # Update reliability based on contract completion
            completed_contracts = db.query(Contract).filter(
                Contract.vendor_id == vendor_id,
                Contract.status.in_(["signed", "executed"])
            ).count()
            
            total_contracts = db.query(Contract).filter(Contract.vendor_id == vendor_id).count()
            
            if total_contracts > 0:
                completion_rate = (completed_contracts / total_contracts) * 100
                vendor.reliability_score = round(completion_rate, 2)

            # Update overall score as weighted average
            vendor.overall_score = round(
                (vendor.quality_score * 0.4 + 
                 vendor.reliability_score * 0.4 + 
                 historical_score * 0.2), 2
            )

            db.commit()

            return {
                "success": True,
                "vendor_id": vendor_id,
                "updated_scores": {
                    "overall_score": vendor.overall_score,
                    "quality_score": vendor.quality_score,
                    "reliability_score": vendor.reliability_score,
                    "historical_performance": round(historical_score, 2)
                }
            }

        except Exception as e:
            logger.error(f"Error updating vendor scores: {str(e)}")
            db.rollback()
            return {"success": False, "error": str(e)}

    async def batch_update_all_vendor_scores(self, db: Session) -> Dict[str, Any]:
        """Update scores for all vendors - useful for periodic maintenance."""
        try:
            vendors = db.query(Vendor).filter(Vendor.status == "active").all()
            results = []
            
            for vendor in vendors:
                result = await self.update_vendor_scores(vendor.id, db)
                results.append({
                    "vendor_id": vendor.id,
                    "vendor_name": vendor.name,
                    "update_result": result
                })

            successful_updates = len([r for r in results if r["update_result"]["success"]])
            
            return {
                "success": True,
                "total_vendors": len(vendors),
                "successful_updates": successful_updates,
                "failed_updates": len(vendors) - successful_updates,
                "results": results
            }

        except Exception as e:
            logger.error(f"Error in batch vendor score update: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }