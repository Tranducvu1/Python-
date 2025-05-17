import os
from flask import Flask, request, render_template, redirect, url_for
from flask_login import current_user, login_required, logout_user
import psycopg2
import psycopg2.extras
from datetime import date, timedelta
from werkzeug.utils import secure_filename
from flask import send_file
import io
from openpyxl import Workbook
# Import đúng login_manager từ login.py thay vì tạo mới
from login import auth_bp, User, get_connection, bcrypt, login_manager
from utils import auto_update_rental_status, get_connection

app = Flask(__name__)
app.secret_key = 'c7a2d89f4a7fa456781a2b3cde9a473ac812f2e3a3b4f6a2d8b21e4b3f8c1d2e'

# Đăng ký login_manager đã import
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Bcrypt setup
bcrypt.init_app(app)

# Đăng ký blueprint từ login.py
app.register_blueprint(auth_bp)

@app.route('/')
@login_required
def index():
    keyword = request.args.get('keyword', '').strip()
    max_price = request.args.get('max_price', '').strip()

    conn = get_connection()
    cur = conn.cursor()

    sql = "SELECT id, address, owner, price, is_rented, image FROM houses WHERE TRUE"
    params = []
    if keyword:
        sql += " AND address ILIKE %s"
        params.append(f'%{keyword}%')
    if max_price:
        try:
            max_price_int = int(max_price)
            sql += " AND price <= %s"
            params.append(max_price_int)
        except ValueError:
            pass  # Nếu không phải số thì bỏ qua filter

    sql += " ORDER BY id"
    cur.execute(sql, params)
    houses = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('index.html', houses=houses)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if current_user.role != 'admin':
        return "Không có quyền", 403

    if request.method == 'POST':
        address = request.form['address']
        owner = request.form['owner']
        price = request.form['price']
        image_file = request.files['image']
        filename = None

        if image_file:
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO houses (address, owner, price, is_rented, image) VALUES (%s, %s, %s, %s, %s)",
            (address, owner, price, False, filename)
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
@login_required
def rent(house_id):
    if request.method == 'POST':
        full_name = request.form['name']
        id_card = request.form['cccd']
        age = int(request.form['age'])
        gender = request.form['gender']
        people_count = int(request.form['number_of_people'])
        rent_from = date.today()
        rent_to = request.form.get('end_date')
        
        rent_from = date.today()

        # Validate ngày thuê đến (end_date)
        rent_to_str = request.form.get('end_date')
        if not rent_to_str:
            return "Bạn phải nhập ngày thuê đến", 400

        try:
            rent_to = date.fromisoformat(rent_to_str)
        except ValueError:
            return "Ngày thuê không hợp lệ", 400

        if rent_to <= rent_from:
            return "Ngày thuê phải lớn hơn ngày hiện tại", 400
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO renters (house_id, user_id, name, cccd, age, gender, number_of_people, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (house_id, current_user.id, full_name, id_card, age, gender, people_count, rent_from, rent_to))

        cur.execute("UPDATE houses SET is_rented = TRUE WHERE id = %s", (house_id,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/my_rentals')

    return render_template('rent.html', house_id=house_id)
    
@app.route('/edit/<int:house_id>', methods=['GET', 'POST'])
def edit(house_id):
    conn = get_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        address = request.form['address']
        owner = request.form['owner']
        price = request.form['price']
        
        # Debug: In ra tất cả dữ liệu form
        print("Form data:", dict(request.form))
        
        # Thay đổi cách xử lý checkbox:
        # Nếu 'is_rented' có trong form -> checkbox được chọn -> True
        # Nếu không có trong form -> checkbox không được chọn -> False
        is_rented = 'is_rented' in request.form
        print(f"Checkbox 'is_rented' trong form: {'is_rented' in request.form}")
        print(f"Giá trị is_rented được gán: {is_rented}")
        
        try:
            price = int(price)
        except ValueError:
            return "Giá phải là số nguyên", 400
        
        # Debug: In ra câu SQL và tham số
        print(f"SQL: UPDATE houses SET address = %s, owner = %s, price = %s, is_rented = %s WHERE id = %s")
        print(f"Params: ({address}, {owner}, {price}, {is_rented}, {house_id})")
        
        cur.execute("""
            UPDATE houses
            SET address = %s, owner = %s, price = %s, is_rented = %s
            WHERE id = %s
        """, (address, owner, price, is_rented, house_id))
        
        # Debug: Kiểm tra số dòng bị ảnh hưởng
        rows_affected = cur.rowcount
        print(f"Rows affected by update: {rows_affected}")
        
        # Kiểm tra giá trị sau khi cập nhật
        cur.execute("SELECT is_rented FROM houses WHERE id = %s", (house_id,))
        updated_value = cur.fetchone()[0]
        print(f"Value in database after update: {updated_value}")
        
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
    SELECT r.id, r.user_id, r.name, r.cccd, r.age, r.gender, r.number_of_people, r.start_date, r.end_date,
       r.house_id
FROM renters r
WHERE r.end_date IS NULL OR r.end_date > CURRENT_DATE
ORDER BY r.start_date DESC
""", (current_user.id,))

    renters = cur.fetchall()
    print("renters là ",renters)
    cur.close()
    conn.close()

    return render_template('renters.html', renters=renters)

@app.route('/export_excel')
@login_required
def export_excel():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, image, address, owner, price, is_rented FROM houses ORDER BY id")
    houses = cur.fetchall()
    cur.close()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Danh sách nhà"

    # Header
    ws.append(['ID', 'Hình ảnh', 'Địa chỉ', 'Chủ nhà', 'Giá', 'Trạng thái thuê'])

    # Data
    for h in houses:
        # h = (id, image, address, owner, price, is_rented)
        status = 'Đã thuê' if h[5] else 'Chưa thuê'
        # Hình ảnh: bạn có thể ghi tên file ảnh hoặc link đến ảnh
        image_name = h[1] if h[1] else ''
        ws.append([h[0], image_name, h[2], h[3], h[4], status])

    # Lưu workbook vào bộ nhớ đệm
    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    # Trả file về cho client
    return send_file(
        file_stream,
        as_attachment=True,
        download_name="danh_sach_nha.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route('/statistics')
@login_required
def statistics():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            h.address,
            h.owner,
            h.price,
            COUNT(r.id) AS rent_count,
            COUNT(r.id) * h.price AS total_revenue
        FROM houses h
        LEFT JOIN renters r ON h.id = r.house_id
        GROUP BY h.id, h.address, h.owner, h.price
        ORDER BY rent_count DESC
    """)
    stats = cur.fetchall()
    cur.close()
    conn.close()

    # Chuyển dữ liệu thành list dict dễ dùng ở JS
    
    stats_dicts = [
        {
            "address": row[0],
            "owner": row[1],
            "price": row[2],
            "rent_count": row[3],
            "total_revenue": row[4]
        }
        for row in stats
    ]

    return render_template('statistics.html', stats=stats, stats_json=stats_dicts)

@app.route('/my_rentals')
@login_required
def my_rentals():
    print("Current user id:", current_user.id)  # Debug
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT r.id, r.house_id, r.name, r.cccd, r.age, r.gender, r.number_of_people, r.start_date, r.end_date,
           h.address, h.owner, h.price
    FROM renters r
    JOIN houses h ON r.house_id = h.id
    WHERE r.user_id = %s
      AND (r.end_date IS NULL OR r.end_date > CURRENT_DATE)
    ORDER BY r.start_date DESC
    """, (current_user.id,))
    rentals = cur.fetchall()
    print("Rentals fetched:", rentals)  # Debug
    cur.close()
    conn.close()

    current_date = date.today()
    return render_template('my_rentals.html', rentals=rentals, current_date=current_date)

@app.route('/cancel_rental/<int:rental_id>', methods=['POST', 'GET']) 
@login_required
def cancel_rental(rental_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Cập nhật end_date cho người thuê hiện tại
        cur.execute("""
            UPDATE renters 
            SET end_date = CURRENT_DATE 
            WHERE id = %s AND user_id = %s
        """, (rental_id, current_user.id))

        # 2. Lấy house_id tương ứng với rental_id này
        cur.execute("SELECT house_id FROM renters WHERE id = %s", (rental_id,))
        house_id_row = cur.fetchone()

        if house_id_row:
            house_id = house_id_row[0]

            # 3. Kiểm tra xem còn ai đang thuê nhà này không (end_date IS NULL hoặc > hôm nay)
            cur.execute("""
                SELECT COUNT(*) FROM renters 
                WHERE house_id = %s AND (end_date IS NULL OR end_date > CURRENT_DATE)
            """, (house_id,))
            active_renters = cur.fetchone()[0]

            # 4. Nếu không còn ai thuê thì cập nhật is_rented = FALSE
            if active_renters == 0:
                cur.execute("""
                    UPDATE houses SET is_rented = FALSE WHERE id = %s
                """, (house_id,))

        conn.commit()
    except Exception as e:
        print("Lỗi khi hủy thuê:", e)
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()  # Đăng xuất user hiện tại
    return render_template('login.html')  
if __name__ == '__main__':
    app.run(debug=True)
