import os
import sqlite3
import mysql.connector
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Transfer data from SQLite3 to MySQL database'

    def handle(self, *args, **kwargs):
        # SQLite3 connection configure
        sqlite_conn = sqlite3.connect('/home/ubuntu/github/easygo/db.sqlite3')
        sqlite_cursor = sqlite_conn.cursor()

        # MySQL connection configure
        mysql_config = {
            'user': 'mysql-easygo',
            'password': 'inri.J1919',
            'host': 'localhost',
            'database': 'easygobank'
        }
        
        try:
            mysql_conn = mysql.connector.connect(**mysql_config)
            mysql_cursor = mysql_conn.cursor()
        except mysql.connector.Error as err:
            self.stdout.write(self.style.ERROR(f'MySQL connection error: {err}'))
            return

        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = sqlite_cursor.fetchall()
        table_names = [t[0] for t in tables]

        # 테이블 순서 설정 (부모 테이블 먼저 삽입)
        table_order = [
            'django_content_type',   # 부모 테이블
            'auth_user',             # 부모 테이블
            'auth_group',            # 부모 테이블
            'auth_permission',       # 자식 테이블
            'django_admin_log',      # 자식 테이블
            'django_session',        # 세션 테이블
            'django_site',           # 사이트 테이블
            'socialaccount_socialapp',
            'socialaccount_socialtoken',
            'socialaccount_socialaccount',
            'paypal_ipn',            
            'admin_honeypot_loginattempt',
            'otp_hotp_hotpdevice',
            'otp_static_statictoken',
            'otp_static_staticdevice',
            'otp_totp_totpdevice',
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

        for table_name in table_order:
            if table_name not in table_names:                
                continue

            self.stdout.write(self.style.SUCCESS(f'Transferring table: {table_name}'))
            
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()

            sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in sqlite_cursor.fetchall()]
            columns_str = ', '.join([f"`{col}`" for col in columns])
            placeholders = ', '.join(['%s'] * len(columns))
            update_query = ', '.join([f"`{col}`=VALUES(`{col}`)" for col in columns])

            insert_query = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders}) " \
                           f"ON DUPLICATE KEY UPDATE "
            final_query = insert_query + update_query
            
            try:
                mysql_cursor.executemany(final_query, rows)
            except mysql.connector.Error as err:
                self.stdout.write(self.style.ERROR(f'{table_name} error during inserting datas into tables: {err}'))
                continue

        mysql_conn.commit()
        sqlite_conn.close()
        mysql_cursor.close()
        mysql_conn.close()

        self.stdout.write(self.style.SUCCESS('MySQL has been updated successfully!'))
