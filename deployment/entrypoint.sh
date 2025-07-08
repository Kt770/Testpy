#!/bin/bash
set -e

# Function to wait for database
wait_for_db() {
    echo "Waiting for database connection..."
    
    # Extract database info from DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | cut -d'@' -f2 | cut -d':' -f1)
    DB_PORT=$(echo $DATABASE_URL | cut -d'@' -f2 | cut -d':' -f2 | cut -d'/' -f1)
    
    # Default values if extraction fails
    DB_HOST=${DB_HOST:-postgres}
    DB_PORT=${DB_PORT:-5432}
    
    # Wait for database to be ready
    while ! curl -s "http://$DB_HOST:$DB_PORT" > /dev/null 2>&1; do
        echo "Database not ready, waiting..."
        sleep 2
    done
    
    echo "Database connection established!"
}

# Function to run database migrations
run_migrations() {
    echo "Running database migrations..."
    python -c "
from app.core.database import engine
from app.models.models import Base
Base.metadata.create_all(bind=engine)
print('Database tables created successfully!')
"
}

# Function to create initial admin user
create_admin_user() {
    echo "Creating initial admin user if not exists..."
    python -c "
from app.core.database import SessionLocal
from app.models.models import User
from app.core.auth import get_password_hash

db = SessionLocal()
try:
    user_count = db.query(User).count()
    if user_count == 0:
        admin_user = User(
            email='admin@contractmanager.com',
            username='admin',
            full_name='System Administrator',
            hashed_password=get_password_hash('admin123'),
            role='admin',
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print('Admin user created: admin / admin123')
    else:
        print('Users already exist, skipping admin creation')
except Exception as e:
    print(f'Error creating admin user: {e}')
finally:
    db.close()
"
}

# Function to validate environment
validate_environment() {
    echo "Validating environment configuration..."
    
    # Check required environment variables
    if [ -z "$DATABASE_URL" ]; then
        echo "WARNING: DATABASE_URL not set, using default SQLite"
    fi
    
    if [ -z "$SECRET_KEY" ]; then
        echo "WARNING: SECRET_KEY not set, using default (not secure for production)"
    fi
    
    if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
        echo "WARNING: No AI API keys configured. AI features will use fallbacks."
    fi
    
    if [ -z "$DOCUSIGN_INTEGRATION_KEY" ]; then
        echo "WARNING: DocuSign not configured. Will use mock signatures."
    fi
    
    echo "Environment validation complete."
}

# Function to set up logging
setup_logging() {
    echo "Setting up logging..."
    mkdir -p /app/logs
    touch /app/logs/app.log
    echo "Logging configured."
}

# Main startup sequence
main() {
    echo "=== Contract Management System Startup ==="
    echo "Environment: ${DEBUG:-production}"
    echo "Timestamp: $(date)"
    
    # Setup
    validate_environment
    setup_logging
    
    # Database setup (only if using PostgreSQL)
    if [[ $DATABASE_URL == *"postgresql"* ]]; then
        wait_for_db
        run_migrations
        create_admin_user
    else
        echo "Using SQLite, skipping database wait..."
        run_migrations
        create_admin_user
    fi
    
    echo "=== Startup Complete ==="
    echo "Starting application with command: $@"
    
    # Execute the main command
    exec "$@"
}

# Run main function
main "$@"