# GenAI Contract Management System

A comprehensive AI-powered contract management platform with intelligent contract generation, vendor selection, e-signature workflows, and automated proposal analysis. Built for on-premise deployment or Saudi Cloud infrastructure.

## 🚀 Features

### 🤖 AI-Powered Capabilities
- **Smart Contract Generation**: AI-generated contracts using GPT-4 with Saudi Arabian legal compliance
- **Intelligent Proposal Analysis**: Automated scoring and risk assessment of vendor proposals
- **Vendor Intelligence**: AI-driven vendor evaluation and recommendation system
- **Contract Term Extraction**: Automated extraction and analysis of key contract terms

### 📄 Contract Management
- Complete contract lifecycle management
- Document version control and audit trails
- Automated contract numbering and categorization
- Risk scoring and compliance monitoring
- Template management and reuse

### 🏢 Vendor Management
- Comprehensive vendor database with performance tracking
- AI-powered vendor selection and recommendations
- Compliance and certification management
- Performance rating and historical analysis

### 📋 Proposal Management
- Automated proposal intake and processing
- AI-driven evaluation and scoring
- Comparative analysis and ranking
- Decision workflow and rationale tracking

### ✍️ E-Signature Workflows
- DocuSign integration for digital signatures
- Multi-party signing workflows
- Automated reminders and status tracking
- Digital certificate management

### 🔐 Security & Compliance
- Role-based access control (RBAC)
- JWT authentication and authorization
- Data encryption and secure file storage
- Saudi Arabian regulatory compliance

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│    │  FastAPI Backend│    │   PostgreSQL    │
│                 │◄──►│                 │◄──►│    Database     │
│   Modern UI/UX  │    │  REST API       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OpenAI GPT-4  │    │  Redis Cache/   │    │   DocuSign API  │
│  AI Services    │◄──►│  Task Queue     │    │  E-Signatures   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Technology Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **SQLAlchemy**: SQL toolkit and ORM
- **PostgreSQL**: Primary database
- **Redis**: Caching and task queue
- **Celery**: Background task processing
- **OpenAI API**: AI/ML capabilities
- **DocuSign API**: E-signature functionality

### Frontend
- **React 18**: Modern frontend framework
- **TypeScript**: Type-safe JavaScript
- **Material-UI**: Professional UI components
- **React Query**: Data fetching and caching
- **React Router**: Client-side routing

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Local development
- **Nginx**: Reverse proxy and load balancing
- **Let's Encrypt**: SSL certificates

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key
- DocuSign developer account (optional)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd genai-contract-management
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. **Start the application**
```bash
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- API Health Check: http://localhost:8000/health

### Initial Setup

1. **Create an admin user**
```bash
docker-compose exec api python -c "
from app.core.auth import get_password_hash
from app.models.user import User
from app.core.database import SessionLocal
db = SessionLocal()
user = User(
    email='admin@company.com',
    hashed_password=get_password_hash('admin123'),
    first_name='Admin',
    last_name='User',
    role='admin',
    is_active=True
)
db.add(user)
db.commit()
print('Admin user created')
"
```

2. **Load sample data** (optional)
```bash
docker-compose exec api python scripts/load_sample_data.py
```

## 📊 API Documentation

The API provides comprehensive endpoints for all system functionality:

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User authentication
- `GET /api/v1/auth/me` - Current user info

### Contracts
- `GET /api/v1/contracts` - List contracts
- `POST /api/v1/contracts` - Create contract
- `GET /api/v1/contracts/{id}` - Get contract details
- `PUT /api/v1/contracts/{id}` - Update contract
- `PUT /api/v1/contracts/{id}/status` - Update status

### Vendors
- `GET /api/v1/vendors` - List vendors
- `POST /api/v1/vendors` - Create vendor
- `GET /api/v1/vendors/{id}` - Get vendor details
- `POST /api/v1/vendors/{id}/rating` - Rate vendor

### Proposals
- `GET /api/v1/proposals` - List proposals
- `POST /api/v1/proposals` - Create proposal
- `POST /api/v1/proposals/{id}/evaluate` - Evaluate proposal

### AI Services
- `POST /api/v1/ai/generate-contract` - Generate contract
- `POST /api/v1/ai/analyze-proposal/{id}` - Analyze proposal
- `POST /api/v1/ai/analyze-vendor/{id}` - Analyze vendor

### E-Signatures
- `POST /api/v1/signatures/{contract_id}/initiate` - Start signing
- `GET /api/v1/signatures/{id}/status` - Check status

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://admin:password@localhost/contract_mgmt` |
| `SECRET_KEY` | JWT secret key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `DOCUSIGN_CLIENT_ID` | DocuSign integration ID | - |
| `DOCUSIGN_CLIENT_SECRET` | DocuSign secret | - |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |

### Saudi Cloud Deployment

For Saudi Cloud deployment, configure additional variables:

```bash
SAUDI_CLOUD_REGION=riyadh
SAUDI_CLOUD_ENDPOINT=your-endpoint
ALLOWED_ORIGINS=["https://your-domain.sa"]
```

## 📈 Monitoring and Analytics

The system provides comprehensive analytics:

- Contract lifecycle metrics
- Vendor performance tracking
- Proposal success rates
- AI model performance
- User activity monitoring

## 🔒 Security Features

- **Authentication**: JWT-based with refresh tokens
- **Authorization**: Role-based access control
- **Data Protection**: Encryption at rest and in transit
- **Audit Trails**: Complete activity logging
- **File Security**: Secure upload and storage
- **API Security**: Rate limiting and CORS protection

## 🌐 Deployment Options

### On-Premise Deployment
- Complete Docker-based setup
- Internal network deployment
- Custom SSL certificates
- Backup and monitoring integration

### Saudi Cloud Deployment
- Optimized for Saudi Cloud infrastructure
- Regional data compliance
- Arabic language support
- Local regulatory compliance

## 🧪 Testing

Run the test suite:

```bash
# Unit tests
docker-compose exec api python -m pytest tests/

# Integration tests
docker-compose exec api python -m pytest tests/integration/

# API tests
docker-compose exec api python -m pytest tests/api/
```

## 📚 Documentation

- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [User Guide](docs/user-guide.md) - End-user documentation
- [Admin Guide](docs/admin-guide.md) - System administration
- [Developer Guide](docs/developer-guide.md) - Development setup

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Contact the development team

## 🚀 Roadmap

### Phase 1 (Current)
- ✅ Core contract management
- ✅ AI-powered contract generation
- ✅ Vendor management
- ✅ Proposal analysis
- ✅ E-signature integration

### Phase 2 (Planned)
- 📋 Advanced workflow automation
- 📊 Enhanced analytics and reporting
- 🔄 Integration with ERP systems
- 📱 Mobile application
- 🌍 Multi-language support

### Phase 3 (Future)
- 🤖 Advanced AI capabilities
- 🔗 Blockchain integration
- 📈 Predictive analytics
- 🛡️ Advanced security features
- ☁️ Multi-cloud support

---

**GenAI Contract Management System** - Transforming contract management with artificial intelligence.