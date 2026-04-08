# app.py - ሙሉ ሆቴል ማኔጅመንት ሲስተም (ሁሉም ባህሪያት ያሉት)

from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
import sqlite3
from datetime import datetime, timedelta
import hashlib
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ሚስጥራዊ_ቁልፍ_ይህን_ቀይሩት')

# ==================== የውሂብ ጎታ ====================
DB_PATH = '/var/data/hotel.db' if os.path.exists('/var/data') else 'hotel.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        fullname TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        price REAL,
        unit TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        product_id INTEGER PRIMARY KEY,
        quantity REAL DEFAULT 0,
        min_stock REAL DEFAULT 5,
        last_updated TEXT,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_number INTEGER,
        table_name TEXT UNIQUE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id INTEGER,
        waiter_id INTEGER,
        created_at TEXT,
        status TEXT DEFAULT 'open',
        total REAL DEFAULT 0,
        payment_method TEXT,
        payment_reference TEXT,
        FOREIGN KEY(table_id) REFERENCES tables(id),
        FOREIGN KEY(waiter_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        unit_price REAL,
        total_price REAL,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS staff_expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        bar_manager_id INTEGER,
        service_description TEXT,
        amount REAL,
        confirmed INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY(employee_id) REFERENCES users(id),
        FOREIGN KEY(bar_manager_id) REFERENCES users(id)
    )''')
    
    admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
    barman_pass = hashlib.sha256('barman123'.encode()).hexdigest()
    waiter_pass = hashlib.sha256('waiter123'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (id, username, password, role, fullname) VALUES (1, 'admin', ?, 'owner', 'ዋና አስተዳዳሪ')", (admin_pass,))
    c.execute("INSERT OR IGNORE INTO users (id, username, password, role, fullname) VALUES (2, 'barman', ?, 'barman', 'አለማየሁ ባርማን')", (barman_pass,))
    c.execute("INSERT OR IGNORE INTO users (id, username, password, role, fullname) VALUES (3, 'waiter', ?, 'waiter', 'ማሞ አስተናጋጅ')", (waiter_pass,))
    
    products = [
        (1, 'ሀበሻ ቢራ', 'beer', 45, 'bottle'), (2, 'ዳሽን ቢራ', 'beer', 50, 'bottle'),
        (3, 'ሀረር ቢራ', 'beer', 40, 'bottle'), (4, 'በደሌ ቢራ', 'beer', 55, 'bottle'),
        (5, 'ድራፍት ሲንግል', 'draft', 60, 'glass'), (6, 'ድራፍት ጃንቦ', 'draft', 110, 'jug'),
        (7, 'ጂን ሲንግል', 'gin', 80, 'glass'), (8, 'ጂን ዳብል', 'gin', 150, 'glass'),
        (9, 'ሽሮ', 'soda', 25, 'bottle'), (10, 'ተጋቢኖ', 'food', 120, 'plate'),
        (11, 'ቆጣ ምግብ', 'food', 80, 'plate'),
    ]
    for pid, name, cat, price, unit in products:
        c.execute("INSERT OR IGNORE INTO products (id, name, category, price, unit) VALUES (?, ?, ?, ?, ?)", (pid, name, cat, price, unit))
        c.execute("INSERT OR IGNORE INTO inventory (product_id, quantity, min_stock, last_updated) VALUES (?, 50, 5, ?)", (pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    for i in range(1, 6):
        c.execute("INSERT OR IGNORE INTO tables (table_number, table_name) VALUES (?, ?)", (i, f"ጠረጴዛ {i}"))
    
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                return "እርስዎ ይህን ገጽ ለማየት አይፈቀድልዎትም", 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        db.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['fullname'] = user['fullname']
            return redirect(url_for('dashboard'))
        else:
            flash('ስህተት የተጠቃሚ ስም ወይም ይሁንታ')
    return render_template_string('''
