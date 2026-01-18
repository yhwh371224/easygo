import sqlite3
import mysql.connector
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Safely restore only the "paid" column for 2026 blog_post data from MySQL backup into SQLite'

    def handle(self, *args, **options):
        # 1️⃣ MySQL 연결 정보
        mysql_config = {
            'host': 'localhost',
            'user': 'mysql-easygo',
            'password': 'YOUR_MYSQL_PASSWORD',  # 실제 비밀번호 입력
            'database': 'easygobank'
        }

        # 2️⃣ SQLite DB 경로
        sqlite_path = '/home/horeb/github/easygo/db.sqlite3'

        # SQLite 연결
        try:
            sqlite_conn = sqlite3.connect(sqlite_path)
            sqlite_cursor = sqlite_conn.cursor()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to open SQLite DB: {e}"))
            return

        # MySQL 연결
        try:
            mysql_conn = mysql.connector.connect(**mysql_config)
            mysql_cursor = mysql_conn.cursor(dictionary=True)
        except mysql.connector.Error as err:
            self.stdout.write(self.style.ERROR(f'MySQL connection error: {err}'))
            return

        # 3️⃣ 2026년 blog_post 데이터의 id + paid 추출
        try:
            mysql_cursor.execute("""
                SELECT id, paid
                FROM post
                WHERE pickup_date LIKE '2026-%';
            """)
            rows = mysql_cursor.fetchall()
            self.stdout.write(self.style.SUCCESS(f"Fetched {len(rows)} rows from MySQL backup"))
        except mysql.connector.Error as e:
            self.stdout.write(self.style.ERROR(f"MySQL query failed: {e}"))
            return

        if not rows:
            self.stdout.write(self.style.WARNING("No 2026 data found in MySQL backup"))
            return

        # 4️⃣ SQLite DB에 paid만 덮어쓰기
        for row in rows:
            try:
                sqlite_cursor.execute("""
                    UPDATE post
                    SET paid = ?
                    WHERE id = ?
                """, (row['paid'], row['id']))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to update row id={row['id']}: {e}"))
                continue

        sqlite_conn.commit()
        sqlite_cursor.close()
        sqlite_conn.close()
        mysql_cursor.close()
        mysql_conn.close()

        self.stdout.write(self.style.SUCCESS("✅ 2026년 blog_post 'paid' 컬럼 안전하게 복원 완료"))
