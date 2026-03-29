import psycopg2
import sys

try:
    conn = psycopg2.connect(
        dbname='postgres',
        user='postgres',
        password='your_password', # I don't know the postgres password
        host='localhost'
    )
    print("Connection to postgres database successful")
    conn.close()
except Exception as e:
    try:
        print(f"Error (decoded as cp1252): {str(e).encode('latin-1').decode('cp1252')}")
    except:
        print(f"Original Error: {e}")
