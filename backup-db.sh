#!/bin/bash

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# ======= CONFIG =======
BASE_PATH="/opt/anipush"
ENV_FILE="$BASE_PATH/.env"
DB_PATH="$BASE_PATH/bot.db"
RCLONE_REMOTE="pclouddb:anipush_backups"
BACKUP_NAME="anipush_backup_$TIMESTAMP.db"
# ==============================

BACKUP_DIR="/tmp/sqlite_backups"
ENCRYPTED_NAME="$BACKUP_NAME.gpg"
ENCRYPTED_PATH="$BACKUP_DIR/$ENCRYPTED_NAME"
GPG_PASSPHRASE=$(grep "^GPG_PASSPHRASE" "$ENV_FILE" | sed -E "s/^GPG_PASSPHRASE *= *[\"'](.*)[\"']/\1/")
HEALTHCHECK_ID= https://hc-ping.com/$(grep "^HEALTHCHECK_ID" "$ENV_FILE" | sed -E "s/^HEALTHCHECK_ID *= *[\"'](.*)[\"']/\1/")

mkdir -p "$BACKUP_DIR"

cp "$DB_PATH" "$BACKUP_DIR/$BACKUP_NAME"
if [[ $? -ne 0 ]]; then
    curl -fsS --retry 3 "$HEALTHCHECK_ID/fail" -d "Errore copia DB"
    exit 1
fi

gpg --batch --yes --passphrase "$GPG_PASSPHRASE" \
    --symmetric --cipher-algo AES256 \
    -o "$ENCRYPTED_PATH" "$BACKUP_DIR/$BACKUP_NAME"
if [[ $? -ne 0 ]]; then
    curl -fsS --retry 3 "$HEALTHCHECK_ID/fail" -d "Errore cifratura GPG"
    rm -f "$BACKUP_DIR/$BACKUP_NAME"
    exit 1
fi

rm -f "$BACKUP_DIR/$BACKUP_NAME"

rclone copy "$ENCRYPTED_PATH" "$RCLONE_REMOTE" --quiet
if [[ $? -ne 0 ]]; then
    curl -fsS --retry 3 "$HEALTHCHECK_ID/fail" -d "Errore upload Rclone"
    exit 1
fi

curl -fsS --retry 3 "$HEALTHCHECK_ID" -d "Backup completato con successo"

rm -f "$ENCRYPTED_PATH"
