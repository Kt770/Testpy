# 🤖 GenAI Contract Management System

A comprehensive AI-powered contract management system that streamlines the entire contract lifecycle from initiation to signature using cutting-edge Generative AI technologies.

## 🚀 Features

### 📄 Contract Initiation
- **AI-Enhanced Contract Generation**: Automatically generate contracts using GPT-4 with intelligent clause suggestions
- **Template Management**: Create and manage reusable contract templates
- **Smart Recommendations**: AI-powered risk assessment and contract enhancement suggestions
- **Workflow Automation**: Automated approval workflows with customizable steps

### 🏢 Vendor Selection
- **AI-Powered Vendor Ranking**: Intelligent vendor selection based on project requirements
- **Multi-Criteria Scoring**: Comprehensive vendor evaluation using reliability, quality, price, and experience metrics
- **Historical Performance Analysis**: Track vendor performance over time
- **Skill-Based Matching**: Match vendors to projects based on specialties and required skills

### 📊 Proposal Analysis
- **Document Processing**: Support for PDF, DOCX, and TXT proposal documents
- **AI Content Extraction**: Automatically extract key information (pricing, deliverables, timelines)
- **Risk Assessment**: AI-powered risk analysis and compliance checking
- **Proposal Comparison**: Side-by-side comparison of multiple proposals with AI insights

### ✍️ E-Signature Workflow
- **DocuSign Integration**: Seamless electronic signature workflow
- **Automated Status Tracking**: Real-time signature status monitoring
- **Workflow Management**: Multi-step approval and signature processes
- **Notifications & Reminders**: Automated email notifications and reminder system

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.8+)
- **Database**: SQLAlchemy with SQLite/PostgreSQL support
- **AI Integration**: OpenAI GPT-4, Anthropic Claude
- **E-Signature**: DocuSign API
- **Document Processing**: PyPDF2, python-docx
- **Authentication**: JWT with bcrypt password hashing
- **API Documentation**: Swagger/OpenAPI 3.0

## 📁 Project Structure

```
app/
├── core/
│   ├── config.py          # Application configuration
│   ├── database.py        # Database setup and connection
│   └── auth.py            # Authentication utilities
├── models/
│   ├── models.py          # SQLAlchemy database models
│   └── schemas.py         # Pydantic request/response schemas
├── routers/
│   ├── auth.py            # Authentication endpoints
│   ├── contracts.py       # Contract management endpoints
│   ├── vendors.py         # Vendor management endpoints
│   └── proposals.py       # Proposal management endpoints
├── services/
│   ├── genai/
│   │   └── openai_service.py     # OpenAI integration
│   ├── analysis/
│   │   └── proposal_analyzer.py  # Proposal analysis service
│   ├── esign/
│   │   └── docusign_service.py   # DocuSign integration
│   └── vendor/
│       └── vendor_selector.py    # Vendor selection service
└── main.py                # FastAPI application entry point
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager
- (Optional) OpenAI API key for AI features
- (Optional) DocuSign API credentials for e-signature features

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd contract-management-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your API keys and configuration
   ```

4. **Run the application**
   ```bash
   python -m app.main
   ```

5. **Access the application**
   - Web Interface: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Alternative Docs: http://localhost:8000/redoc

### Default Login
- **Username**: `admin`
- **Password**: `admin123`

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./contract_management.db

# OpenAI (for AI features)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic (alternative AI provider)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# DocuSign (for e-signature)
DOCUSIGN_INTEGRATION_KEY=your_docusign_integration_key
DOCUSIGN_USER_ID=your_docusign_user_id
DOCUSIGN_ACCOUNT_ID=your_docusign_account_id
DOCUSIGN_BASE_PATH=https://demo.docusign.net/restapi

# Security
SECRET_KEY=your_super_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
APP_NAME=Contract Management System
DEBUG=True
```

## 📚 API Usage Examples

### Authentication
```bash
# Register a new user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "full_name": "Test User",
    "password": "password123",
    "role": "user"
  }'

# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

### Contract Management
```bash
# Create a contract
curl -X POST "http://localhost:8000/contracts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Software Development Contract",
    "description": "Web application development",
    "contract_type": "service",
    "value": 50000,
    "vendor_id": 1
  }'

# Generate contract with AI
curl -X POST "http://localhost:8000/contracts/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_type": "service",
    "vendor_id": 1,
    "ai_enhance": true
  }'
```

### Vendor Selection
```bash
# AI-powered vendor selection
curl -X POST "http://localhost:8000/vendors/select" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_description": "Need a web development company for e-commerce site",
    "required_skills": ["Python", "React", "PostgreSQL"],
    "budget_range": {"min": 30000, "max": 100000},
    "project_timeline": "3 months"
  }'
```

### Proposal Analysis
```bash
# Upload and analyze proposal
curl -X POST "http://localhost:8000/proposals/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@proposal.pdf" \
  -F "vendor_id=1" \
  -F "title=Website Development Proposal"
```

## 🎯 Key AI Features

### 1. Contract Generation
- Automatically generates contract content based on type and vendor information
- Suggests appropriate clauses and terms
- Provides risk assessment and recommendations
- Enhances existing contracts with AI suggestions

### 2. Proposal Analysis
- Extracts key information from proposal documents
- Performs risk assessment (financial, delivery, technical, compliance)
- Generates summary and recommendations
- Scores proposals for easy comparison

### 3. Vendor Selection
- Evaluates vendors based on multiple criteria
- Considers historical performance and project fit
- Provides AI reasoning for recommendations
- Ranks vendors with confidence scores

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control**: Admin, Manager, and User roles
- **Password Hashing**: bcrypt for secure password storage
- **API Key Management**: Secure handling of external API credentials
- **Audit Logging**: Track all system activities

## 📊 Analytics & Reporting

- **Vendor Performance Metrics**: Track success rates, contract values, completion times
- **Proposal Analytics**: Success rates, average scores, processing times
- **Contract Insights**: Status distribution, workflow efficiency
- **System Dashboards**: Real-time statistics and trends

## 🧪 Testing

```bash
# Run tests (when implemented)
python -m pytest tests/

# Test API endpoints
python -m pytest tests/test_api.py

# Test AI services
python -m pytest tests/test_ai_services.py
```

## 🚀 Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
EXPOSE 8000

CMD ["python", "-m", "app.main"]
```

### Production Considerations
- Use PostgreSQL for production database
- Set up proper environment variable management
- Configure CORS for your frontend domain
- Set up SSL/TLS certificates
- Use a reverse proxy (nginx) for better performance
- Implement proper logging and monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the API documentation at `/docs`
- Review the example usage in this README

## 🔄 Roadmap

### Upcoming Features
- [ ] Advanced contract templates with conditional logic
- [ ] Integration with more e-signature providers
- [ ] Machine learning model for vendor performance prediction
- [ ] Advanced analytics dashboard
- [ ] Mobile application
- [ ] Integration with ERP systems
- [ ] Multi-language support
- [ ] Advanced workflow automation

---

**Built with ❤️ using FastAPI, OpenAI, and modern Python technologies.**