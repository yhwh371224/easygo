#!/bin/bash

# 1. 마이그레이션 파일 생성 (DB 지정 없이)
echo ">>> Making migrations..."
python3 manage.py makemigrations

# 2. 기본 DB (SQLite3) 마이그레이션 적용
echo ">>> Applying migrations to default DB (SQLite3)..."
python3 manage.py migrate

# 3. 백업용 MySQL DB 마이그레이션 적용
echo ">>> Applying migrations to backup MySQL DB..."
python3 manage.py migrate --database=backup

echo ">>> Migration done for all databases."
