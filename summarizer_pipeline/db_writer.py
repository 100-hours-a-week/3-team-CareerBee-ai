import pymysql
import os
from dotenv import load_dotenv

# .env 파일 로딩
load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

def update_issue_for_company(corp_name, summary_text):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE 회사
                SET 최근이슈 = %s
                WHERE 회사명 = %s
            """
            cursor.execute(sql, (summary_text, corp_name))
        conn.commit()
    finally:
        conn.close()
