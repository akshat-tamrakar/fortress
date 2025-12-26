#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Fortress User Management Service${NC}"
echo -e "${GREEN}========================================${NC}"

# Wait for Redis to be ready
echo -e "${YELLOW}Waiting for Redis...${NC}"
until python -c "import redis; r = redis.Redis.from_url('${REDIS_URL:-redis://redis:6379/1}'); r.ping()" &> /dev/null; do
    echo -e "${YELLOW}Redis is unavailable - sleeping${NC}"
    sleep 2
done
echo -e "${GREEN}Redis is up and running!${NC}"

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python manage.py migrate --noinput
echo -e "${GREEN}Database migrations completed!${NC}"

# Collect static files (only in production)
if [ "$DEBUG" = "False" ] || [ "$DEBUG" = "false" ]; then
    echo -e "${YELLOW}Collecting static files...${NC}"
    python manage.py collectstatic --noinput --clear
    echo -e "${GREEN}Static files collected!${NC}"
fi

# Create cache tables if needed
echo -e "${YELLOW}Setting up cache tables...${NC}"
python manage.py createcachetable 2>/dev/null || true
echo -e "${GREEN}Cache tables ready!${NC}"

# Create superuser if needed (development only)
if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ]; then
    echo -e "${YELLOW}Creating default superuser (if not exists)...${NC}"
    python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@fortress.local', 'admin')
    print('Superuser created: admin/admin')
else:
    print('Superuser already exists')
END
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting application...${NC}"
echo -e "${GREEN}========================================${NC}"

# Execute the command passed to the script
exec "$@"
