from flask import Flask, request, render_template, redirect
import psycopg2
from datetime import date, timedelta

app = Flask(__name__)

def get_connection():
    return psycopg2.connect(
        host="tramway.proxy.rlwy.net",
        port=25778,
        dbname="railway",
        user="postgres",
        password="DRVLcMSIrvlqpZCIsHFeUvQADtTHKkdg"
    )

@app.route('/')
def index():
    auto_update_rental_status()
    keyword = request.args.get('keyword', '')
    max_price = request.args.get('max_price', None)

    conn = get_connection()
    cur = conn.cursor()

    sql = "SELECT id, address, owner, price, is_rented FROM houses WHERE TRUE"
    params = []

    if keyword:
        sql += " AND address ILIKE %s"
        params.append(f'%{keyword}%')
    if max_price:
        sql += " AND price <= %s"
        params.append(max_price)

    sql += " ORDER BY id"
    cur.execute(sql, params)
    houses = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('index.html', houses=houses)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        address = request.form['address']
        owner = request.form['owner']
        price = request.form['price']
        is_rented = False

        try:
            price = int(price)
        except ValueError:
            return "Giá phải là số nguyên", 400

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO houses (address, owner, price, is_rented) VALUES (%s, %s, %s, %s)",
            (address, owner, price, is_rented)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/')

    return render_template('add.html')

@app.route('/toggle/<int:house_id>')
def toggle(house_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT is_rented FROM houses WHERE id = %s", (house_id,))
    row = cur.fetchone()
    if row is None:
        cur.close()
        conn.close()
        return "Không tìm thấy nhà", 404

    current_status = row[0]
    new_status = not current_status

    cur.execute("UPDATE houses SET is_rented = %s WHERE id = %s", (new_status, house_id))
    conn.commit()

    cur.close()
    conn.close()
    return redirect('/')

@app.route('/delete/<int:house_id>')
def delete(house_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM houses WHERE id = %s", (house_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')
@app.route('/search')
def search():
    # code xử lý tìm kiếm, hoặc có thể redirect về index vì bạn đã có tìm kiếm ở index rồi
    return redirect('/')

@app.route('/rent/<int:house_id>', methods=['GET', 'POST'])
def rent(house_id):
    if request.method == 'POST':
        full_name = request.form['name']
        id_card = request.form['cccd']
        age = int(request.form['age'])
        gender = request.form['gender']
        people_count = int(request.form['number_of_people'])
        rent_from = date.today()
        rent_to = request.form.get('end_date')  # sửa tên field cho khớp

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO renters (house_id, name, cccd, age, gender, number_of_people, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (house_id, full_name, id_card, age, gender, people_count, rent_from, rent_to))

        cur.execute("UPDATE houses SET is_rented = TRUE WHERE id = %s", (house_id,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/')

    return render_template('rent.html', house_id=house_id)

@app.route('/edit/<int:house_id>', methods=['GET', 'POST'])
def edit(house_id):
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        address = request.form['address']
        owner = request.form['owner']
        price = request.form['price']
        is_rented = request.form.get('is_rented') == 'on'  # checkbox

        try:
            price = int(price)
        except ValueError:
            return "Giá phải là số nguyên", 400

        cur.execute("""
            UPDATE houses 
            SET address = %s, owner = %s, price = %s, is_rented = %s 
            WHERE id = %s
        """, (address, owner, price, is_rented, house_id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/')

    # GET: lấy dữ liệu nhà hiện tại
    cur.execute("SELECT id, address, owner, price, is_rented FROM houses WHERE id = %s", (house_id,))
    house = cur.fetchone()
    cur.close()
    conn.close()

    if house is None:
        return "Không tìm thấy nhà", 404

    return render_template('edit.html', house=house)
def auto_update_rental_status():
    conn = get_connection()
    cur = conn.cursor()
    # Set is_rented = TRUE cho nhà đang có hợp đồng thuê hiệu lực (ngày hiện tại nằm trong khoảng thuê)
    cur.execute("""
        UPDATE houses
        SET is_rented = TRUE
        WHERE id IN (
            SELECT house_id FROM renters 
            WHERE CURRENT_DATE BETWEEN start_date AND end_date
        )
    """)
    # Set is_rented = FALSE cho nhà không có hợp đồng thuê hiệu lực
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

@app.route('/delete_renter/<int:renter_id>')
def delete_renter(renter_id):
    conn = get_connection()
    cur = conn.cursor()
    
    # Xóa người thuê
    cur.execute("DELETE FROM renters WHERE id = %s", (renter_id,))
    conn.commit()
    
    cur.close()
    conn.close()
    
    return redirect('/renters')

@app.route('/renters')
def renters_list():
    conn = get_connection()
    cur = conn.cursor()

    # Query lấy thông tin người thuê kèm thông tin nhà
    cur.execute("""
        SELECT r.id, r.name, r.cccd, r.age, r.gender, r.number_of_people, r.start_date, r.end_date,
               h.address, h.id as house_id
        FROM renters r
        JOIN houses h ON r.house_id = h.id
        ORDER BY r.start_date DESC
    """)
    renters = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('renters.html', renters=renters)

if __name__ == '__main__':
    app.run(debug=True)
