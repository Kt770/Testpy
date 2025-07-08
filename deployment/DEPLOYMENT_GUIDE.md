# 🚀 Deployment Guide: GenAI Contract Management System

## Overview

This guide provides comprehensive deployment instructions for both **on-premises** and **Saudi cloud-based** environments, ensuring data sovereignty, security, and compliance with local regulations.

## 📋 Pre-Deployment Checklist

### System Requirements
- **CPU**: 4+ cores (8+ recommended for production)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 100GB minimum (SSD recommended)
- **Network**: Stable internet connection for AI services
- **OS**: Ubuntu 20.04+, RHEL 8+, or compatible Linux distribution

### Required Software
- Docker Engine 20.10+
- Docker Compose 2.0+
- SSL certificates (for production)
- Domain name (optional but recommended)

---

## 🏢 On-Premises Deployment

### 1. Quick Start (Development/Testing)

```bash
# Clone the repository
git clone <repository-url>
cd contract-management-system

# Create environment file
cp .env.example .env

# Edit environment variables
nano .env

# Start services
cd deployment
docker-compose up -d

# Check status
docker-compose ps
```

### 2. Production On-Premises Setup

#### Step 1: Environment Configuration

```bash
# Create production environment file
cat > deployment/.env.prod << EOF
# Database Configuration
DB_PASSWORD=your_secure_database_password_here
REDIS_PASSWORD=your_secure_redis_password_here

# Application Security
SECRET_KEY=$(openssl rand -hex 32)
ACCESS_TOKEN_EXPIRE_MINUTES=60

# AI Services (Optional - can use local alternatives)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# DocuSign (Optional - can use local e-signature)
DOCUSIGN_INTEGRATION_KEY=your_docusign_key
DOCUSIGN_USER_ID=your_docusign_user_id
DOCUSIGN_ACCOUNT_ID=your_docusign_account_id

# Monitoring
GRAFANA_PASSWORD=your_grafana_password_here

# Production Settings
DEBUG=False
APP_NAME=Contract Management System - On Premises
EOF
```

#### Step 2: SSL Certificate Setup

```bash
# Create SSL directory
mkdir -p deployment/ssl

# Option 1: Self-signed certificate (for internal use)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deployment/ssl/key.pem \
  -out deployment/ssl/cert.pem \
  -subj "/C=SA/ST=Riyadh/L=Riyadh/O=YourOrg/CN=yourdomain.local"

# Option 2: Let's Encrypt (for public domains)
# Install certbot first, then:
# certbot certonly --standalone -d yourdomain.com
# cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem deployment/ssl/cert.pem
# cp /etc/letsencrypt/live/yourdomain.com/privkey.pem deployment/ssl/key.pem
```

#### Step 3: Production Deployment

```bash
# Deploy with production configuration
docker-compose --env-file .env.prod up -d

# Verify deployment
docker-compose ps
docker-compose logs -f contract_app

# Check health
curl -k https://localhost/health
```

#### Step 4: Backup Configuration

```bash
# Create backup script
cat > deployment/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/contract-management/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U contract_user contract_management > $BACKUP_DIR/database.sql

# Backup uploaded files
docker cp contract_app:/app/uploads $BACKUP_DIR/uploads

# Backup environment
cp .env.prod $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x deployment/backup.sh

# Set up daily backup cron job
echo "0 2 * * * /path/to/deployment/backup.sh" | crontab -
```

---

## ☁️ Saudi Cloud Deployment

### Supported Saudi Cloud Providers

1. **SDAIA Cloud** (Saudi Data and AI Authority)
2. **STC Cloud** (Saudi Telecom Company)
3. **Mobily Cloud**
4. **Zain Cloud**
5. **NEOM Cloud**

### 1. SDAIA Cloud Deployment

#### Prerequisites
- SDAIA Cloud account
- Kubernetes cluster access
- Saudi data residency compliance

#### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: contract-management
  labels:
    compliance: saudi-data-residency
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: contract-app
  namespace: contract-management
spec:
  replicas: 3
  selector:
    matchLabels:
      app: contract-app
  template:
    metadata:
      labels:
        app: contract-app
    spec:
      containers:
      - name: contract-app
        image: your-registry/contract-management:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: database-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: secret-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: contract-service
  namespace: contract-management
spec:
  selector:
    app: contract-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### Deploy to SDAIA Cloud

