import psycopg2

conn = psycopg2.connect(
    host="tramway.proxy.rlwy.net",
    port=25778,
    dbname="railway",
    user="postgres",
    password="DRVLcMSIrvlqpZCIsHFeUvQADtTHKkdg"
)
cur = conn.cursor()

try:
    cur.execute("""
        SELECT * FROM houses WHERE TRUE AND address ILIKE '%Trần Đại Nghĩa%';
    """)  # ✅ KHÔNG truyền thêm tuple ở đây
    renters = cur.fetchall()
    print("Kết quả:", renters)
except Exception as e:
    print("Lỗi khi truy vấn dữ liệu:", e)
finally:
    cur.close()
    conn.close()
