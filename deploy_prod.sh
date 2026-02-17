#!/bin/bash

# 🚀 SOS KG Production Deployment Script

set -e

echo "🚀 Starting SOS KG Production Deployment..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Please copy env.prod.example to .env and configure it"
    exit 1
fi

# Останавливаем существующие контейнеры
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

# Удаляем старые volumes (опционально)
read -p "🗑️  Remove old volumes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Removing old volumes..."
    docker volume rm sos_kg_postgres_data_prod sos_kg_redis_data_prod sos_kg_static_volume_prod sos_kg_media_volume_prod 2>/dev/null || true
fi

# Собираем и запускаем контейнеры
echo "🔨 Building and starting containers..."
docker-compose -f docker-compose.prod.yml up -d --build

# Ждем запуска базы данных
echo "⏳ Waiting for database to start..."
sleep 10

# Проверяем статус
echo "📊 Checking container status..."
docker-compose -f docker-compose.prod.yml ps

# Создаем суперпользователя (если нужно)
read -p "👤 Create superuser? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "👤 Creating superuser..."
    docker exec sos_backend_prod python manage.py createsuperuser
fi

# Собираем статические файлы
echo "📦 Collecting static files..."
docker exec sos_backend_prod python manage.py collectstatic --noinput

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Access your application:"
echo "   - Main app: http://localhost"
echo "   - Admin: http://localhost/admin/"
echo "   - API: http://localhost/api/"
echo "   - Health: http://localhost/health/"
echo ""
echo "📊 View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "🛑 Stop: docker-compose -f docker-compose.prod.yml down"

