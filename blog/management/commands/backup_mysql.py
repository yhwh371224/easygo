import sqlite3
import mysql.connector
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Transfer data from SQLite3 to MySQL database'

    def handle(self, *args, **kwargs):
        # SQLite3 연결 설정
        sqlite_conn = sqlite3.connect('/home/ubuntu/github/easygo/db.sqlite3')
        sqlite_cursor = sqlite_conn.cursor()

        # MySQL 연결 설정
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

        # 테이블 목록 가져오기
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = sqlite_cursor.fetchall()

        for table in tables:
            table_name = table[0]
            self.stdout.write(self.style.SUCCESS(f'Transferring table: {table_name}'))
            
            # SQLite3에서 데이터 가져오기
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()

            # SQLite3의 테이블 스키마 가져오기
            sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in sqlite_cursor.fetchall()]
            columns_str = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(columns))

            # MySQL로 데이터 삽입
            for row in rows:
                insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) " \
                               f"ON DUPLICATE KEY UPDATE "
                update_query = ', '.join([f"{col}=VALUES({col})" for col in columns])
                final_query = insert_query + update_query
                
                try:
                    mysql_cursor.execute(final_query, row)
                except mysql.connector.Error as err:
                    self.stdout.write(self.style.ERROR(f'{table_name} error during inserting datas: {err}'))
                    continue

        # 변경사항 커밋 및 연결 종료
        mysql_conn.commit()
        sqlite_conn.close()
        mysql_cursor.close()
        mysql_conn.close()

        self.stdout.write(self.style.SUCCESS('MySQL has been updated successfully'))