```bash
# Build and push image to SDAIA registry
docker build -f deployment/Dockerfile -t sdaia-registry.sa/contract-management:latest .
docker push sdaia-registry.sa/contract-management:latest

# Create secrets
kubectl create secret generic db-secrets \
  --from-literal=database-url="postgresql://user:pass@postgres:5432/contract_management" \
  -n contract-management

kubectl create secret generic app-secrets \
  --from-literal=secret-key="$(openssl rand -hex 32)" \
  -n contract-management

# Deploy application
kubectl apply -f k8s-deployment.yaml

# Check status
kubectl get pods -n contract-management
kubectl get services -n contract-management
```

### 2. STC Cloud Deployment

#### Using STC Cloud Services

```bash
# STC Cloud CLI setup
stc-cli configure --region riyadh --profile production

# Create VPC and security groups
stc-cli vpc create --cidr 10.0.0.0/16 --name contract-vpc
stc-cli security-group create --name contract-sg --vpc-id vpc-xxx

# Launch instances
stc-cli instance create \
  --image ubuntu-20.04 \
  --instance-type c5.large \
  --key-name your-key \
  --security-group-id sg-xxx \
  --subnet-id subnet-xxx \
  --user-data deployment/cloud-init.yaml

# Set up load balancer
stc-cli elb create \
  --name contract-lb \
  --subnets subnet-xxx \
  --security-groups sg-xxx
```

### 3. Local AI Alternative (Data Sovereignty)

For complete data sovereignty, deploy local AI models:

#### Option 1: Ollama (Local LLM)

```yaml
# Add to docker-compose.yml
  ollama:
    image: ollama/ollama:latest
    container_name: contract_ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0
    restart: unless-stopped
    networks:
      - contract_network

volumes:
  ollama_data:
    driver: local
```

```bash
# Pull and run local models
docker-compose exec ollama ollama pull llama2:13b
docker-compose exec ollama ollama pull codellama:7b

# Configure application to use local AI
# Add to .env:
LOCAL_AI_ENABLED=true
OLLAMA_BASE_URL=http://ollama:11434
```

#### Option 2: Local Text Processing

```python
# Add to app/services/genai/local_ai_service.py
class LocalAIService:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
    
    async def analyze_proposal_local(self, content: str) -> Dict[str, Any]:
        # Local NLP processing
        doc = self.nlp(content)
        
        # Extract entities, sentiment, keywords
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        
        return {
            "summary": self._generate_summary(doc),
            "entities": entities,
            "sentiment": self._analyze_sentiment(doc),
            "risk_factors": self._identify_risks(doc)
        }
```

---

## 🔒 Security & Compliance

### Data Residency Compliance

#### Saudi Data Governance Framework
- ✅ All data stored within Saudi Arabia
- ✅ Encrypted data at rest and in transit
- ✅ Access logging and audit trails
- ✅ Local backup and disaster recovery

#### Configuration for Saudi Compliance

```bash
# Environment variables for compliance
cat >> .env.prod << EOF
# Data Residency
DATA_REGION=saudi-arabia
ENCRYPTION_AT_REST=true
AUDIT_LOGGING=true
DATA_RETENTION_DAYS=2555  # 7 years as per Saudi regulations

# Privacy Settings
GDPR_COMPLIANCE=false
SAUDI_DPL_COMPLIANCE=true
DATA_CLASSIFICATION=confidential

# Backup and DR
BACKUP_LOCATION=saudi-cloud
DR_REGION=saudi-backup
EOF
```

### Network Security

```bash
# Firewall configuration
ufw allow 22/tcp     # SSH
ufw allow 80/tcp     # HTTP
ufw allow 443/tcp    # HTTPS
ufw deny 8000/tcp    # Direct app access
ufw enable

# VPN-only access (recommended)
# Configure OpenVPN or WireGuard for admin access
```

### Monitoring and Alerting

```yaml
# Add monitoring to docker-compose.yml
  alertmanager:
    image: prom/alertmanager:latest
    container_name: contract_alertmanager
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"
    networks:
      - contract_network

  # Saudi-specific monitoring
  security_monitor:
    image: elastic/filebeat:8.8.0
    container_name: contract_security
    volumes:
      - nginx_logs:/var/log/nginx:ro
      - app_logs:/var/log/app:ro
    environment:
      - OUTPUT_ELASTICSEARCH_HOSTS=["saudi-siem.local:9200"]
    networks:
      - contract_network
```

---

## 🚀 Performance Optimization

### Production Scaling

