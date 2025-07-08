from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import logging

from app.core.config import settings
from app.core.database import engine, get_db
from app.models.models import Base
from app.routers import auth, contracts, vendors, proposals

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    # GenAI Contract Management System

    A comprehensive contract management system powered by AI that includes:

    ## Features
    - **Contract Initiation**: Create and manage contracts with AI-enhanced templates
    - **Vendor Selection**: AI-powered vendor selection based on project requirements
    - **Proposal Analysis**: Automated analysis of vendor proposals using AI
    - **E-Signature Workflow**: DocuSign integration for electronic signatures
    - **AI Insights**: Contract risk assessment, compliance checking, and recommendations

    ## API Endpoints
    - **Authentication**: User registration, login, and management
    - **Contracts**: Full contract lifecycle management
    - **Vendors**: Vendor database and AI-powered selection
    - **Proposals**: Proposal upload, analysis, and comparison
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(vendors.router)
app.include_router(proposals.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Welcome page with system information."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Contract Management System</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 30px;
            }
            .feature-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .feature-card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .feature-card h3 {
                color: #333;
                margin-top: 0;
            }
            .api-links {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
            }
            .api-links a {
                display: inline-block;
                margin: 10px;
                padding: 12px 24px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                transition: background 0.3s;
            }
            .api-links a:hover {
                background: #5a6fd8;
            }
            .status {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                font-weight: bold;
            }
            .status.active {
                background: #d4edda;
                color: #155724;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 GenAI Contract Management System</h1>
            <p>AI-Powered Contract Lifecycle Management</p>
            <span class="status active">SYSTEM ACTIVE</span>
        </div>

        <div class="feature-grid">
            <div class="feature-card">
                <h3>📄 Contract Initiation</h3>
                <p>Create and manage contracts with AI-enhanced templates, automated clause generation, and smart recommendations.</p>
                <ul>
                    <li>AI-powered contract generation</li>
                    <li>Template management</li>
                    <li>Workflow automation</li>
                    <li>Risk assessment</li>
                </ul>
            </div>

            <div class="feature-card">
                <h3>🏢 Vendor Selection</h3>
                <p>AI-driven vendor evaluation and selection based on project requirements, historical performance, and scoring algorithms.</p>
                <ul>
                    <li>Automated vendor scoring</li>
                    <li>Skill-based matching</li>
                    <li>Performance analytics</li>
                    <li>Risk evaluation</li>
                </ul>
            </div>

            <div class="feature-card">
                <h3>📊 Proposal Analysis</h3>
                <p>Automated analysis of vendor proposals using AI to extract insights, assess risks, and provide recommendations.</p>
                <ul>
                    <li>Document processing (PDF, DOCX)</li>
                    <li>AI-powered analysis</li>
                    <li>Risk assessment</li>
                    <li>Proposal comparison</li>
                </ul>
            </div>

            <div class="feature-card">
                <h3>✍️ E-Signature Workflow</h3>
                <p>Integrated DocuSign workflow for electronic signatures with automated status tracking and notifications.</p>
                <ul>
                    <li>DocuSign integration</li>
                    <li>Workflow management</li>
                    <li>Status tracking</li>
                    <li>Automated reminders</li>
                </ul>
            </div>
        </div>

        <div class="api-links">
            <h3>🚀 API Documentation</h3>
            <a href="/docs" target="_blank">Interactive API Docs (Swagger)</a>
            <a href="/redoc" target="_blank">API Documentation (ReDoc)</a>
        </div>

        <div class="feature-card">
            <h3>📈 System Status</h3>
            <p><strong>Version:</strong> """ + settings.APP_VERSION + """</p>
            <p><strong>Environment:</strong> """ + ("Development" if settings.DEBUG else "Production") + """</p>
            <p><strong>Features:</strong></p>
            <ul>
                <li>✅ Authentication & Authorization</li>
                <li>✅ Contract Management</li>
                <li>✅ Vendor Management</li>
                <li>✅ Proposal Analysis</li>
                <li>✅ AI Integration (OpenAI)</li>
                <li>✅ E-Signature (DocuSign)</li>
                <li>✅ File Upload & Processing</li>
                <li>✅ Analytics & Reporting</li>
            </ul>
        </div>
    </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": "development" if settings.DEBUG else "production"
    }


@app.get("/system-info")
async def system_info(db: Session = Depends(get_db)):
    """Get system information and statistics."""
    try:
        from app.models.models import User, Vendor, Contract, Proposal
        
        # Get counts from database
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_vendors = db.query(Vendor).count()
        active_vendors = db.query(Vendor).filter(Vendor.status == "active").count()
        total_contracts = db.query(Contract).count()
        total_proposals = db.query(Proposal).count()
        
        return {
            "system": {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "status": "operational"
            },
            "database": {
                "total_users": total_users,
                "active_users": active_users,
                "total_vendors": total_vendors,
                "active_vendors": active_vendors,
                "total_contracts": total_contracts,
                "total_proposals": total_proposals
            },
            "features": {
                "ai_analysis": bool(settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY),
                "docusign_integration": bool(settings.DOCUSIGN_INTEGRATION_KEY),
                "file_upload": True,
                "analytics": True
            }
        }
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving system information")


# Initialize sample data on startup
@app.on_event("startup")
async def startup_event():
    """Initialize sample data and configurations on startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Check if we should create sample data
    db = next(get_db())
    try:
        from app.models.models import User
        from app.core.auth import get_password_hash
        
        # Create default admin user if no users exist
        user_count = db.query(User).count()
        if user_count == 0:
            admin_user = User(
                email="admin@contractmanager.com",
                username="admin",
                full_name="System Administrator",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            logger.info("Created default admin user: admin / admin123")
        
        # Log configuration status
        if settings.OPENAI_API_KEY:
            logger.info("OpenAI API configured ✓")
        else:
            logger.warning("OpenAI API not configured - AI features will use fallbacks")
            
        if settings.DOCUSIGN_INTEGRATION_KEY:
            logger.info("DocuSign API configured ✓")
        else:
            logger.warning("DocuSign API not configured - will use mock signatures")
            
        logger.info("System startup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Contract Management System")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )