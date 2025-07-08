import PyPDF2
import docx
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import aiofiles
import re
from app.services.genai.openai_service import OpenAIService
from app.models.models import Proposal, Vendor
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ProposalAnalyzer:
    def __init__(self):
        self.openai_service = OpenAIService()

    async def analyze_proposal_document(self, file_path: str, proposal_id: int, db: Session) -> Dict[str, Any]:
        """
        Extract text from proposal document and perform comprehensive AI analysis.
        """
        try:
            # Get proposal and vendor info from database
            proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
            if not proposal:
                raise ValueError(f"Proposal with ID {proposal_id} not found")

            vendor = db.query(Vendor).filter(Vendor.id == proposal.vendor_id).first()
            if not vendor:
                raise ValueError(f"Vendor for proposal {proposal_id} not found")

            # Extract text from document
            text_content = await self._extract_text_from_file(file_path, proposal.file_type)
            
            if not text_content:
                raise ValueError("No text content could be extracted from the document")

            # Prepare vendor information for analysis
            vendor_info = {
                "name": vendor.name,
                "industry": vendor.industry,
                "years_in_business": vendor.years_in_business,
                "specialties": vendor.specialties or [],
                "overall_score": vendor.overall_score,
                "reliability_score": vendor.reliability_score
            }

            # Perform AI analysis
            ai_analysis = await self.openai_service.analyze_proposal(text_content, vendor_info)

            # Extract structured data from proposal content
            structured_data = await self._extract_structured_data(text_content)

            # Update proposal with analysis results
            proposal.proposal_content = text_content[:5000]  # Store first 5000 chars
            proposal.ai_summary = ai_analysis.get("summary", "")
            proposal.ai_risk_assessment = ai_analysis.get("risk_assessment", {})
            proposal.ai_compliance_check = ai_analysis.get("compliance_check", {})
            proposal.ai_score = ai_analysis.get("score", 0.0)
            proposal.key_benefits = ai_analysis.get("key_benefits", [])
            proposal.concerns = ai_analysis.get("concerns", [])
            proposal.technical_specifications = structured_data.get("technical_specs", {})
            proposal.deliverables = structured_data.get("deliverables", [])
            
            # Extract financial information
            if structured_data.get("proposed_value"):
                proposal.proposed_value = structured_data["proposed_value"]
            
            db.commit()

            return {
                "success": True,
                "analysis": ai_analysis,
                "structured_data": structured_data,
                "text_content_length": len(text_content)
            }

        except Exception as e:
            logger.error(f"Error analyzing proposal document: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
                "analysis": None
            }

    async def _extract_text_from_file(self, file_path: str, file_type: str) -> str:
        """
        Extract text content from various document formats.
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            if file_type.lower() == 'pdf' or file_path.suffix.lower() == '.pdf':
                return await self._extract_text_from_pdf(file_path)
            elif file_type.lower() in ['docx', 'doc'] or file_path.suffix.lower() in ['.docx', '.doc']:
                return await self._extract_text_from_docx(file_path)
            elif file_type.lower() == 'txt' or file_path.suffix.lower() == '.txt':
                return await self._extract_text_from_txt(file_path)
            else:
                # Try to read as text file as fallback
                return await self._extract_text_from_txt(file_path)

        except Exception as e:
            logger.error(f"Error extracting text from file {file_path}: {str(e)}")
            return ""

    async def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""

    async def _extract_text_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            return ""

    async def _extract_text_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT file."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                content = await file.read()
            return content.strip()
        except Exception as e:
            logger.error(f"Error extracting text from TXT: {str(e)}")
            return ""

    async def _extract_structured_data(self, text_content: str) -> Dict[str, Any]:
        """
        Extract structured data from proposal text using regex patterns and AI.
        """
        structured_data = {}

        try:
            # Extract monetary values
            money_patterns = [
                r'\$([0-9,]+(?:\.[0-9]{2})?)',
                r'([0-9,]+(?:\.[0-9]{2})?) (?:USD|dollars|DOL)',
                r'total[:\s]+\$?([0-9,]+(?:\.[0-9]{2})?)',
                r'cost[:\s]+\$?([0-9,]+(?:\.[0-9]{2})?)',
                r'price[:\s]+\$?([0-9,]+(?:\.[0-9]{2})?)'
            ]

            for pattern in money_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                if matches:
                    try:
                        # Take the largest monetary value found
                        amounts = [float(match.replace(',', '')) for match in matches]
                        structured_data["proposed_value"] = max(amounts)
                        break
                    except ValueError:
                        continue

            # Extract deliverables
            deliverable_patterns = [
                r'deliverables?[:\s]+(.*?)(?:\n\n|\n[A-Z]|$)',
                r'we will provide[:\s]+(.*?)(?:\n\n|\n[A-Z]|$)',
                r'scope[:\s]+(.*?)(?:\n\n|\n[A-Z]|$)'
            ]

            for pattern in deliverable_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)
                if matches:
                    deliverables_text = matches[0].strip()
                    # Split by bullets, numbers, or new lines
                    deliverables = re.split(r'[•\-\*\n]\s*', deliverables_text)
                    deliverables = [d.strip() for d in deliverables if d.strip() and len(d.strip()) > 5]
                    structured_data["deliverables"] = deliverables[:10]  # Limit to 10 deliverables
                    break

            # Extract timeline information
            timeline_patterns = [
                r'timeline[:\s]+(.*?)(?:\n\n|\n[A-Z]|$)',
                r'duration[:\s]+(.*?)(?:\n\n|\n[A-Z]|$)',
                r'completion[:\s]+(.*?)(?:\n\n|\n[A-Z]|$)',
                r'([0-9]+)\s*(?:weeks?|months?|days?)',
            ]

            for pattern in timeline_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)
                if matches:
                    structured_data["timeline"] = matches[0].strip()
                    break

            # Extract technical specifications using AI
            tech_specs = await self._extract_technical_specs_with_ai(text_content)
            if tech_specs:
                structured_data["technical_specs"] = tech_specs

        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")

        return structured_data

    async def _extract_technical_specs_with_ai(self, text_content: str) -> Dict[str, Any]:
        """
        Use AI to extract technical specifications from proposal text.
        """
        try:
            prompt = f"""
            Extract technical specifications from the following proposal text:

            {text_content[:3000]}  # Limit to first 3000 characters

            Please provide a JSON response with technical specifications:
            {{
                "technologies": ["list of technologies mentioned"],
                "requirements": ["list of technical requirements"],
                "methodologies": ["list of methodologies/approaches"],
                "tools": ["list of tools/software mentioned"],
                "standards": ["list of standards/compliance requirements"]
            }}

            If no technical specifications are found, return empty arrays.
            """

            response = await self.openai_service.openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a technical analyst expert at extracting technical specifications from business documents."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )

            specs_text = response.choices[0].message.content

            try:
                import json
                specs = json.loads(specs_text)
                return specs
            except json.JSONDecodeError:
                logger.error(f"Failed to parse technical specs JSON: {specs_text}")
                return {}

        except Exception as e:
            logger.error(f"Error extracting technical specs with AI: {str(e)}")
            return {}

    async def batch_analyze_proposals(self, proposal_ids: List[int], db: Session) -> Dict[str, Any]:
        """
        Analyze multiple proposals in batch.
        """
        results = []
        errors = []

        for proposal_id in proposal_ids:
            try:
                proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
                if not proposal or not proposal.file_path:
                    errors.append(f"Proposal {proposal_id}: No file found")
                    continue

                result = await self.analyze_proposal_document(
                    proposal.file_path, proposal_id, db
                )
                
                results.append({
                    "proposal_id": proposal_id,
                    "success": result["success"],
                    "analysis": result.get("analysis", {}),
                    "error": result.get("error")
                })

            except Exception as e:
                errors.append(f"Proposal {proposal_id}: {str(e)}")

        return {
            "total_processed": len(results),
            "successful": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "results": results,
            "errors": errors
        }

    async def compare_proposals(self, proposal_ids: List[int], db: Session) -> Dict[str, Any]:
        """
        Compare multiple proposals using AI analysis.
        """
        try:
            proposals = []
            for proposal_id in proposal_ids:
                proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
                if proposal:
                    vendor = db.query(Vendor).filter(Vendor.id == proposal.vendor_id).first()
                    proposals.append({
                        "id": proposal.id,
                        "title": proposal.title,
                        "vendor_name": vendor.name if vendor else "Unknown",
                        "proposed_value": proposal.proposed_value,
                        "ai_score": proposal.ai_score,
                        "ai_summary": proposal.ai_summary,
                        "key_benefits": proposal.key_benefits or [],
                        "concerns": proposal.concerns or [],
                        "risk_assessment": proposal.ai_risk_assessment or {}
                    })

            if len(proposals) < 2:
                return {"error": "At least 2 proposals required for comparison"}

            # Use AI to generate comparison
            comparison_text = ""
            for i, proposal in enumerate(proposals, 1):
                comparison_text += f"""
                Proposal {i}: {proposal['title']} by {proposal['vendor_name']}
                Value: ${proposal['proposed_value'] or 'Not specified'}
                AI Score: {proposal['ai_score']}/100
                Summary: {proposal['ai_summary']}
                Benefits: {', '.join(proposal['key_benefits'])}
                Concerns: {', '.join(proposal['concerns'])}
                """

            prompt = f"""
            Compare the following proposals and provide a recommendation:

            {comparison_text}

            Please provide a JSON response with:
            {{
                "recommendation": "Which proposal is recommended and why",
                "comparison_matrix": {{
                    "criteria": ["cost", "quality", "risk", "timeline", "experience"],
                    "scores": [
                        {{"proposal_id": 1, "scores": [8, 9, 7, 8, 9]}},
                        {{"proposal_id": 2, "scores": [9, 7, 8, 7, 8]}}
                    ]
                }},
                "pros_cons": [
                    {{"proposal_id": 1, "pros": ["list"], "cons": ["list"]}},
                    {{"proposal_id": 2, "pros": ["list"], "cons": ["list"]}}
                ],
                "final_ranking": [1, 2, 3]
            }}
            """

            response = await self.openai_service.openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert procurement analyst specializing in proposal evaluation and vendor comparison."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )

            comparison_text = response.choices[0].message.content

            try:
                import json
                comparison = json.loads(comparison_text)
                return {
                    "success": True,
                    "proposals": proposals,
                    "comparison": comparison
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Failed to parse AI comparison response",
                    "proposals": proposals
                }

        except Exception as e:
            logger.error(f"Error comparing proposals: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }