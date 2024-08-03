import sqlite3
import mysql.connector

sqlite_conn = sqlite3.connect('/home/ubuntu/github/easygo/db.sqlite3')
sqlite_cursor = sqlite_conn.cursor()

mysql_conn = mysql.connector.connect(
    host='localhost',
    user='mysql-easygo',
    password='inri.J1919',
    database='easygobank'
)
mysql_cursor = mysql_conn.cursor()

sqlite_cursor.execute('SELECT * FROM blog_post')
rows = sqlite_cursor.fetchall()

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

for row in rows:
    mysql_cursor.execute(insert_query, row[1:])  

mysql_conn.commit()

sqlite_conn.close()
mysql_conn.close()

print("Data migration from SQLite to MySQL completed successfully.")