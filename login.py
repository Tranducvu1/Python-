from flask import Blueprint, render_template, request, redirect
from flask_login import LoginManager, current_user, login_required, login_user
from utils import get_connection
from flask_bcrypt import Bcrypt
from flask_login import UserMixin


auth_bp = Blueprint('auth', __name__)  # Bỏ url_prefix='/auth'
bcrypt = Bcrypt()


login_manager = LoginManager()

class User(UserMixin):
    def __init__(self, id, username, password, role):
        self.id = id
        self.username = username
        self.password = password
        self.role = role

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password, role FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return User(*row)
    return None

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        role = request.form['role']
        email = request.form['email']

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password, role, email) VALUES (%s, %s, %s, %s)",
                    (username, password, role, email))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/login')
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password, role FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and bcrypt.check_password_hash(user[2], password):
            login_user(User(*user))
            return redirect('/')
        else:
            return "Sai tài khoản hoặc mật khẩu", 401

    return render_template('login.html')

@auth_bp.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']
        return "Nếu email tồn tại, hướng dẫn đã được gửi", 200
    return render_template('forgot.html')

# @auth_bp.route('/')
# @login_required
# def index():
   
#     conn = get_connection()
#     cur = conn.cursor()

#     if current_user.role == 'admin':
#         cur.execute("SELECT id, address, owner, price, is_rented, image FROM houses ORDER BY id")
#     else:
#         cur.execute("SELECT id, address, owner, price, is_rented, image FROM houses WHERE is_rented = FALSE ORDER BY id")
    
#     houses = cur.fetchall()
#     cur.close()
#     conn.close() 
#     return render_template('index.html', houses=houses, user=current_user)

# Import hàm auto_update_rental_status từ file cũ
