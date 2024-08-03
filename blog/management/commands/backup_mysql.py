import sqlite3
import mysql.connector
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Backup data from SQLite to MySQL'

    def handle(self, *args, **options):
        # SQLite 데이터베이스 연결
        sqlite_conn = sqlite3.connect('/home/ubuntu/github/easygo/db.sqlite3')
        sqlite_cursor = sqlite_conn.cursor()

        # MySQL 데이터베이스 연결
        mysql_conn = mysql.connector.connect(
            host='localhost',
            user='mysql-easygo',
            password='inri.J1919',
            database='easygobank'
        )
        mysql_cursor = mysql_conn.cursor()

        # SQLite에서 blog_post 테이블 데이터 읽기
        sqlite_cursor.execute('SELECT * FROM blog_post')
        rows = sqlite_cursor.fetchall()

        # MySQL에 데이터 삽입 쿼리
        insert_query = '''
        INSERT INTO blog_post (
            name,
            company_name,
            contact,
            email,
            email1,
            pickup_date,
            flight_number,
            flight_time,
            pickup_time,
            direction,
            suburb,
            street,
            no_of_passenger,
            no_of_baggage,
            return_direction,
            return_pickup_date,
            return_flight_number,
            return_flight_time,
            return_pickup_time,
            message,
            notice,
            price,
            paid,
            discount,
            toll,
            driver,
            meeting_point,
            is_confirmed,
            cash,
            cruise,
            cancelled,
            private_ride,
            reminder,
            sent_email,
            calendar_event_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )'''

        # 데이터 삽입
        for row in rows:
            # SQLite에서 id 컬럼을 제외한 나머지 데이터를 삽입
            if len(row) == 33:  # 총 컬럼 수 확인
                mysql_cursor.execute(insert_query, row[1:])
            else:
                self.stdout.write(self.style.ERROR(f'Row length mismatch: {len(row)}'))

        mysql_conn.commit()

        # 연결 종료
        sqlite_conn.close()
        mysql_conn.close()

        self.stdout.write(self.style.SUCCESS('Data migration from SQLite to MySQL completed successfully.'))