<!DOCTYPE html><html><head><title>ግቤት</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>.marquee{background:linear-gradient(90deg,#ff6b6b,#4ecdc4);color:white;padding:12px;overflow:hidden;white-space:nowrap;animation:scrollText 15s linear infinite;}@keyframes scrollText{0%{transform:translateX(100%);}100%{transform:translateX(-100%);}}</style></head>
<body><div class="marquee">🏨 ሆቴልዎን ዘመናዊ አስተዳደር ተጠቅመው ትርፍማ ይሁኑ 🚀</div>
<div class="container mt-5"><div class="card mx-auto" style="max-width:400px"><div class="card-header bg-primary text-white"><h4>🍺 ሆቴል ሲስተም</h4></div>
<div class="card-body">{% with m=get_flashed_messages() %}{% if m %}<div class="alert alert-danger">{{ m[0] }}</div>{% endif %}{% endwith %}
<form method="post"><div class="mb-2"><label>የተጠቃሚ ስም</label><input name="username" class="form-control"></div>
<div class="mb-2"><label>ይሁንታ</label><input type="password" name="password" class="form-control"></div>
<button class="btn btn-primary w-100">ግባ</button></form><div class="mt-3 small">admin/admin123 | barman/barman123 | waiter/waiter123</div></div></div></div></body></html>''')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required()
def dashboard():
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    sales = db.execute("SELECT SUM(total) as total FROM orders WHERE status='closed' AND created_at LIKE ?", (today+'%',)).fetchone()
    total_sales = sales['total'] if sales['total'] else 0
    role = session['role']
    waiter_btns = "<a href='" + url_for('waiter_orders') + "' class='btn btn-primary m-1'>📝 ትዕዛዝ መውሰድ</a>"
    barman_btns = "<a href='" + url_for('barman_expenses') + "' class='btn btn-warning m-1'>💰 የሰራተኛ ወጪ</a><a href='" + url_for('barman_inventory') + "' class='btn btn-info m-1'>📦 ክምችት አስተዳደር</a><a href='" + url_for('barman_waiter_sales') + "' class='btn btn-secondary m-1'>📊 የአስተናጋጆች ሽያጭ</a>"
    owner_btns = "<a href='" + url_for('owner_reports') + "' class='btn btn-info m-1'>📊 ሪፖርቶች</a><a href='" + url_for('owner_top_products') + "' class='btn btn-warning m-1'>🏆 ከፍተኛ ሽያጭ ምርቶች</a><a href='" + url_for('owner_products') + "' class='btn btn-secondary m-1'>🍺 ምርቶች</a><a href='" + url_for('owner_users') + "' class='btn btn-dark m-1'>👥 ሰራተኞች</a><a href='" + url_for('owner_advanced_reports') + "' class='btn btn-danger m-1'>📈 የላቀ ሪፖርት</a>"
    common_btns = "<a href='" + url_for('manage_tables') + "' class='btn btn-success m-1'>🍽️ ጠረጴዛዎች አስተዳደር</a>"
    if role == 'waiter':
        btns = waiter_btns + common_btns
        marquee_msg = "🎯 የዚህ ሆቴል ትርፍማነት ለ እርስዎም የስራ እድል መፈጠር ነው! 💼"
    elif role == 'barman':
        btns = barman_btns + common_btns
        marquee_msg = "⚠️ ትኩረት ሰጠህ በመስራት ከኪሳራ እራቅ! 📉➡️📈"
    else:
        btns = owner_btns + common_btns
        marquee_msg = "💡 ዛሬ ምን ሰራህ? ስንት አተረፍህ? 🧠💰"
        top_waiter_day = db.execute("SELECT u.fullname, SUM(o.total) as total FROM orders o JOIN users u ON o.waiter_id = u.id WHERE o.status='closed' AND date(o.created_at) = date('now') GROUP BY u.id ORDER BY total DESC LIMIT 1").fetchone()
        top_waiter_week = db.execute("SELECT u.fullname, SUM(o.total) as total FROM orders o JOIN users u ON o.waiter_id = u.id WHERE o.status='closed' AND date(o.created_at) >= date('now', '-7 days') GROUP BY u.id ORDER BY total DESC LIMIT 1").fetchone()
        top_waiter_month = db.execute("SELECT u.fullname, SUM(o.total) as total FROM orders o JOIN users u ON o.waiter_id = u.id WHERE o.status='closed' AND date(o.created_at) >= date('now', '-30 days') GROUP BY u.id ORDER BY total DESC LIMIT 1").fetchone()
        day_info = f"{top_waiter_day['fullname']} - {top_waiter_day['total']:.2f} ብር" if top_waiter_day else "ምንም ሽያጭ የለም"
        week_info = f"{top_waiter_week['fullname']} - {top_waiter_week['total']:.2f} ብር" if top_waiter_week else "ምንም ሽያጭ የለም"
        month_info = f"{top_waiter_month['fullname']} - {top_waiter_month['total']:.2f} ብር" if top_waiter_month else "ምንም ሽያጭ የለም"
        top_waiter_html = f'''<div class="row mt-4"><div class="col-md-4"><div class="card text-white bg-primary"><div class="card-header">🏅 የቀኑ ከፍተኛ ሽያጭ አስተናጋጅ</div><div class="card-body"><h5>{day_info}</h5></div></div></div><div class="col-md-4"><div class="card text-white bg-success"><div class="card-header">🏆 የሳምንቱ ከፍተኛ ሽያጭ አስተናጋጅ</div><div class="card-body"><h5>{week_info}</h5></div></div></div><div class="col-md-4"><div class="card text-white bg-warning"><div class="card-header">🌟 የወሩ ከፍተኛ ሽያጭ አስተናጋጅ</div><div class="card-body"><h5>{month_info}</h5></div></div></div></div>'''
        db.close()
        return render_template_string(f'''<!DOCTYPE html><html><head><title>ዳሽቦርድ</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"><style>.marquee{{background:linear-gradient(90deg,#ff6b6b,#4ecdc4);color:white;padding:12px;overflow:hidden;white-space:nowrap;animation:scrollText 15s linear infinite;}}@keyframes scrollText{{0%{{transform:translateX(100%);}}100%{{transform:translateX(-100%);}}}}</style><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="marquee">{marquee_msg}</div><div class="container mt-4"><div class="card text-white bg-success"><div class="card-body"><h5>የዛሬ ሽያጭ</h5><h2>{total_sales} ብር</h2></div></div>{top_waiter_html}<div class="mt-4">{btns}</div></div></body></html>''')
    db.close()
    return render_template_string(f'''<!DOCTYPE html><html><head><title>ዳሽቦርድ</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"><style>.marquee{{background:linear-gradient(90deg,#ff6b6b,#4ecdc4);color:white;padding:12px;overflow:hidden;white-space:nowrap;animation:scrollText 15s linear infinite;}}@keyframes scrollText{{0%{{transform:translateX(100%);}}100%{{transform:translateX(-100%);}}}}</style><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="marquee">{marquee_msg}</div><div class="container mt-4"><div class="card text-white bg-success"><div class="card-body"><h5>የዛሬ ሽያጭ</h5><h2>{total_sales} ብር</h2></div></div><div class="mt-4">{btns}</div></div></body></html>''')

# ==================== ጠረጴዛዎች አስተዳደር ====================
@app.route('/manage_tables')
@login_required()
def manage_tables():
    db = get_db()
    tables = db.execute("SELECT * FROM tables ORDER BY table_number").fetchall()
    db.close()
    rows = ''.join([f'<tr><td>{t["table_number"]}</td><td>{t["table_name"]}</td><td><button class="btn btn-sm btn-primary" onclick="editTable({t["id"]}, \'{t["table_name"]}\')">✏️ አርትዕ</button> <button class="btn btn-sm btn-danger" onclick="deleteTable({t["id"]})">🗑 ሰርዝ</button></td></tr>' for t in tables])
    return render_template_string(f'''<!DOCTYPE html><html><head><title>ጠረጴዛዎች አስተዳደር</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"><script>function addTable(){{ let num=document.getElementById('num').value, name=document.getElementById('name').value; if(!num||!name){{ alert('ሁለቱንም ይሙሉ'); return; }} fetch('/api/add_table',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{table_number:num, table_name:name}})}}).then(()=>location.reload()); }} function editTable(id, oldName){{ let newName=prompt('አዲስ ስም ያስገቡ', oldName); if(newName) fetch('/api/edit_table',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:id, table_name:newName}})}}).then(()=>location.reload()); }} function deleteTable(id){{ if(confirm('እርግጠኛ ነዎት?')) fetch('/api/delete_table',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:id}})}}).then(()=>location.reload()); }}</script></head><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="container mt-4"><h2>🍽️ ጠረጴዛዎች አስተዳደር</h2><div class="row"><div class="col-md-4"><div class="card"><div class="card-header">አዲስ ጠረጴዛ ጨምር</div><div class="card-body"><input id="num" type="number" placeholder="ቁጥር" class="form-control mb-2"><input id="name" placeholder="ስም" class="form-control mb-2"><button class="btn btn-primary" onclick="addTable()">ጨምር</button></div></div></div><div class="col-md-8"><table class="table table-bordered"><thead class="table-dark"><tr><th>ቁጥር</th><th>ስም</th><th>ድርጊት</th></tr></thead><tbody>{rows}</tbody></table></div></div><div class="mt-3"><a href="{{ url_for('dashboard') }}" class="btn btn-secondary">ወደ ዳሽቦርድ ተመለስ</a></div></div></body></html>''')

@app.route('/api/add_table', methods=['POST'])
@login_required()
def add_table():
    data = request.json
    db = get_db()
    db.execute("INSERT INTO tables (table_number, table_name) VALUES (?, ?)", (data['table_number'], data['table_name']))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/edit_table', methods=['POST'])
@login_required()
def edit_table():
    data = request.json
    db = get_db()
    db.execute("UPDATE tables SET table_name = ? WHERE id = ?", (data['table_name'], data['id']))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/delete_table', methods=['POST'])
@login_required()
def delete_table():
    data = request.json
    db = get_db()
    db.execute("DELETE FROM tables WHERE id = ?", (data['id'],))
    db.commit()
    db.close()
    return jsonify({'success': True})

# ==================== አስተናጋጅ ====================
@app.route('/waiter/orders')
@login_required(role='waiter')
def waiter_orders():
    db = get_db()
    tables = db.execute("SELECT * FROM tables ORDER BY table_number").fetchall()
    products = db.execute("SELECT * FROM products").fetchall()
    open_orders = db.execute("SELECT o.*, t.table_name FROM orders o JOIN tables t ON o.table_id = t.id WHERE o.status='open' AND o.waiter_id=?", (session['user_id'],)).fetchall()
    closed_orders = db.execute("SELECT o.*, t.table_name FROM orders o JOIN tables t ON o.table_id = t.id WHERE o.status='closed' AND o.waiter_id=? ORDER BY o.created_at DESC LIMIT 10", (session['user_id'],)).fetchall()
    today = datetime.now().strftime('%Y-%m-%d')
    today_sales = db.execute("SELECT SUM(total) as total FROM orders WHERE status='closed' AND waiter_id=? AND created_at LIKE ?", (session['user_id'], today+'%')).fetchone()
    today_total = today_sales['total'] if today_sales['total'] else 0
    db.close()
    tables_html = ''.join([f'<button class="list-group-item list-group-item-action" onclick="createOrder({t["id"]})">ጠረጴዛ {t["table_name"]}</button>' for t in tables])
    products_html = ''.join([f'<option value="{p["id"]}">{p["name"]} - {p["price"]} ብር</option>' for p in products])
    open_orders_html = ''
    for o in open_orders:
        open_orders_html += f'''<div class="card mb-2"><div class="card-body"><h5>{o["table_name"]}</h5><p>ጠቅላላ: {o["total"]} ብር | ቀን: {o["created_at"][:16]}</p><button class="btn btn-sm btn-success" onclick="viewOrder({o["id"]})">ዝርዝር</button><button class="btn btn-sm btn-primary" onclick="showReceipt({o["id"]})">🧾 ደረሰኝ አሳይ</button><button class="btn btn-sm btn-danger" onclick="openPaymentModal({o["id"]})">💳 ሂሳብ ክፈል</button></div></div>'''
    closed_html = ''
    for o in closed_orders:
        closed_html += f'''<div class="card mb-2 bg-light"><div class="card-body"><h5>{o["table_name"]} (የተዘጋ)</h5><p>ጠቅላላ: {o["total"]} ብር | ቀን: {o["created_at"][:16]}</p><button class="btn btn-sm btn-primary" onclick="showReceipt({o["id"]})">🧾 ደረሰኝ አሳይ</button></div></div>'''
    payment_methods = ["ንግድ ባንክ", "አዋሽ ባንክ", "አቢሲኒያ ባንክ", "አባይ ባንክ", "ቴሌ ብር", "ዎገን ባንክ"]
    methods_options = ''.join([f'<option value="{m}">{m}</option>' for m in payment_methods])
    return render_template_string(f'''<!DOCTYPE html><html><head><title>የአስተናጋጅ ትዕዛዝ</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"><script src="https://code.jquery.com/jquery-3.6.0.min.js"></script><style>.marquee{{background:linear-gradient(90deg,#ff6b6b,#4ecdc4);color:white;padding:12px;overflow:hidden;white-space:nowrap;animation:scrollText 15s linear infinite;}}@keyframes scrollText{{0%{{transform:translateX(100%);}}100%{{transform:translateX(-100%);}}}}</style></head><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="marquee">🎯 የዚህ ሆቴል ትርፍማነት ለ እርስዎም የስራ እድል መፈጠር ነው! 💼</div><div class="container mt-4"><div class="alert alert-info">💰 የዛሬ ሽያጬ: <strong>{today_total} ብር</strong> <button class="btn btn-sm btn-outline-primary ms-2" onclick="showDailyReceipt()">🧾 የዛሬ ሽያጮቼ</button></div><h2>📝 ትዕዛዝ አስተዳደር</h2><div class="row"><div class="col-md-4"><h4>ጠረጴዛዎች</h4><div class="list-group">{tables_html}</div></div><div class="col-md-8"><h4>ክፍት ትዕዛዞች</h4><div id="openOrders">{open_orders_html}</div><h4 class="mt-4">የተዘጉ ትዕዛዞች (ከቅርብ ጊዜ)</h4><div id="closedOrders">{closed_html}</div></div></div><div class="mt-3"><h4>ምርቶች ለመጨመር</h4><select id="productSelect" class="form-select w-50 d-inline">{products_html}</select><input type="number" id="qty" placeholder="ብዛት" class="w-25 d-inline ms-2" value="1"><button class="btn btn-primary ms-2" onclick="addToCurrentOrder()">ጨምር</button><p class="mt-2">በመጀመሪያ ከላይ ካሉት ክፍት ትዕዛዞች አንዱን በ"ዝርዝር" ላይ ጠቅ ያድርጉ።</p></div></div><div class="modal fade" id="paymentModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">💳 ክፍያ መረጃ</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><p>ትዕዛዝ ቁጥር: <span id="modalOrderId"></span></p><label>የክፍያ ዘዴ ይምረጡ:</label><select id="paymentMethod" class="form-control mb-3">{methods_options}</select><label>ሪፈረንስ ቁጥር (የክፍያ መጠየቂያ ቁጥር):</label><input type="text" id="paymentRef" class="form-control" placeholder="ለምሳሌ: 1234567890"></div><div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">ዝጋ</button><button type="button" class="btn btn-primary" onclick="processPayment()">ክፈል እና ዝጋ</button></div></div></div></div><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script><script>let currentOrderId = null; let currentCloseOrderId = null; function createOrder(tableId) {{ fetch('/api/create_order', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{table_id:tableId}})}}).then(res=>res.json()).then(data=>{{if(data.order_id) location.reload();}}); }} function viewOrder(orderId) {{ currentOrderId = orderId; fetch('/api/order_items/'+orderId).then(res=>res.json()).then(data=>{{ let msg=''; data.items.forEach(i=>{{msg+=i.name+' x'+i.quantity+' = '+i.total_price+' ብር\\n';}}); alert(msg+'\\nጠቅላላ: '+data.total+' ብር\\nአሁን ምርቶች መጨመር ይችላሉ'); }}); }} function addToCurrentOrder() {{ if(!currentOrderId){{ alert('በመጀመሪያ ከላይ ካሉት ክፍት ትዕዛዞች አንዱን ይምረጡ'); return; }} let pid=document.getElementById('productSelect').value; let qty=document.getElementById('qty').value; fetch('/api/add_item',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{order_id:currentOrderId,product_id:pid,quantity:qty}})}}).then(()=>location.reload()); }} function showReceipt(orderId) {{ window.open('/waiter/receipt/'+orderId, '_blank', 'width=500,height=600'); }} function showDailyReceipt() {{ window.open('/waiter/daily_sales', '_blank', 'width=500,height=600'); }} function openPaymentModal(orderId) {{ currentCloseOrderId = orderId; document.getElementById('modalOrderId').innerText = orderId; document.getElementById('paymentMethod').value = ''; document.getElementById('paymentRef').value = ''; var myModal = new bootstrap.Modal(document.getElementById('paymentModal')); myModal.show(); }} function processPayment() {{ let method = document.getElementById('paymentMethod').value; let ref = document.getElementById('paymentRef').value; if(!method){{ alert('እባክዎ የክፍያ ዘዴ ይምረጡ'); return; }} if(!ref){{ alert('እባክዎ ሪፈረንስ ቁጥር ያስገቡ'); return; }} fetch('/api/close_order_with_payment', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{order_id:currentCloseOrderId, payment_method:method, payment_reference:ref}})}}).then(res=>res.json()).then(data=>{{ if(data.success) location.reload(); else alert('ስህተት: '+data.error); }}); }}</script></body></html>''')

@app.route('/waiter/daily_sales')
@login_required(role='waiter')
def waiter_daily_sales():
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    orders = db.execute("SELECT o.*, t.table_name FROM orders o JOIN tables t ON o.table_id = t.id WHERE o.status='closed' AND o.waiter_id=? AND date(o.created_at) = date('now') ORDER BY o.created_at", (session['user_id'],)).fetchall()
    total = sum(o['total'] for o in orders)
    rows = ''.join([f'<tr><td>{o["created_at"][:16]}</td><td>{o["table_name"]}</td><td class="text-end">{o["total"]:.2f} ብር</td></tr>' for o in orders])
    return render_template_string(f'''<!DOCTYPE html><html><head><title>የዕለት ሽያጭ ሪፖርት</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head><body><div class="container mt-3"><div class="card"><div class="card-header bg-primary text-white">📅 {today} - የሽያጭ ሪፖርት</div><div class="card-body"><table class="table table-sm"><thead><tr><th>ሰዓት</th><th>ጠረጴዛ</th><th class="text-end">ጠቅላላ</th></tr></thead><tbody>{rows}<tr class="fw-bold"><td colspan="2" class="text-end">ጠቅላላ ድምር</td><td class="text-end">{total:.2f} ብር</td></tr></tbody></table><button class="btn btn-primary mt-2" onclick="window.print()">🖨️ አትም</button><button class="btn btn-secondary mt-2" onclick="window.close()">ዝጋ</button></div></div></div></body></html>''')

@app.route('/waiter/receipt/<int:order_id>')
@login_required(role='waiter')
def waiter_receipt(order_id):
    db = get_db()
    order = db.execute("SELECT o.*, t.table_name, u.fullname as waiter_name FROM orders o JOIN tables t ON o.table_id = t.id JOIN users u ON o.waiter_id = u.id WHERE o.id = ?", (order_id,)).fetchone()
    if not order:
        return "ትዕዛዝ አልተገኘም", 404
    items = db.execute("SELECT oi.*, p.name as product_name FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?", (order_id,)).fetchall()
    db.close()
    items_rows = ''.join([f'<td>{item["product_name"]} existing<td class="text-center">{item["quantity"]} existing<td class="text-end">{item["unit_price"]:.2f} existing<td class="text-end">{item["total_price"]:.2f} existing</tr>' for item in items])
    payment_info = f"<p><strong>ክፍያ ዘዴ:</strong> {order['payment_method']}<br><strong>ሪፈረንስ ቁጥር:</strong> {order['payment_reference']}</p>" if order['payment_method'] else ""
    return render_template_string(f'''<!DOCTYPE html><html><head><title>ደረሰኝ - ትዕዛዝ #{order_id}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"><style>@media print{{.no-print{{display:none;}}}} .receipt{{max-width:400px;margin:auto;font-family:monospace;}}</style></head><body><div class="container receipt mt-3"><div class="header text-center border-bottom pb-2"><h3>🍺 ሆቴል ሲስተም</h3><p>የሽያጭ ደረሰኝ</p></div><div><p><strong>ትዕዛዝ ቁጥር:</strong> #{order['id']}<br><strong>ጠረጴዛ:</strong> {order['table_name']}<br><strong>ቀን እና ሰዓት:</strong> {order['created_at']}<br><strong>አስተናጋጅ:</strong> {order['waiter_name']}<br><strong>ሁኔታ:</strong> {'የተዘጋ' if order['status'] == 'closed' else 'ክፍት'}</p>{payment_info}</div><table class="table table-sm"><thead><tr><th>የአገልግሎት አይነት</th><th class="text-center">ብዛት</th><th class="text-end">የአንዱ ዋጋ</th><th class="text-end">ጠቅላላ</th></tr></thead><tbody>{items_rows}<tr class="total"><td colspan="3" class="text-end"><strong>ጠቅላላ ድምር</strong></td><td class="text-end"><strong>{order['total']:.2f} ብር</strong></td></tr></tbody></table><div class="footer text-center border-top pt-2 mt-2"><p>እንደገና ለመጠቀም እንኳን ደህና መጡ!</p><button class="btn btn-sm btn-primary no-print" onclick="window.print()">🖨️ አትም</button><button class="btn btn-sm btn-secondary no-print" onclick="window.close()">ዝጋ</button></div></div></body></html>''')

@app.route('/api/create_order', methods=['POST'])
@login_required(role='waiter')
def create_order():
    table_id = request.json['table_id']
    db = get_db()
    db.execute("INSERT INTO orders (table_id, waiter_id, created_at, status) VALUES (?, ?, ?, 'open')", (table_id, session['user_id'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    db.commit()
    order_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return jsonify({'order_id': order_id})

@app.route('/api/add_item', methods=['POST'])
@login_required(role='waiter')
def add_item():
    data = request.json
    order_id = data['order_id']
    product_id = data['product_id']
    quantity = int(data['quantity'])
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    unit_price = product['price']
    total_price = unit_price * quantity
    db.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price, total_price) VALUES (?,?,?,?,?)", (order_id, product_id, quantity, unit_price, total_price))
    db.execute("UPDATE orders SET total = (SELECT SUM(total_price) FROM order_items WHERE order_id=?) WHERE id=?", (order_id, order_id))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/order_items/<int:order_id>')
@login_required()
def get_order_items(order_id):
    db = get_db()
    items = db.execute("SELECT oi.*, p.name FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id=?", (order_id,)).fetchall()
    order = db.execute("SELECT total FROM orders WHERE id=?", (order_id,)).fetchone()
    db.close()
    return jsonify({'items': [dict(item) for item in items], 'total': order['total']})

@app.route('/api/close_order_with_payment', methods=['POST'])
@login_required(role='waiter')
def close_order_with_payment():
    data = request.json
    db = get_db()
    db.execute("UPDATE orders SET status='closed', payment_method=?, payment_reference=? WHERE id=?", (data['payment_method'], data['payment_reference'], data['order_id']))
    db.commit()
    db.close()
    return jsonify({'success': True})

# ==================== ባርማን ====================
@app.route('/barman/expenses')
@login_required(role='barman')
def barman_expenses():
    db = get_db()
    employees = db.execute("SELECT id, fullname FROM users WHERE role='waiter'").fetchall()
    expenses = db.execute("SELECT se.*, u.fullname as emp_name FROM staff_expenses se JOIN users u ON se.employee_id = u.id WHERE se.confirmed=0").fetchall()
    db.close()
    employees_html = ''.join([f'<option value="{e["id"]}">{e["fullname"]}</option>' for e in employees])
    expenses_html = ''.join([f'<li class="list-group-item">{e["emp_name"]} - {e["service_description"]} - {e["amount"]} ብር <button class="btn btn-sm btn-success float-end" onclick="confirmExpense({e["id"]})">አረጋግጥ</button></li>' for e in expenses])
    return render_template_string(f'''<!DOCTYPE html><html><head><title>የባርማን ወጪ መዝገብ</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"><style>.marquee{{background:linear-gradient(90deg,#ff6b6b,#4ecdc4);color:white;padding:12px;overflow:hidden;white-space:nowrap;animation:scrollText 15s linear infinite;}}@keyframes scrollText{{0%{{transform:translateX(100%);}}100%{{transform:translateX(-100%);}}}}</style></head><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="marquee">⚠️ ትኩረት ሰጠህ በመስራት ከኪሳራ እራቅ! 📉➡️📈</div><div class="container mt-4"><h2>💰 የሰራተኛ ወጪ መዝገብ</h2><div class="row"><div class="col-md-5"><div class="card"><div class="card-header">አዲስ ወጪ መዝግብ</div><div class="card-body"><select id="employee_id" class="form-control mb-2"><option value="">ሰራተኛ ምረጥ</option>{employees_html}</select><input type="text" id="desc" class="form-control mb-2" placeholder="አገልግሎት ገልጽ"><input type="number" id="amount" class="form-control mb-2" placeholder="ወጪ ብር"><button class="btn btn-primary" onclick="addExpense()">መዝግብ</button></div></div></div><div class="col-md-7"><h4>ያልተረጋገጠ ወጪ</h4><ul class="list-group">{expenses_html}</ul></div></div></div><script>function addExpense(){{ fetch('/api/add_expense',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{employee_id:document.getElementById('employee_id').value,description:document.getElementById('desc').value,amount:document.getElementById('amount').value}})}}).then(()=>location.reload());}} function confirmExpense(id){{ fetch('/api/confirm_expense/'+id,{{method:'POST'}}).then(()=>location.reload());}}</script></body></html>''')

@app.route('/api/add_expense', methods=['POST'])
@login_required(role='barman')
def add_expense():
    data = request.json
    db = get_db()
    db.execute("INSERT INTO staff_expenses (employee_id, bar_manager_id, service_description, amount, confirmed, created_at) VALUES (?, ?, ?, ?, 0, ?)", (data['employee_id'], session['user_id'], data['description'], data['amount'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/confirm_expense/<int:expense_id>', methods=['POST'])
@login_required(role='barman')
def confirm_expense(expense_id):
    db = get_db()
    db.execute("UPDATE staff_expenses SET confirmed=1 WHERE id=?", (expense_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/barman/inventory')
@login_required(role='barman')
def barman_inventory():
    db = get_db()
    inventory = db.execute("SELECT p.id, p.name, p.category, p.unit, i.quantity, i.min_stock, i.last_updated FROM products p LEFT JOIN inventory i ON p.id = i.product_id ORDER BY p.category, p.name").fetchall()
    db.close()
    rows_html = ''.join([f'<tr><td>{row["name"]}</td><td>{row["category"]}</td><td>{row["unit"]}</td><td class="{"text-danger" if row["quantity"] < row["min_stock"] else ""}">{row["quantity"]}</td><td>{row["min_stock"]}</td><td><input type="number" id="qty_{row["id"]}" class="form-control form-control-sm" style="width:100px" placeholder="አዲስ ብዛት"></td><td><button class="btn btn-sm btn-primary" onclick="updateStock({row["id"]})">አዘምን</button></td></tr>' for row in inventory])
    return render_template_string(f'''<!DOCTYPE html><html><head><title>ክምችት አስተዳደር</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="container mt-4"><h2>📦 የምርት ክምችት አስተዳደር</h2><table class="table table-bordered"><thead class="table-dark"><tr><th>ምርት</th><th>ምድብ</th><th>ክፍል</th><th>ቀሪ ክምችት</th><th>ዝቅተኛ ገደብ</th><th>አዲስ ብዛት</th><th>ድርጊት</th></tr></thead><tbody>{rows_html}</tbody></table><p class="text-muted">ቀይ ቀለም ያላቸው ምርቶች ከዝቅተኛ ገደብ በታች ናቸው!</p></div><script>function updateStock(pid){{ let qty=document.getElementById('qty_'+pid).value; if(!qty){{ alert('እባክዎ ብዛት ያስገቡ'); return; }} fetch('/api/update_inventory',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{product_id:pid,quantity:qty}})}}).then(res=>res.json()).then(data=>{{if(data.success)location.reload();else alert('ስህተት');}});}}</script></body></html>''')

@app.route('/api/update_inventory', methods=['POST'])
@login_required(role='barman')
def update_inventory():
    data = request.json
    db = get_db()
    db.execute("UPDATE inventory SET quantity = ?, last_updated = ? WHERE product_id = ?", (data['quantity'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), data['product_id']))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/barman/waiter_sales')
@login_required(role='barman')
def barman_waiter_sales():
    db = get_db()
    waiters = db.execute("SELECT id, fullname FROM users WHERE role='waiter'").fetchall()
    waiter_list = []
    for w in waiters:
        total = db.execute("SELECT SUM(total) as total FROM orders WHERE status='closed' AND waiter_id=?", (w['id'],)).fetchone()['total'] or 0
        waiter_list.append({'id': w['id'], 'fullname': w['fullname'], 'total': total})
    db.close()
    rows = ''.join([f'<li class="list-group-item d-flex justify-content-between align-items-center"><a href="#" onclick="showWaiterSales({w["id"]}, \'{w["fullname"]}\')">{w["fullname"]}</a><span class="badge bg-primary rounded-pill">{w["total"]:.2f} ብር</span></li>' for w in waiter_list])
    return render_template_string(f'''<!DOCTYPE html><html><head><title>የአስተናጋጆች ሽያጭ</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="container mt-4"><h2>📊 የአስተናጋጆች ሽያጭ ሪፖርት</h2><ul class="list-group">{rows}</ul><p class="mt-2 text-muted">አስተናጋጁን ስም ይንኩ ዝርዝር ለማየት።</p></div><script>function showWaiterSales(waiterId, name){{ window.open('/barman/waiter_sales_detail/'+waiterId, '_blank', 'width=600,height=500'); }}</script></body></html>''')

@app.route('/barman/waiter_sales_detail/<int:waiter_id>')
@login_required(role='barman')
def waiter_sales_detail(waiter_id):
    db = get_db()
    waiter = db.execute("SELECT fullname FROM users WHERE id=?", (waiter_id,)).fetchone()
    if not waiter:
        return "አስተናጋጅ አልተገኘም", 404
    orders = db.execute("SELECT o.id, o.created_at, t.table_name, o.total FROM orders o JOIN tables t ON o.table_id = t.id WHERE o.status='closed' AND o.waiter_id=? ORDER BY o.created_at DESC", (waiter_id,)).fetchall()
    rows = ''
    grand_total = 0
    for o in orders:
        grand_total += o['total']
        rows += f'<tr><td>{o["created_at"][:16]}</td><td>{o["table_name"]}</td><td class="text-end">{o["total"]:.2f} ብር</td><td><button class="btn btn-sm btn-primary" onclick="showReceipt({o["id"]})">🧾 ደረሰኝ</button></td></tr>'
    return render_template_string(f'''<!DOCTYPE html><html><head><title>{waiter['fullname']} - ሽያጭ ዝርዝር</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"><script>function showReceipt(oid){{ window.open('/waiter/receipt/'+oid, '_blank', 'width=500,height=600'); }}</script></head><body><div class="container mt-3"><h3>👤 {waiter['fullname']} የሽያጭ ዝርዝር</h3><table class="table table-bordered"><thead><tr><th>ቀን/ሰዓት</th><th>ጠረጴዛ</th><th class="text-end">ጠቅላላ</th><th>ድርጊት</th></tr></thead><tbody>{rows}<tr class="fw-bold"><td colspan="2" class="text-end">ጠቅላላ ድምር</td><td class="text-end">{grand_total:.2f} ብር</td><td></td></tr></tbody></table><button class="btn btn-secondary mt-2" onclick="window.close()">ዝጋ</button></div></body></html>''')

# ==================== አስተዳዳሪ ====================
@app.route('/owner/reports')
@login_required(role='owner')
def owner_reports():
    db = get_db()
    daily = db.execute("SELECT date(created_at) as day, SUM(total) as total FROM orders WHERE status='closed' GROUP BY date(created_at) ORDER BY day DESC LIMIT 7").fetchall()
    by_waiter = db.execute("SELECT u.fullname, COUNT(o.id) as order_count, SUM(o.total) as total FROM orders o JOIN users u ON o.waiter_id = u.id WHERE o.status='closed' GROUP BY u.id ORDER BY total DESC").fetchall()
    pending = db.execute("SELECT SUM(amount) as total FROM staff_expenses WHERE confirmed=0").fetchone()
    pending_total = pending['total'] if pending['total'] else 0
    daily_html = ''.join([f'<li class="list-group-item">{d["day"]} : {d["total"]} ብር</li>' for d in daily])
    waiter_html = ''.join([f'<li class="list-group-item">{w["fullname"]} : {w["total"]} ብር ({w["order_count"]} ትዕዛዝ)</li>' for w in by_waiter])
    return render_template_string(f'''<!DOCTYPE html><html><head><title>ሪፖርቶች</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="container mt-4"><h2>📊 ሪፖርቶች</h2><div class="row"><div class="col-md-6"><div class="card"><div class="card-header">የቀን ሽያጭ (ከ7 ቀን)</div><ul class="list-group">{daily_html}</ul></div></div><div class="col-md-6"><div class="card"><div class="card-header">በአስተናጋጅ ሽያጭ (ከፍተኛ ሻጭ በላይ)</div><ul class="list-group">{waiter_html}</ul></div><div class="card mt-3"><div class="card-header">ያልተረጋገጠ ወጪ</div><div class="card-body"><h3>{pending_total} ብር</h3></div></div></div></div></div></body></html>''')

@app.route('/owner/advanced_reports')
@login_required(role='owner')
def owner_advanced_reports():
    db = get_db()
    daily = db.execute("SELECT date(created_at) as day, SUM(total) as total FROM orders WHERE status='closed' AND date(created_at) = date('now') GROUP BY date(created_at)").fetchone()
    daily_total = daily['total'] if daily else 0
    weekly = db.execute("SELECT SUM(total) as total FROM orders WHERE status='closed' AND date(created_at) >= date('now', '-7 days')").fetchone()
    weekly_total = weekly['total'] if weekly['total'] else 0
    monthly = db.execute("SELECT SUM(total) as total FROM orders WHERE status='closed' AND date(created_at) >= date('now', '-30 days')").fetchone()
    monthly_total = monthly['total'] if monthly['total'] else 0
    top_products = db.execute("SELECT p.name, SUM(oi.quantity) as total_qty, SUM(oi.total_price) as total_revenue FROM order_items oi JOIN products p ON oi.product_id = p.id JOIN orders o ON oi.order_id = o.id WHERE o.status = 'closed' GROUP BY p.id ORDER BY total_revenue DESC LIMIT 5").fetchall()
    waiter_performance = db.execute("SELECT u.fullname, COUNT(o.id) as order_count, SUM(o.total) as total_sales, ROUND(AVG(o.total), 2) as avg_order_value FROM orders o JOIN users u ON o.waiter_id = u.id WHERE o.status = 'closed' GROUP BY u.id ORDER BY total_sales DESC").fetchall()
    db.close()
    top_products_html = ''.join([f'<li class="list-group-item">{p["name"]} - {p["total_qty"]} ቁጥር - {p["total_revenue"]} ብር</li>' for p in top_products])
    waiter_html = ''.join([f'<li class="list-group-item"><b>{w["fullname"]}</b> : {w["total_sales"]} ብር | {w["order_count"]} ትዕዛዝ | አማካይ {w["avg_order_value"]} ብር</li>' for w in waiter_performance])
    return render_template_string(f'''<!DOCTYPE html><html><head><title>የላቀ ሪፖርት</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="container mt-4"><h2>📈 የላቀ ሪፖርት</h2><div class="row"><div class="col-md-4"><div class="card text-white bg-primary mb-3"><div class="card-header">የዛሬ ሽያጭ</div><div class="card-body"><h3>{daily_total} ብር</h3></div></div></div><div class="col-md-4"><div class="card text-white bg-success mb-3"><div class="card-header">የሳምንት ሽያጭ</div><div class="card-body"><h3>{weekly_total} ብር</h3></div></div></div><div class="col-md-4"><div class="card text-white bg-info mb-3"><div class="card-header">የወር ሽያጭ</div><div class="card-body"><h3>{monthly_total} ብር</h3></div></div></div></div><div class="row"><div class="col-md-6"><div class="card"><div class="card-header">🏆 ከፍተኛ ሽያጭ ያላቸው ምርቶች (Top 5)</div><ul class="list-group">{top_products_html}</ul></div></div><div class="col-md-6"><div class="card"><div class="card-header">👨‍🍳 የዌተሮች አፈጻጸም</div><ul class="list-group">{waiter_html}</ul></div></div></div><div class="mt-3"><a href="{{ url_for('owner_reports') }}" class="btn btn-secondary">ወደ መሰረታዊ ሪፖርት ተመለስ</a></div></div></body></html>''')

@app.route('/owner/top_products')
@login_required(role='owner')
def owner_top_products():
    db = get_db()
    daily_top = db.execute("SELECT p.name, SUM(oi.quantity) as total_qty, SUM(oi.total_price) as revenue FROM order_items oi JOIN products p ON oi.product_id = p.id JOIN orders o ON oi.order_id = o.id WHERE o.status = 'closed' AND date(o.created_at) = date('now') GROUP BY p.id ORDER BY revenue DESC LIMIT 1").fetchone()
    weekly_top = db.execute("SELECT p.name, SUM(oi.quantity) as total_qty, SUM(oi.total_price) as revenue FROM order_items oi JOIN products p ON oi.product_id = p.id JOIN orders o ON oi.order_id = o.id WHERE o.status = 'closed' AND date(o.created_at) >= date('now', '-7 days') GROUP BY p.id ORDER BY revenue DESC LIMIT 1").fetchone()
    monthly_top = db.execute("SELECT p.name, SUM(oi.quantity) as total_qty, SUM(oi.total_price) as revenue FROM order_items oi JOIN products p ON oi.product_id = p.id JOIN orders o ON oi.order_id = o.id WHERE o.status = 'closed' AND date(o.created_at) >= date('now', '-30 days') GROUP BY p.id ORDER BY revenue DESC LIMIT 1").fetchone()
    yearly_top = db.execute("SELECT p.name, SUM(oi.quantity) as total_qty, SUM(oi.total_price) as revenue FROM order_items oi JOIN products p ON oi.product_id = p.id JOIN orders o ON oi.order_id = o.id WHERE o.status = 'closed' AND date(o.created_at) >= date('now', '-365 days') GROUP BY p.id ORDER BY revenue DESC LIMIT 1").fetchone()
    db.close()
    daily_info = f"{daily_top['name']} - {daily_top['total_qty']} ቁጥር - {daily_top['revenue']} ብር" if daily_top else "ምንም ሽያጭ የለም"
    weekly_info = f"{weekly_top['name']} - {weekly_top['total_qty']} ቁጥር - {weekly_top['revenue']} ብር" if weekly_top else "ምንም ሽያጭ የለም"
    monthly_info = f"{monthly_top['name']} - {monthly_top['total_qty']} ቁጥር - {monthly_top['revenue']} ብር" if monthly_top else "ምንም ሽያጭ የለም"
    yearly_info = f"{yearly_top['name']} - {yearly_top['total_qty']} ቁጥር - {yearly_top['revenue']} ብር" if yearly_top else "ምንም ሽያጭ የለም"
    return render_template_string(f'''<!DOCTYPE html><html><head><title>ከፍተኛ ሽያጭ ምርቶች</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="container mt-4"><h2>🏆 ከፍተኛ ሽያጭ ምርቶች ሪፖርት</h2><div class="row mt-4"><div class="col-md-3"><div class="card text-white bg-primary"><div class="card-header">የዛሬ ከፍተኛ ሽያጭ</div><div class="card-body"><h5>{daily_info}</h5></div></div></div><div class="col-md-3"><div class="card text-white bg-success"><div class="card-header">የሳምንቱ ከፍተኛ ሽያጭ</div><div class="card-body"><h5>{weekly_info}</h5></div></div></div><div class="col-md-3"><div class="card text-white bg-warning"><div class="card-header">የወሩ ከፍተኛ ሽያጭ</div><div class="card-body"><h5>{monthly_info}</h5></div></div></div><div class="col-md-3"><div class="card text-white bg-danger"><div class="card-header">የአመቱ ከፍተኛ ሽያጭ</div><div class="card-body"><h5>{yearly_info}</h5></div></div></div></div><div class="mt-4"><a href="{{ url_for('owner_advanced_reports') }}" class="btn btn-secondary">ወደ ላቀ ሪፖርት ተመለስ</a></div></div></body></html>''')

@app.route('/owner/products')
@login_required(role='owner')
def owner_products():
    db = get_db()
    products = db.execute("SELECT * FROM products").fetchall()
    db.close()
    products_rows = ''.join([f'<tr><td>{p["name"]}</td><td>{p["category"]}</td><td>{p["price"]}</td><td>{p["unit"]}</td></tr>' for p in products])
    return render_template_string(f'''<!DOCTYPE html><html><head><title>ምርቶች አስተዳደር</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="container mt-4"><h2>🍺 ምርቶች አስተዳደር</h2><table class="table table-bordered"><thead class="table-dark"><tr><th>ስም</th><th>ምድብ</th><th>ዋጋ</th><th>ክፍል</th></tr></thead><tbody>{products_rows}</tbody></table><button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addModal">+ አዲስ አገልግሎት ጨምር</button><div class="modal fade" id="addModal"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5>አዲስ አገልግሎት</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><input id="pname" placeholder="ስም" class="form-control mb-2"><input id="pcategory" placeholder="ምድብ" class="form-control mb-2"><input id="pprice" placeholder="ዋጋ" type="number" step="0.01" class="form-control mb-2"><input id="punit" placeholder="ክፍል" class="form-control mb-2"></div><div class="modal-footer"><button class="btn btn-primary" onclick="addProduct()">አስገባ</button></div></div></div></div></div><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script><script>function addProduct(){{ fetch('/api/add_product',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{name:document.getElementById('pname').value,category:document.getElementById('pcategory').value,price:document.getElementById('pprice').value,unit:document.getElementById('punit').value}})}}).then(()=>location.reload());}}</script></body></html>''')

@app.route('/api/add_product', methods=['POST'])
@login_required(role='owner')
def add_product():
    data = request.json
    db = get_db()
    db.execute("INSERT INTO products (name, category, price, unit) VALUES (?,?,?,?)", (data['name'], data['category'], data['price'], data['unit']))
    product_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("INSERT INTO inventory (product_id, quantity, min_stock, last_updated) VALUES (?, 0, 5, ?)", (product_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/owner/users')
@login_required(role='owner')
def owner_users():
    db = get_db()
    users = db.execute("SELECT id, username, fullname, role FROM users").fetchall()
    db.close()
    users_rows = ''.join([f'<tr><td>{u["fullname"]}</td><td>{u["username"]}</td><td>{u["role"]}</td></tr>' for u in users])
    return render_template_string(f'''<!DOCTYPE html><html><head><title>ሰራተኞች አስተዳደር</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head><body><nav class="navbar navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="{{ url_for('dashboard') }}">🍺 ሆቴል ሲስተም</a><div class="navbar-nav ms-auto"><span class="nav-link text-white">👋 {session['fullname']} ({session['role']})</span><a class="nav-link" href="{{ url_for('logout') }}">ውጣ</a></div></div></nav><div class="container mt-4"><h2>👥 ሰራተኞች አስተዳደር</h2><table class="table table-bordered"><thead class="table-dark"><tr><th>ሙሉ ስም</th><th>የተጠቃሚ ስም</th><th>ሚና</th></tr></thead><tbody>{users_rows}</tbody></table><button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addUserModal">+ አዲስ ሰራተኛ ጨምር</button><div class="modal fade" id="addUserModal"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5>አዲስ ሰራተኛ</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><input id="uname" placeholder="የተጠቃሚ ስም" class="form-control mb-2"><input id="pass" placeholder="ይሁንታ" type="password" class="form-control mb-2"><input id="fname" placeholder="ሙሉ ስም" class="form-control mb-2"><select id="role" class="form-control mb-2"><option value="waiter">አስተናጋጅ</option><option value="barman">ባርማን</option></select></div><div class="modal-footer"><button class="btn btn-primary" onclick="addUser()">አስገባ</button></div></div></div></div></div><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script><script>function addUser(){{ let u=document.getElementById('uname').value, p=document.getElementById('pass').value, f=document.getElementById('fname').value, r=document.getElementById('role').value; if(!u||!p||!f){{ alert('ሁሉንም ይሙሉ'); return; }} fetch('/api/add_user',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{username:u, password:p, fullname:f, role:r}})}}).then(()=>location.reload());}}</script></body></html>''')

@app.route('/api/add_user', methods=['POST'])
@login_required(role='owner')
def add_user():
    data = request.json
    hashed = hashlib.sha256(data['password'].encode()).hexdigest()
    db = get_db()
    try:
        db.execute("INSERT INTO users (username, password, role, fullname) VALUES (?, ?, ?, ?)", (data['username'], hashed, data['role'], data['fullname']))
        db.commit()
        db.close()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Username already exists'})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))