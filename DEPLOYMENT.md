# GraphRAG Deployment Guide

This guide walks you through deploying the GraphRAG engine using Docker Compose.

## Prerequisites

- Docker Desktop or Docker Engine (20.10+)
- Docker Compose (2.0+)
- At least 4GB RAM available
- Google Drive service account credentials (JSON file)

## Quick Start

### 1. Configure Environment

The `.env.docker` file is already configured with Docker service names. Update the passwords:

```bash
# Edit the production environment file
nano .env.docker
```

**Required changes:**
- `POSTGRES_PASSWORD` - Set a strong password
- `NEO4J_PASSWORD` - Set a strong password
- Update `POSTGRES_URL` to match the new password

### 2. Prepare Credentials

Ensure your Google Drive credentials are in place:

```bash
# Check if credentials exist
ls credentials/

# Should contain: qubo-426217-6ebaa2216a16.json
```

### 3. Deploy

#### Option A: Using the deployment script (Recommended)

```bash
# Make script executable
chmod +x deploy.sh

# Start all services
./deploy.sh start

# View logs
./deploy.sh logs

# Check status
./deploy.sh status

# Stop services
./deploy.sh stop
```

#### Option B: Using Docker Compose directly

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps

# Stop services
docker compose down
```

## Service Access Points

Once deployed, access the services at:

| Service | URL | Purpose |
|---------|-----|---------|
| **GraphRAG API** | http://localhost:8000 | Main application |
| **API Documentation** | http://localhost:8000/docs | Swagger UI |
| **Neo4j Browser** | http://localhost:7474 | Graph visualization |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | Vector DB UI |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                   (graphrag-network)                     │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │PostgreSQL│  │  Neo4j   │  │  Qdrant  │  │  App   │ │
│  │  :5432   │  │:7474/7687│  │:6333/6334│  │ :8000  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│       ↑              ↑             ↑            ↑       │
│       └──────────────┴─────────────┴────────────┘       │
│                    Persistent Volumes                    │
└─────────────────────────────────────────────────────────┘
```

## Database Configuration

### PostgreSQL
- **Port**: 5432
- **User**: graphuser
- **Database**: graphrag
- **Purpose**: Document metadata and deduplication
- **Volume**: `postgres_data`

### Neo4j
- **HTTP Port**: 7474 (Browser)
- **Bolt Port**: 7687 (Application)
- **User**: neo4j
- **Purpose**: Knowledge graph storage
- **Volume**: `neo4j_data`, `neo4j_logs`, `neo4j_plugins`
- **Memory**: 256MB heap, 256MB page cache

### Qdrant
- **REST Port**: 6333
- **gRPC Port**: 6334
- **Purpose**: Vector embeddings (1024-dim)
- **Volume**: `qdrant_data`

## Common Operations

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f app
docker compose logs -f postgres
docker compose logs -f neo4j
docker compose logs -f qdrant
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart app
```

### Rebuild After Code Changes

```bash
# Rebuild and restart app
docker compose build app
docker compose up -d app
```

### Database Access

```bash
# PostgreSQL
docker compose exec postgres psql -U graphuser -d graphrag

# Neo4j (via browser)
# Open http://localhost:7474

# Qdrant (via REST API)
curl http://localhost:6333/collections
```

## Production Deployment

### Security Checklist

- [ ] Change default passwords in `.env.docker`
- [ ] Use strong, unique passwords
- [ ] Enable HTTPS with reverse proxy (nginx/Traefik)
- [ ] Restrict database port access (remove public ports if not needed)
- [ ] Use Docker secrets for sensitive data
- [ ] Enable firewall rules
- [ ] Set up monitoring and alerting
- [ ] Configure automated backups

### Reverse Proxy Setup (nginx example)

```nginx
server {
    listen 80;
    server_name graphrag.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL/TLS with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d graphrag.yourdomain.com
```

## Monitoring

### Health Checks

All services have built-in health checks. View status:

```bash
docker compose ps
```

### Resource Usage

```bash
# View container stats
docker stats
```

### Logs Aggregation

Consider using:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Grafana Loki**
- **CloudWatch** (AWS)
- **Stackdriver** (GCP)

## Backup and Recovery

### PostgreSQL Backup

```bash
# Create backup
docker compose exec postgres pg_dump -U graphuser graphrag > backup_$(date +%Y%m%d).sql

# Restore backup
cat backup.sql | docker compose exec -T postgres psql -U graphuser -d graphrag
```

### Neo4j Backup

```bash
# Create backup
docker compose exec neo4j neo4j-admin dump --database=neo4j --to=/data/backup.dump

# Copy to host
docker cp graphrag-neo4j:/data/backup.dump ./neo4j_backup.dump
```

### Qdrant Backup

```bash
# Snapshot API
curl -X POST http://localhost:6333/collections/documents/snapshots

# Or backup volume
docker compose stop qdrant
docker run --rm -v graphrag_qdrant_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/qdrant_backup.tar.gz /data
docker compose start qdrant
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs for errors
docker compose logs

# Check if ports are in use
lsof -i :8000
lsof -i :5432
lsof -i :7687
lsof -i :6333

# Stop conflicting services
sudo systemctl stop postgresql  # If running locally
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
docker compose exec postgres pg_isready -U graphuser

# Test Neo4j connection
curl http://localhost:7474

# Test Qdrant connection
curl http://localhost:6333/
```

### App Can't Connect to Databases

Ensure all services are on the same network:

```bash
docker compose exec app ping postgres
docker compose exec app ping neo4j
docker compose exec app ping qdrant
```

### Out of Memory

Adjust Neo4j memory settings in `docker-compose.yml`:

```yaml
neo4j:
  environment:
    NEO4J_server_memory_heap_max__size: 1G
    NEO4J_server_memory_pagecache_size: 512m
```

## Scaling

### Horizontal Scaling (App)

```bash
# Run 3 app instances
docker compose up -d --scale app=3
```

Note: You'll need a load balancer in front of the app instances.

### Vertical Scaling

Increase resources in `docker-compose.yml`:

```yaml
app:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
```

## Updates

### Update Application Code

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose build app
docker compose up -d app
```

### Update Database Images

```bash
# Pull new images
docker compose pull

# Restart with new images
docker compose up -d
```

## Support

For issues and questions:
- Check logs: `docker compose logs`
- Review documentation: `README.md`
- Open an issue on the repository

## License

[Add your license here]
