import os
import sqlite3
import mysql.connector
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Transfer data from SQLite3 to MySQL database (robust, with diagnostics)'

    def handle(self, *args, **options):
        sqlite_path = '/home/horeb/github/easygo/db.sqlite3'

        # 1) sqlite 파일 존재 확인
        if not os.path.exists(sqlite_path):
            self.stdout.write(self.style.ERROR(f"SQLite DB not found at: {sqlite_path}"))
            return

        try:
            sqlite_conn = sqlite3.connect(sqlite_path)
            sqlite_cursor = sqlite_conn.cursor()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to open SQLite DB: {e}"))
            return

        # 2) MySQL 연결
        mysql_config = getattr(settings, 'MYSQL_CONFIG', None)
        if not mysql_config:
            self.stdout.write(self.style.ERROR("settings.MYSQL_CONFIG is not set."))
            return

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

        # SQLite 테이블 목록
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        sqlite_tables = set(t[0] for t in sqlite_cursor.fetchall())

        self.stdout.write("\n=== [SQLite 테이블 존재 여부] ===")
        for table in table_order:
            if table in sqlite_tables:
                self.stdout.write(self.style.SUCCESS(f'✔ {table} - 존재함'))
            else:
                self.stdout.write(self.style.WARNING(f'✖ {table} - 없음'))

        # MySQL 테이블 목록
        try:
            mysql_cursor.execute("SHOW TABLES")
            mysql_tables = set(t[0] for t in mysql_cursor.fetchall())
        except mysql.connector.Error as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch MySQL tables: {e}"))
            sqlite_conn.close()
            mysql_cursor.close()
            mysql_conn.close()
            return

        self.stdout.write("\n=== [MySQL 테이블 존재 여부] ===")
        for table in table_order:
            if table in mysql_tables:
                self.stdout.write(self.style.SUCCESS(f'✔ {table} - 존재함'))
            else:
                self.stdout.write(self.style.WARNING(f'✖ {table} - 없음'))

        # 외래키 체크 끄기 (안전하게)
        try:
            mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not disable foreign key checks: {e}"))

        batch_size = 500

        for table_name in table_order:
            if table_name not in sqlite_tables:
                self.stdout.write(self.style.WARNING(f"\nSkipping {table_name}: not present in SQLite"))
                continue
            if table_name not in mysql_tables:
                self.stdout.write(self.style.WARNING(f"\nSkipping {table_name}: not present in MySQL"))
                continue

            if hasattr(self.style, 'NOTICE'):
                self.stdout.write(self.style.NOTICE(f'\n=== Transferring: {table_name} ==='))
            else:
                self.stdout.write(f'\n=== Transferring: {table_name} ===')

            # 가져오기
            try:
                sqlite_cursor.execute(f"SELECT * FROM `{table_name}`")
                rows = sqlite_cursor.fetchall()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to read from SQLite table {table_name}: {e}"))
                continue

            if not rows:
                self.stdout.write(self.style.SUCCESS(f"{table_name}: no rows to transfer"))
                continue

            # 컬럼 목록
            try:
                sqlite_cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                columns = [col[1] for col in sqlite_cursor.fetchall()]
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"PRAGMA failed for {table_name}: {e}"))
                continue

            columns_str = ', '.join([f"`{col}`" for col in columns])
            placeholders = ', '.join(['%s'] * len(columns))

            # ON DUPLICATE KEY UPDATE 안전 처리: 키/컬럼이 없는 경우 대비
            update_clause = ', '.join([f"`{col}`=VALUES(`{col}`)" for col in columns])

            insert_query = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"

            # Insert in batches with try/except and per-batch commit
            try:
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    try:
                        mysql_cursor.executemany(insert_query, batch)
                        mysql_conn.commit()
                    except mysql.connector.Error as e:
                        # 상세 오류: 어떤 행에서 오류가 났는지 보려면 한 행씩 시도
                        self.stdout.write(self.style.ERROR(f"{table_name} insert batch error: {e}. Trying row-by-row to isolate..."))
                        for r_index, row in enumerate(batch):
                            try:
                                mysql_cursor.execute(insert_query, row)
                            except mysql.connector.Error as row_err:
                                self.stdout.write(self.style.ERROR(f"Failed on table={table_name} batch_index={i // batch_size} row_in_batch={r_index} error={row_err} row_sample={str(row)[:200]}"))
                                # 필요시 계속하거나 중단: 여기선 계속 진행
                        mysql_conn.commit()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"{table_name} 데이터 삽입 중 예상치 못한 오류: {e}"))
                continue

            self.stdout.write(self.style.SUCCESS(f"{table_name} transferred."))

        # 복구
        try:
            mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            mysql_conn.commit()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not re-enable foreign key checks cleanly: {e}"))

        sqlite_conn.close()
        mysql_cursor.close()
        mysql_conn.close()

        self.stdout.write(self.style.SUCCESS('\nMySQL 데이터 이전 완료!'))