```yaml
# High-availability deployment
version: '3.8'
services:
  contract_app:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - WORKERS=4
      - MAX_REQUESTS=1000
      - MAX_REQUESTS_JITTER=100

  postgres:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    environment:
      - POSTGRES_SHARED_BUFFERS=1GB
      - POSTGRES_EFFECTIVE_CACHE_SIZE=3GB
      - POSTGRES_MAX_CONNECTIONS=200
```

### Database Optimization

```sql
-- PostgreSQL optimization for Saudi deployment
-- Add to init.sql

-- Performance settings
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Arabic text support
ALTER DATABASE contract_management SET default_text_search_config = 'arabic';

-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_contracts_vendor_status ON contracts(vendor_id, status);
CREATE INDEX CONCURRENTLY idx_proposals_ai_score ON proposals(ai_score DESC) WHERE ai_score IS NOT NULL;
CREATE INDEX CONCURRENTLY idx_vendors_overall_score ON vendors(overall_score DESC) WHERE status = 'active';

SELECT pg_reload_conf();
```

---

## 📊 Monitoring & Maintenance

### Health Checks

```bash
#!/bin/bash
# health-check.sh

echo "=== Contract Management System Health Check ==="
echo "Timestamp: $(date)"

# Check application
echo "Checking application..."
if curl -sf https://localhost/health > /dev/null; then
    echo "✅ Application is healthy"
else
    echo "❌ Application is down"
fi

# Check database
echo "Checking database..."
if docker-compose exec -T postgres pg_isready -U contract_user; then
    echo "✅ Database is healthy"
else
    echo "❌ Database is down"
fi

# Check disk space
echo "Checking disk space..."
df -h | grep -E "(/$|/var)" | awk '{print $5 " " $6}' | while read usage partition; do
    usage_num=${usage%?}
    if [ $usage_num -ge 80 ]; then
        echo "⚠️  High disk usage on $partition: $usage"
    else
        echo "✅ Disk usage on $partition: $usage"
    fi
done

# Check SSL certificate expiry
echo "Checking SSL certificate..."
if openssl x509 -in deployment/ssl/cert.pem -checkend 2592000 -noout; then
    echo "✅ SSL certificate is valid"
else
    echo "⚠️  SSL certificate expires within 30 days"
fi

echo "=== Health Check Complete ==="
```

### Automated Updates

```bash
#!/bin/bash
# update.sh

echo "Updating Contract Management System..."

# Backup before update
./backup.sh

# Pull latest images
docker-compose pull

# Update with zero downtime
docker-compose up -d --no-deps contract_app

# Health check
sleep 30
if curl -sf https://localhost/health > /dev/null; then
    echo "✅ Update successful"
    # Clean up old images
    docker image prune -f
else
    echo "❌ Update failed, rolling back..."
    docker-compose restart contract_app
fi
```

---

## 🆘 Troubleshooting

### Common Issues

1. **Application won't start**
   ```bash
   # Check logs
   docker-compose logs contract_app
   
   # Check environment
   docker-compose exec contract_app env | grep -E "(DATABASE|SECRET|API)"
   ```

2. **Database connection issues**
   ```bash
   # Test database connectivity
   docker-compose exec postgres psql -U contract_user -d contract_management -c "SELECT 1;"
   ```

3. **SSL/TLS issues**
   ```bash
   # Test SSL certificate
   openssl s_client -connect localhost:443 -servername localhost
   ```

4. **Performance issues**
   ```bash
   # Check resource usage
   docker stats
   
   # Check database performance
   docker-compose exec postgres psql -U contract_user -d contract_management \
     -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
   ```

### Support Contacts

- **Technical Support**: support@yourorganization.sa
- **Security Issues**: security@yourorganization.sa
- **Emergency**: +966-xxx-xxx-xxxx

---

## 📋 Compliance Checklist

### Saudi Data Protection Law (DPL) Compliance

- [ ] Data stored within Saudi Arabia
- [ ] Encryption at rest and in transit
- [ ] Access controls and authentication
- [ ] Audit logging enabled
- [ ] Data retention policies configured
- [ ] User consent mechanisms
- [ ] Data breach notification procedures
- [ ] Regular security assessments
- [ ] Staff training on data protection

### Technical Compliance

- [ ] SSL/TLS encryption enabled
- [ ] Regular security updates
- [ ] Backup and disaster recovery tested
- [ ] Monitoring and alerting configured
- [ ] Access logs retained for 7 years
- [ ] Network segmentation implemented
- [ ] Intrusion detection active
- [ ] Vulnerability scanning scheduled

---

This deployment guide ensures your GenAI Contract Management System meets Saudi Arabian data sovereignty requirements while maintaining enterprise-grade security and performance standards.