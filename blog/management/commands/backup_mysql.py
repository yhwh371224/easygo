import os
import sqlite3
import mysql.connector
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Transfer data from SQLite3 to MySQL database'

    def handle(self, *args, **kwargs):
        # SQLite3 연결
        sqlite_path = '/home/ubuntu/github/easygo/db.sqlite3'
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()

        # MySQL 연결
        mysql_config = settings.MYSQL_CONFIG
        try:
            mysql_conn = mysql.connector.connect(**mysql_config)
            mysql_cursor = mysql_conn.cursor()
        except mysql.connector.Error as err:
            self.stdout.write(self.style.ERROR(f'MySQL connection error: {err}'))
            return

        # 테이블 순서 (의존성 고려)
        table_order = [
            'django_content_type',
            'auth_user',
            'auth_group',
            'auth_permission',
            'django_admin_log',
            'django_session',
            'django_site',
            'socialaccount_socialapp',
            'socialaccount_socialtoken',
            'socialaccount_socialaccount',
            'paypal_ipn',
            'admin_honeypot_loginattempt',
            'otp_hotp_hotpdevice',
            'otp_static_statictoken',
            'otp_static_staticdevice',
            'account_emailaddress',
            'axes_accessattempt',
            'axes_accesslog',
            'axes_accessfailurelog',
            'easygo_review_post',
            'easygo_review_comment',
            'blog_driver',
            'blog_paypalpayment',
            'blog_stripepayment',
            'blog_inquiry',
            'blog_post'
        ]

        # SQLite 테이블 목록 확인
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        sqlite_tables = set(t[0] for t in sqlite_cursor.fetchall())

        self.stdout.write(self.style.NOTICE("\n=== [SQLite 테이블 존재 여부] ==="))
        for table in table_order:
            if table in sqlite_tables:
                self.stdout.write(self.style.SUCCESS(f'✔ {table} - 존재함'))
            else:
                self.stdout.write(self.style.WARNING(f'✖ {table} - 없음'))

        # MySQL 테이블 목록 확인
        mysql_cursor.execute("SHOW TABLES")
        mysql_tables = set(t[0] for t in mysql_cursor.fetchall())

        self.stdout.write(self.style.NOTICE("\n=== [MySQL 테이블 존재 여부] ==="))
        for table in table_order:
            if table in mysql_tables:
                self.stdout.write(self.style.SUCCESS(f'✔ {table} - 존재함'))
            else:
                self.stdout.write(self.style.WARNING(f'✖ {table} - 없음'))

        # foreign key 비활성화
        mysql_cursor.execute("SET foreign_key_checks = 0")

        batch_size = 1000  # 대용량 안전 처리

        for table_name in table_order:
            if table_name not in sqlite_tables or table_name not in mysql_tables:
                continue

            self.stdout.write(self.style.SUCCESS(f'\n=== Transferring: {table_name} ==='))

            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()

            if not rows:
                continue

            sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in sqlite_cursor.fetchall()]
            columns_str = ', '.join([f"`{col}`" for col in columns])
            placeholders = ', '.join(['%s'] * len(columns))
            update_query = ', '.join([f"`{col}`=VALUES(`{col}`)" for col in columns])

            insert_query = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders}) " \
                           f"ON DUPLICATE KEY UPDATE {update_query}"

            try:
                for i in range(0, len(rows), batch_size):
                    mysql_cursor.executemany(insert_query, rows[i:i + batch_size])
            except mysql.connector.Error as err:
                self.stdout.write(self.style.ERROR(f'{table_name} 데이터 삽입 오류: {err}'))
                continue

        mysql_conn.commit()
        mysql_cursor.execute("SET foreign_key_checks = 1")

        sqlite_conn.close()
        mysql_cursor.close()
        mysql_conn.close()

        self.stdout.write(self.style.SUCCESS('\nMySQL 데이터 이전 완료!'))
