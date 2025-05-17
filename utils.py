# utils.py
import psycopg2

def get_connection():
    return psycopg2.connect(
        host="tramway.proxy.rlwy.net",
        port=25778,
        dbname="railway",
        user="postgres",
        password="DRVLcMSIrvlqpZCIsHFeUvQADtTHKkdg"
    )

def auto_update_rental_status():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE houses
        SET is_rented = TRUE
        WHERE id IN (
            SELECT house_id FROM renters 
            WHERE CURRENT_DATE BETWEEN start_date AND end_date
        )
    """)

    cur.execute("""
        UPDATE houses
        SET is_rented = FALSE
        WHERE id NOT IN (
            SELECT house_id FROM renters 
            WHERE CURRENT_DATE BETWEEN start_date AND end_date
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
