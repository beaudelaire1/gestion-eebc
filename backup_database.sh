#!/bin/bash

# ============================================================================
# PostgreSQL Database Backup Script for EEBC Django Project
# ============================================================================
# This script backs up the PostgreSQL database to S3 or local storage.
# Can be scheduled via crontab for automated backups.
#
# Usage: ./backup_database.sh
# ============================================================================

set -e

# Configuration
DB_NAME="${DATABASE_NAME:-eebc_db}"
DB_USER="${DATABASE_USER:-eebc_user}"
DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/eebc_db_backup_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    echo "Created backup directory: $BACKUP_DIR"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} Starting PostgreSQL backup..."

# Check if DATABASE_URL is set (Render.com environment)
if [ -n "$DATABASE_URL" ]; then
    echo "Using DATABASE_URL from environment (Render.com)"
    # Extract connection details from DATABASE_URL
    # Format: postgres://user:password@host:port/dbname
    pg_dump "$DATABASE_URL" > "$BACKUP_FILE"
else
    # Use individual environment variables
    PGPASSWORD="${DATABASE_PASSWORD:-}" pg_dump \
        -h "$DB_HOST" \
        -U "$DB_USER" \
        -p "$DB_PORT" \
        -d "$DB_NAME" \
        > "$BACKUP_FILE"
fi

if [ $? -eq 0 ]; then
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] Backup completed successfully${NC}"
    echo -e "${GREEN}File: $BACKUP_FILE${NC}"
    echo -e "${GREEN}Size: $FILE_SIZE${NC}"
    
    # Compress the backup
    gzip "$BACKUP_FILE"
    COMPRESSED_FILE="$BACKUP_FILE.gz"
    COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
    echo -e "${GREEN}Compressed size: $COMPRESSED_SIZE${NC}"
    
    # Upload to S3 if AWS credentials are available
    if command -v aws &> /dev/null; then
        if [ -n "$AWS_S3_BUCKET" ]; then
            echo -e "${YELLOW}Uploading to S3...${NC}"
            aws s3 cp "$COMPRESSED_FILE" "s3://$AWS_S3_BUCKET/db-backups/$(basename $COMPRESSED_FILE)"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}S3 upload completed${NC}"
            else
                echo -e "${RED}S3 upload failed${NC}"
            fi
        fi
    fi
    
    # Clean up old backups (keep only last N days)
    echo -e "${YELLOW}Removing backups older than $BACKUP_RETENTION_DAYS days...${NC}"
    find "$BACKUP_DIR" -name "eebc_db_backup_*.sql.gz" -mtime +$BACKUP_RETENTION_DAYS -delete
    
else
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] Backup failed${NC}"
    exit 1
fi

echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] Backup process completed${NC}"
