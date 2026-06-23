import sqlite3
import functools

from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-to-a-random-secret-key'
csrf = CSRFProtect(app)

DATABASE = 'app.db'

# 預設管理員帳號（題目要求內建這組帳密）
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'


# ---------- 資料庫工具函式 ----------
def get_db():
    """建立並回傳一個新的資料庫連線，使用 row_factory 讓查詢結果可用欄位名存取。"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """程式啟動時自動檢查並建立 customer 資料表。"""
    conn = get_db()
    try:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS customer (
                    cid TEXT PRIMARY KEY,
                    cname TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT NOT NULL,
                    address TEXT
                )
            ''')
    finally:
        conn.close()
init_db() 

# ---------- Flask-WTF 表單 ----------
class LoginForm(FlaskForm):
    username = StringField('帳號', validators=[DataRequired(message='帳號必填')])
    password = PasswordField('密碼', validators=[DataRequired(message='密碼必填')])
    submit = SubmitField('登入')


class CustomerForm(FlaskForm):
    cid = StringField('* 客戶編號', validators=[
        DataRequired(message='❌客戶編號必填'),
        Length(3, 10, message='❌客戶編號長度需為 3~10 字元')
    ])
    cname = StringField('* 客戶姓名', validators=[DataRequired(message='❌姓名必填')])
    email = StringField('* 電子郵件', validators=[
        DataRequired(message='❌Email 必填'),
        Email(message='❌請輸入有效的 Email 格式')
    ])
    phone = StringField('* 聯絡電話', validators=[
        DataRequired(message='❌電話必填'),
        Length(10, 10, message='❌電話必須為 10 碼')
    ])
    address = StringField('地址')
    submit = SubmitField('儲存')


# ---------- 權限保護 decorator ----------
def login_required(view):
    """檢查 session 是否已登入，未登入則導向 /login。"""
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'username' not in session:
            flash('請先登入才能存取此頁面')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped_view


# ---------- 路由：首頁 ----------
@app.route('/')
def index():
    return render_template('index.html')


# ---------- 路由：登入 / 登出 ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('customer_list'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['username'] = username
            flash('登入成功')
            return redirect(url_for('customer_list'))
        else:
            flash('帳號或密碼錯誤')

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    flash('已登出')
    return redirect(url_for('login'))


# ---------- 路由：客戶列表 ----------
@app.route('/customers')
@login_required
def customer_list():
    conn = get_db()
    try:
        rows = conn.execute('SELECT * FROM customer ORDER BY cid').fetchall()
    finally:
        conn.close()
    return render_template('customers.html', customers=rows)


# ---------- 路由：新增客戶 ----------
@app.route('/customer/add', methods=['GET', 'POST'])
@login_required
def customer_add():
    form = CustomerForm()

    if form.validate_on_submit():
        conn = get_db()
        try:
            with conn:
                conn.execute(
                    'INSERT INTO customer (cid, cname, email, phone, address) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (form.cid.data, form.cname.data, form.email.data,
                     form.phone.data, form.address.data)
                )
            flash('新增成功')
            return redirect(url_for('customer_list'))
        except sqlite3.IntegrityError:
            flash('客戶編號或 Email 已存在')
        finally:
            conn.close()

    return render_template('customer_form.html', form=form, mode='add')


# ---------- 路由：編輯客戶 ----------
@app.route('/customer/<cid>/edit', methods=['GET', 'POST'])
@login_required
def customer_edit(cid):
    conn = get_db()
    try:
        row = conn.execute('SELECT * FROM customer WHERE cid = ?', (cid,)).fetchone()
        if row is None:
            flash('找不到該客戶資料')
            return redirect(url_for('customer_list'))

        form = CustomerForm()

        if form.validate_on_submit():
            # Email 不可與其他客戶重複（但可維持自己原本的 Email）
            existing = conn.execute(
                'SELECT cid FROM customer WHERE email = ? AND cid != ?',
                (form.email.data, cid)
            ).fetchone()

            if existing:
                flash('此 Email 已被其他客戶使用')
            else:
                try:
                    with conn:
                        conn.execute(
                            'UPDATE customer SET cname = ?, email = ?, phone = ?, address = ? '
                            'WHERE cid = ?',
                            (form.cname.data, form.email.data, form.phone.data,
                             form.address.data, cid)
                        )
                    flash('更新成功')
                    return redirect(url_for('customer_list'))
                except sqlite3.IntegrityError:
                    flash('更新失敗，Email 已存在')

        elif request.method == 'GET':
            # 將資料庫現有資料帶入表單
            form.cid.data = row['cid']
            form.cname.data = row['cname']
            form.email.data = row['email']
            form.phone.data = row['phone']
            form.address.data = row['address']
    finally:
        conn.close()

    return render_template('customer_form.html', form=form, mode='edit', cid=cid)


# ---------- 路由：刪除客戶 ----------
@app.route('/customer/<cid>/delete', methods=['POST'])
@login_required
def customer_delete(cid):
    conn = get_db()
    try:
        with conn:
            conn.execute('DELETE FROM customer WHERE cid = ?', (cid,))
        flash('刪除成功')
    finally:
        conn.close()
    return redirect(url_for('customer_list'))


# ---------- 簡單的錯誤頁 ----------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message='找不到此頁面 (404)'), 404
