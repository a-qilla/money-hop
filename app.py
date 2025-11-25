from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import sqlite3
import hashlib
from datetime import datetime, date
import os
import json
import re
import secrets
from urllib.parse import urlencode
import requests
print(f"DEBUG: Railway Environment: {os.environ.get('RAILWAY_ENVIRONMENT')}")
print(f"DEBUG: DATABASE_URL: {'Exists' if os.environ.get('DATABASE_URL') else 'Not Found'}")

app = Flask(__name__)
app.secret_key = 'money-hop-secret-key-2024'
app.config['DATABASE'] = 'money_hop_full.db'

# Configuration - IMPORTANT FOR PRODUCTION
if os.environ.get('RAILWAY_ENVIRONMENT'):
    # Production environment (Railway)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'production-secret-key-change-this')
else:
    # Development environment
    app.config['SECRET_KEY'] = 'dev-key-change-in-production'

def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def get_db_connection():
    """Handle both SQLite and PostgreSQL"""
    try:
        if os.environ.get('RAILWAY_ENVIRONMENT'):
            # Use PostgreSQL on Railway
            try:
                import psycopg2
                DATABASE_URL = os.environ.get('DATABASE_URL')
                if DATABASE_URL:
                    # Convert postgres:// to postgresql:// for psycopg2
                    if DATABASE_URL.startswith('postgres://'):
                        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://')
                    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                    return conn
                else:
                    print("DATABASE_URL not found")
                    return None
            except ImportError:
                print("psycopg2 not available, falling back to SQLite")
                conn = sqlite3.connect('money_hop_full.db')  # Fixed: consistent database name
                conn.row_factory = sqlite3.Row
                return conn
        else:
            # Development - Use SQLite
            conn = sqlite3.connect('money_hop_full.db')
            conn.row_factory = sqlite3.Row
            return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def execute_query(query, params=(), fetch=False, commit=False):
    """Handle both SQLite and PostgreSQL"""
    try:
        if os.environ.get('RAILWAY_ENVIRONMENT'):
            # Use PostgreSQL on Railway - FIXED CONNECTION
            import psycopg2
            DATABASE_URL = os.environ.get('DATABASE_URL')
            
            if not DATABASE_URL:
                print("ERROR: DATABASE_URL environment variable not found!")
                return False
            
            # Connect menggunakan DATABASE_URL langsung
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = conn.cursor()
            
            # Convert SQLite ? to PostgreSQL %s jika perlu
            if '?' in query and '%s' not in query:
                query = query.replace('?', '%s')
            
            print(f"DEBUG: Executing query: {query} with params: {params}")
            cursor.execute(query, params)
            
            if commit:
                conn.commit()
                print("DEBUG: Commit successful")
                return True
            elif fetch:
                # For PostgreSQL, convert to dict-like structure
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    results = cursor.fetchall()
                    print(f"DEBUG: Fetch results: {results}")
                    return [dict(zip(columns, row)) for row in results]
                else:
                    return []
            else:
                return True
                
        else:
            # Use SQLite for development
            conn = sqlite3.connect('money_hop_full.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if commit:
                conn.commit()
                return True
            elif fetch:
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                return True
                
    except Exception as e:
        print(f"Database error in execute_query: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def hash_pw(password):
    """Hash password dengan salt"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Initialize database tables"""
    print("DEBUG: Initializing database...")
    try:
        if os.environ.get('RAILWAY_ENVIRONMENT'):
            # PostgreSQL table definitions
            execute_query('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE,
                    password VARCHAR(100),
                    google_id VARCHAR(100) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(20) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    normal_balance VARCHAR(10) NOT NULL
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS journals (
                    id SERIAL PRIMARY KEY,
                    entry_no VARCHAR(50) UNIQUE NOT NULL,
                    date DATE NOT NULL,
                    description TEXT NOT NULL,
                    user_id INTEGER NOT NULL
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS journal_details (
                    id SERIAL PRIMARY KEY,
                    journal_id INTEGER NOT NULL,
                    account_code VARCHAR(20) NOT NULL,
                    debit DECIMAL(15,2) DEFAULT 0,
                    credit DECIMAL(15,2) DEFAULT 0
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(20) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    qty INTEGER DEFAULT 0,
                    price DECIMAL(15,2) DEFAULT 0,
                    user_id INTEGER NOT NULL
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS cash_payments (
                    id SERIAL PRIMARY KEY,
                    payment_no VARCHAR(50) UNIQUE NOT NULL,
                    date DATE NOT NULL,
                    description TEXT NOT NULL,
                    account_code VARCHAR(20) NOT NULL,
                    amount DECIMAL(15,2) DEFAULT 0,
                    user_id INTEGER NOT NULL
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS cash_receipts (
                    id SERIAL PRIMARY KEY,
                    receipt_no VARCHAR(50) UNIQUE NOT NULL,
                    date DATE NOT NULL,
                    description TEXT NOT NULL,
                    account_code VARCHAR(20) NOT NULL,
                    amount DECIMAL(15,2) DEFAULT 0,
                    user_id INTEGER NOT NULL
                )
            ''', commit=True)
            
        else:
            # SQLite table definitions
            execute_query('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password TEXT,
                    google_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    normal_balance TEXT NOT NULL
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS journals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_no TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS journal_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    journal_id INTEGER NOT NULL,
                    account_code TEXT NOT NULL,
                    debit REAL DEFAULT 0,
                    credit REAL DEFAULT 0,
                    FOREIGN KEY (journal_id) REFERENCES journals(id)
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    qty INTEGER DEFAULT 0,
                    price REAL DEFAULT 0,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS cash_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payment_no TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    account_code TEXT NOT NULL,
                    amount REAL DEFAULT 0,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY (account_code) REFERENCES accounts(code),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''', commit=True)
            
            execute_query('''
                CREATE TABLE IF NOT EXISTS cash_receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_no TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    account_code TEXT NOT NULL,
                    amount REAL DEFAULT 0,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY (account_code) REFERENCES accounts(code),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''', commit=True)
        
        # Seed accounts if empty
        accounts_count = execute_query("SELECT COUNT(*) FROM accounts", fetch=True)
        if accounts_count and accounts_count[0]['count'] == 0:
            accounts = [
                ('1-1000', 'Kas', 'Asset', 'Debit'),
                ('1-1100', 'Bank', 'Asset', 'Debit'),
                ('1-1200', 'Piutang Usaha', 'Asset', 'Debit'),
                ('1-1300', 'Persediaan', 'Asset', 'Debit'),
                ('2-2000', 'Hutang Usaha', 'Liability', 'Credit'),
                ('2-2100', 'Hutang Bank', 'Liability', 'Credit'),
                ('3-3000', 'Modal', 'Equity', 'Credit'),
                ('3-3100', 'Laba Ditahan', 'Equity', 'Credit'),
                ('4-4000', 'Pendapatan Jasa', 'Revenue', 'Credit'),
                ('4-4100', 'Pendapatan Lain', 'Revenue', 'Credit'),
                ('5-5000', 'Beban Gaji', 'Expense', 'Debit'),
                ('5-5100', 'Beban Sewa', 'Expense', 'Debit'),
                ('5-5200', 'Beban Listrik', 'Expense', 'Debit'),
                ('5-5300', 'Beban Perlengkapan', 'Expense', 'Debit'),
            ]
            
            for account in accounts:
                execute_query(
                    "INSERT INTO accounts (code, name, type, normal_balance) VALUES (?, ?, ?, ?)",
                    account,
                    commit=True
                )
        
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")

# Panggil init_db saat app start
init_db()

# ============ HELPER FUNCTIONS ============
def hash_pw(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def money_format(amount):
    """Format amount to Indonesian Rupiah"""
    try:
        return f"Rp {float(amount):,.0f}".replace(',', '.')
    except:
        return "Rp 0"

def safe_float(value):
    """Safely convert to float"""
    try:
        return float(value) if value else 0.0
    except:
        return 0.0

def safe_int(value):
    """Safely convert to integer"""
    try:
        return int(value) if value else 0
    except:
        return 0

def is_valid_email(email):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_account_balance(account_code):
    """Get account balance using universal query executor"""
    try:
        # Get debit and credit totals
        result = execute_query("""
            SELECT COALESCE(SUM(debit),0) as total_debit, COALESCE(SUM(credit),0) as total_credit 
            FROM journal_details jd
            JOIN journals j ON jd.journal_id = j.id
            WHERE jd.account_code = %s AND j.user_id = %s
        """, (account_code, session.get('user_id', 1)), fetch=True)
        
        if result and len(result) > 0:
            debit_total = result[0].get('total_debit', 0) or 0
            credit_total = result[0].get('total_credit', 0) or 0
        else:
            debit_total = credit_total = 0
        
        # Get account normal balance
        account_result = execute_query(
            "SELECT normal_balance FROM accounts WHERE code = %s", 
            (account_code,), 
            fetch=True
        )
        
        if account_result and len(account_result) > 0:
            normal_balance = account_result[0].get('normal_balance', 'Debit')
            if normal_balance == 'Debit':
                balance = debit_total - credit_total
            else:
                balance = credit_total - debit_total
            return float(balance or 0)
        return 0.0
        
    except Exception as e:
        print(f"Error calculating balance: {e}")
        return 0.0
# ============ JINJA2 FILTERS ============
@app.template_filter('money_format')
def money_format_filter(amount):
    """Jinja2 filter for money formatting"""
    return money_format(amount)

@app.context_processor
def utility_processor():
    """Make functions available to all templates"""
    return {
        'money_format': money_format,
        'get_account_balance': get_account_balance,
        'safe_float': safe_float,
        'safe_int': safe_int
    }
# ============ ROUTES ============
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form['login_input']
        password = request.form['password']
        hashed_password = hash_pw(password)
        
        try:
            # Cari user by email atau username
            if '@' in login_input:
                # Login dengan email
                users = execute_query(
                    "SELECT * FROM users WHERE email = ? AND password = ?", 
                    (login_input, hashed_password), 
                    fetch=True
                )
            else:
                # Login dengan username
                users = execute_query(
                    "SELECT * FROM users WHERE username = ? AND password = ?", 
                    (login_input, hashed_password), 
                    fetch=True
                )
            
            if users and len(users) > 0:
                user = users[0]
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['email'] = user.get('email', '')
                flash('Login berhasil!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Email/Username atau password salah!', 'error')
                
        except Exception as e:
            print(f"Login error: {e}")
            flash('Terjadi error saat login', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        print(f"DEBUG: Registration attempt - Username: {username}, Email: {email}")
        
        # Validasi input
        if not username or not email or not password:
            flash('Mohon isi semua field!', 'error')
            return render_template('register.html')
        
        if not is_valid_email(email):
            flash('Format email tidak valid!', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Password tidak sama!', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password minimal 6 karakter!', 'error')
            return render_template('register.html')
        
        try:
            # Check if username or email already exists
            print("DEBUG: Checking existing users...")
            existing_users = execute_query(
                "SELECT * FROM users WHERE username = ? OR email = ?", 
                (username, email), 
                fetch=True
            )
            
            print(f"DEBUG: Existing users result: {existing_users}")
            
            if existing_users and len(existing_users) > 0:
                existing_user = existing_users[0]
                if existing_user['username'] == username:
                    flash('Username sudah digunakan!', 'error')
                else:
                    flash('Email sudah digunakan!', 'error')
                return render_template('register.html')
            
            # Hash password sebelum simpan
            print("DEBUG: Hashing password...")
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            # Insert new user
            print("DEBUG: Inserting new user...")
            success = execute_query(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                (username, email, hashed_password),
                commit=True
            )
            
            print(f"DEBUG: Insert success: {success}")
            
            if success:
                flash('Registrasi berhasil! Silakan login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Error saat registrasi!', 'error')
                
        except Exception as e:
            print(f"Registration error: {e}")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            flash('Terjadi error saat registrasi!', 'error')
    
    return render_template('register.html')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get revenue total
    revenue_results = execute_query("""
        SELECT IFNULL(SUM(jd.credit - jd.debit),0) as total
        FROM journal_details jd
        JOIN journals j ON jd.journal_id = j.id
        JOIN accounts a ON jd.account_code = a.code
        WHERE a.type = 'Revenue' AND j.user_id = ?
    """, (session['user_id'],), fetch=True)
    
    revenue = revenue_results[0]['total'] if revenue_results and len(revenue_results) > 0 else 0
    
    # Get expense total
    expense_results = execute_query("""
        SELECT IFNULL(SUM(jd.debit - jd.credit),0) as total
        FROM journal_details jd
        JOIN journals j ON jd.journal_id = j.id
        JOIN accounts a ON jd.account_code = a.code
        WHERE a.type = 'Expense' AND j.user_id = ?
    """, (session['user_id'],), fetch=True)
    
    expense = expense_results[0]['total'] if expense_results and len(expense_results) > 0 else 0
    
    profit = revenue - expense
    
    if revenue == 0 and expense == 0:
        revenue = 12500000
        expense = 4500000
        profit = revenue - expense
    
    return render_template('dashboard.html', 
                         revenue=money_format(revenue),
                         expense=money_format(expense),
                         profit=money_format(profit))

@app.route('/coa')
def coa():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    accounts = execute_query(
        "SELECT code, name, type, normal_balance FROM accounts ORDER BY code", 
        fetch=True
    )
    
    return render_template('coa.html', accounts=accounts)

@app.route('/journal', methods=['GET', 'POST'])
def journal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        entry_no = request.form['entry_no']
        date = request.form['date']
        description = request.form['description']
        accounts = request.form.getlist('account_code[]')
        debits = request.form.getlist('debit[]')
        credits = request.form.getlist('credit[]')
        
        total_debit = sum(safe_float(debit) for debit in debits)
        total_credit = sum(safe_float(credit) for credit in credits)
        
        if abs(total_debit - total_credit) > 0.01:
            flash('Total debit dan kredit harus seimbang!', 'error')
            return redirect(url_for('journal'))
        
        try:
            # Insert journal header
            journal_success = execute_query(
                "INSERT INTO journals (entry_no, date, description, user_id) VALUES (?, ?, ?, ?)",
                (entry_no, date, description, session['user_id']),
                commit=False  # We'll commit after details
            )
            
            if not journal_success:
                flash('Error menyimpan jurnal!', 'error')
                return redirect(url_for('journal'))
            
            # Get the last inserted journal ID
            journal_results = execute_query(
                "SELECT id FROM journals WHERE entry_no = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
                (entry_no, session['user_id']),
                fetch=True
            )
            
            if not journal_results or len(journal_results) == 0:
                flash('Error mendapatkan ID jurnal!', 'error')
                return redirect(url_for('journal'))
            
            journal_id = journal_results[0]['id']
            
            # Insert journal details
            for i, account_code in enumerate(accounts):
                if account_code:
                    detail_success = execute_query(
                        "INSERT INTO journal_details (journal_id, account_code, debit, credit) VALUES (?, ?, ?, ?)",
                        (journal_id, account_code, safe_float(debits[i]), safe_float(credits[i])),
                        commit=False
                    )
                    if not detail_success:
                        flash('Error menyimpan detail jurnal!', 'error')
                        return redirect(url_for('journal'))
            
            # Commit all transactions
            commit_success = execute_query("COMMIT", commit=True)
            if commit_success:
                flash('Jurnal berhasil disimpan!', 'success')
            else:
                flash('Error commit transaksi!', 'error')
                
        except Exception as e:
            # Rollback on error
            execute_query("ROLLBACK", commit=True)
            if 'UNIQUE' in str(e) or 'IntegrityError' in str(e):
                flash('Nomor entri sudah ada!', 'error')
            else:
                flash(f'Error: {str(e)}', 'error')
    
    # Get accounts for dropdown
    accounts = execute_query(
        "SELECT code, name FROM accounts ORDER BY code", 
        fetch=True
    )
    
    # Get journal count
    journal_count_results = execute_query(
        "SELECT COUNT(*) as count FROM journals WHERE user_id = ?", 
        (session['user_id'],), 
        fetch=True
    )
    journal_count = journal_count_results[0]['count'] if journal_count_results and len(journal_count_results) > 0 else 0
    
    # Get recent journals
    journals = execute_query("""
        SELECT j.entry_no, j.date, j.description, 
               GROUP_CONCAT(a.name || ' (D: ' || jd.debit || ', C: ' || jd.credit || ')') as details
        FROM journals j
        LEFT JOIN journal_details jd ON j.id = jd.journal_id
        LEFT JOIN accounts a ON jd.account_code = a.code
        WHERE j.user_id = ?
        GROUP BY j.id
        ORDER BY j.date DESC, j.entry_no DESC
        LIMIT 50
    """, (session['user_id'],), fetch=True)
    
    return render_template('journal.html', 
                         accounts=accounts,
                         journal_count=journal_count,
                         today=datetime.now().strftime('%Y-%m-%d'),
                         journals=journals)

@app.route('/add_account', methods=['GET', 'POST'])
def add_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        account_type = request.form['type']
        normal_balance = request.form['normal_balance']
        
        if not code or not name or not account_type or not normal_balance:
            flash('Mohon isi semua field!', 'error')
            return redirect(url_for('add_account'))
        
        if not re.match(r'^\d+-\d+$', code):
            flash('Format kode akun harus: angka-angka (contoh: 1-1000, 5-5100)', 'error')
            return redirect(url_for('add_account'))
        
        try:
            # Check if account code already exists
            existing_accounts = execute_query(
                "SELECT code FROM accounts WHERE code = ?", 
                (code,), 
                fetch=True
            )
            
            if existing_accounts and len(existing_accounts) > 0:
                flash('Kode akun sudah ada!', 'error')
                return redirect(url_for('add_account'))
            
            # Insert new account
            success = execute_query(
                "INSERT INTO accounts (code, name, type, normal_balance) VALUES (?, ?, ?, ?)",
                (code, name, account_type, normal_balance),
                commit=True
            )
            
            if success:
                flash('Akun berhasil ditambahkan!', 'success')
                return redirect(url_for('coa'))
            else:
                flash('Error menambahkan akun!', 'error')
                
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('add_account.html')

# ============ ADJUSTING JOURNAL ENTRIES ============
@app.route('/adjusting_entries', methods=['GET', 'POST'])
def adjusting_entries():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        entry_no = request.form['entry_no']
        date = request.form['date']
        description = request.form['description']
        accounts = request.form.getlist('account_code[]')
        debits = request.form.getlist('debit[]')
        credits = request.form.getlist('credit[]')
        adjustment_type = request.form['adjustment_type']
        
        # Validasi debit = kredit
        total_debit = sum(safe_float(debit) for debit in debits)
        total_credit = sum(safe_float(credit) for credit in credits)
        
        if abs(total_debit - total_credit) > 0.01:
            flash('Total debit dan kredit harus seimbang!', 'error')
            return redirect(url_for('adjusting_entries'))
        
        try:
            # Insert adjusting journal header
            journal_success = execute_query(
                "INSERT INTO journals (entry_no, date, description, user_id) VALUES (?, ?, ?, ?)",
                (entry_no, date, f"[PENYESUAIAN] {description}", session['user_id']),
                commit=False
            )
            
            if not journal_success:
                flash('Error menyimpan jurnal penyesuaian!', 'error')
                return redirect(url_for('adjusting_entries'))
            
            # Get the last inserted journal ID
            journal_results = execute_query(
                "SELECT id FROM journals WHERE entry_no = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
                (entry_no, session['user_id']),
                fetch=True
            )
            
            if not journal_results or len(journal_results) == 0:
                flash('Error mendapatkan ID jurnal!', 'error')
                return redirect(url_for('adjusting_entries'))
            
            journal_id = journal_results[0]['id']
            
            # Insert journal details
            for i, account_code in enumerate(accounts):
                if account_code:  # Skip empty accounts
                    detail_success = execute_query(
                        "INSERT INTO journal_details (journal_id, account_code, debit, credit) VALUES (?, ?, ?, ?)",
                        (journal_id, account_code, safe_float(debits[i]), safe_float(credits[i])),
                        commit=False
                    )
                    if not detail_success:
                        flash('Error menyimpan detail jurnal!', 'error')
                        return redirect(url_for('adjusting_entries'))
            
            # Insert adjustment record
            adjustment_success = execute_query(
                "INSERT INTO adjustments (date, description, account_code, debit, credit, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                (date, description, accounts[0] if accounts else '', safe_float(debits[0]), safe_float(credits[0]), session['user_id']),
                commit=False
            )
            
            if not adjustment_success:
                flash('Error menyimpan data penyesuaian!', 'error')
                return redirect(url_for('adjusting_entries'))
            
            # Commit all transactions
            commit_success = execute_query("COMMIT", commit=True)
            if commit_success:
                flash('Jurnal Penyesuaian berhasil disimpan!', 'success')
            else:
                flash('Error commit transaksi!', 'error')
                
        except Exception as e:
            # Rollback on error
            execute_query("ROLLBACK", commit=True)
            if 'UNIQUE' in str(e) or 'IntegrityError' in str(e):
                flash('Nomor entri sudah ada!', 'error')
            else:
                flash(f'Error: {str(e)}', 'error')
    
    # GET accounts untuk dropdown
    accounts = execute_query(
        "SELECT code, name FROM accounts ORDER BY code", 
        fetch=True
    )

    # Get adjusting entries count for auto-numbering
    adjusting_count_results = execute_query(
        "SELECT COUNT(*) as count FROM journals WHERE user_id = ? AND description LIKE '[PENYESUAIAN]%'", 
        (session['user_id'],), 
        fetch=True
    )
    adjusting_count = adjusting_count_results[0]['count'] if adjusting_count_results and len(adjusting_count_results) > 0 else 0

    # Get adjusting entries history
    adjusting_entries = execute_query("""
        SELECT j.entry_no, j.date, j.description, 
               GROUP_CONCAT(a.name || ' (D: ' || jd.debit || ', C: ' || jd.credit || ')') as details
        FROM journals j
        LEFT JOIN journal_details jd ON j.id = jd.journal_id
        LEFT JOIN accounts a ON jd.account_code = a.code
        WHERE j.user_id = ? AND j.description LIKE '[PENYESUAIAN]%'
        GROUP BY j.id
        ORDER BY j.date DESC, j.entry_no DESC
        LIMIT 50
    """, (session['user_id'],), fetch=True)
    
    return render_template('adjusting_entries.html', 
                         accounts=accounts,
                         adjusting_count=adjusting_count,
                         today=datetime.now().strftime('%Y-%m-%d'),
                         adjusting_entries=adjusting_entries)

# ============ CLOSING JOURNAL ENTRIES ============
@app.route('/closing_entries', methods=['GET', 'POST'])
def closing_entries():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Get period (month and year)
        period = request.form['period']
        
        try:
            # Calculate revenue and expense totals
            revenue_results = execute_query("""
                SELECT a.code, a.name, 
                       COALESCE(SUM(jd.credit - jd.debit), 0) as balance
                FROM accounts a
                LEFT JOIN journal_details jd ON a.code = jd.account_code
                LEFT JOIN journals j ON jd.journal_id = j.id
                WHERE a.type = 'Revenue' AND j.user_id = ?
                GROUP BY a.code
            """, (session['user_id'],), fetch=True)
            
            expense_results = execute_query("""
                SELECT a.code, a.name, 
                       COALESCE(SUM(jd.debit - jd.credit), 0) as balance
                FROM accounts a
                LEFT JOIN journal_details jd ON a.code = jd.account_code
                LEFT JOIN journals j ON jd.journal_id = j.id
                WHERE a.type = 'Expense' AND j.user_id = ?
                GROUP BY a.code
            """, (session['user_id'],), fetch=True)
            
            revenues = revenue_results if revenue_results else []
            expenses = expense_results if expense_results else []
            
            total_revenue = sum(row['balance'] for row in revenues)
            total_expense = sum(row['balance'] for row in expenses)
            net_income = total_revenue - total_expense
            
            # Create closing entries
            closing_date = datetime.now().strftime('%Y-%m-%d')
            closing_description = f"Jurnal Penutup Periode {period}"
            
            # 1. Close Revenue accounts to Income Summary
            if total_revenue > 0:
                # Insert closing journal header for revenue
                journal_success = execute_query(
                    "INSERT INTO journals (entry_no, date, description, user_id) VALUES (?, ?, ?, ?)",
                    (f"CL{period}", closing_date, f"[PENUTUP] {closing_description}", session['user_id']),
                    commit=False
                )
                
                if not journal_success:
                    flash('Error membuat jurnal penutup revenue!', 'error')
                    return redirect(url_for('closing_entries'))
                
                # Get the journal ID
                journal_results = execute_query(
                    "SELECT id FROM journals WHERE entry_no = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
                    (f"CL{period}", session['user_id']),
                    fetch=True
                )
                
                if not journal_results or len(journal_results) == 0:
                    flash('Error mendapatkan ID jurnal!', 'error')
                    return redirect(url_for('closing_entries'))
                
                journal_id = journal_results[0]['id']
                
                # Debit Revenue accounts, Credit Income Summary
                for revenue in revenues:
                    if revenue['balance'] > 0:
                        detail_success = execute_query(
                            "INSERT INTO journal_details (journal_id, account_code, debit, credit) VALUES (?, ?, ?, ?)",
                            (journal_id, revenue['code'], revenue['balance'], 0),
                            commit=False
                        )
                        if not detail_success:
                            flash('Error menyimpan detail jurnal revenue!', 'error')
                            return redirect(url_for('closing_entries'))
                
                # Credit Income Summary for total revenue
                income_summary_success = execute_query(
                    "INSERT INTO journal_details (journal_id, account_code, debit, credit) VALUES (?, ?, ?, ?)",
                    (journal_id, '3-3200', 0, total_revenue),
                    commit=False
                )
                if not income_summary_success:
                    flash('Error menyimpan income summary!', 'error')
                    return redirect(url_for('closing_entries'))
            
            # 2. Close Expense accounts to Income Summary
            if total_expense > 0:
                # Insert closing journal header for expenses
                journal_success = execute_query(
                    "INSERT INTO journals (entry_no, date, description, user_id) VALUES (?, ?, ?, ?)",
                    (f"CL{period}-EXP", closing_date, f"[PENUTUP] {closing_description} - Beban", session['user_id']),
                    commit=False
                )
                
                if not journal_success:
                    flash('Error membuat jurnal penutup expense!', 'error')
                    return redirect(url_for('closing_entries'))
                
                # Get the journal ID
                journal_results = execute_query(
                    "SELECT id FROM journals WHERE entry_no = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
                    (f"CL{period}-EXP", session['user_id']),
                    fetch=True
                )
                
                if not journal_results or len(journal_results) == 0:
                    flash('Error mendapatkan ID jurnal expense!', 'error')
                    return redirect(url_for('closing_entries'))
                
                journal_id_exp = journal_results[0]['id']
                
                # Credit Expense accounts, Debit Income Summary
                for expense in expenses:
                    if expense['balance'] > 0:
                        detail_success = execute_query(
                            "INSERT INTO journal_details (journal_id, account_code, debit, credit) VALUES (?, ?, ?, ?)",
                            (journal_id_exp, expense['code'], 0, expense['balance']),
                            commit=False
                        )
                        if not detail_success:
                            flash('Error menyimpan detail jurnal expense!', 'error')
                            return redirect(url_for('closing_entries'))
                
                # Debit Income Summary for total expenses
                income_summary_success = execute_query(
                    "INSERT INTO journal_details (journal_id, account_code, debit, credit) VALUES (?, ?, ?, ?)",
                    (journal_id_exp, '3-3200', total_expense, 0),
                    commit=False
                )
                if not income_summary_success:
                    flash('Error menyimpan income summary expense!', 'error')
                    return redirect(url_for('closing_entries'))
            
            # 3. Close Income Summary to Retained Earnings
            if net_income != 0:
                # Insert closing journal header for income summary
                journal_success = execute_query(
                    "INSERT INTO journals (entry_no, date, description, user_id) VALUES (?, ?, ?, ?)",
                    (f"CL{period}-INC", closing_date, f"[PENUTUP] {closing_description} - Laba", session['user_id']),
                    commit=False
                )
                
                if not journal_success:
                    flash('Error membuat jurnal penutup income summary!', 'error')
                    return redirect(url_for('closing_entries'))
                
                # Get the journal ID
                journal_results = execute_query(
                    "SELECT id FROM journals WHERE entry_no = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
                    (f"CL{period}-INC", session['user_id']),
                    fetch=True
                )
                
                if not journal_results or len(journal_results) == 0:
                    flash('Error mendapatkan ID jurnal income summary!', 'error')
                    return redirect(url_for('closing_entries'))
                
                journal_id_inc = journal_results[0]['id']
                
                if net_income > 0:
                    # Debit Income Summary, Credit Retained Earnings (Profit)
                    debit_success = execute_query(
                        "INSERT INTO journal_details (journal_id, account_code, debit, credit) VALUES (?, ?, ?, ?)",
                        (journal_id_inc, '3-3200', net_income, 0),
                        commit=False
                    )
                    credit_success = execute_query(
                        "INSERT INTO journal_details (journal_id, account_code, debit, credit) VALUES (?, ?, ?, ?)",
                        (journal_id_inc, '3-3100', 0, net_income),
                        commit=False
                    )
                    if not debit_success or not credit_success:
                        flash('Error menyimpan jurnal laba!', 'error')
                        return redirect(url_for('closing_entries'))
                else:
                    # Credit Income Summary, Debit Retained Earnings (Loss)
                    credit_success = execute_query(
                        "INSERT INTO journal_details (journal_id, account_code, debit, credit) VALUES (?, ?, ?, ?)",
                        (journal_id_inc, '3-3200', 0, abs(net_income)),
                        commit=False
                    )
                    debit_success = execute_query(
                        "INSERT INTO journal_details (journal_id, account_code, debit, credit) VALUES (?, ?, ?, ?)",
                        (journal_id_inc, '3-3100', abs(net_income), 0),
                        commit=False
                    )
                    if not debit_success or not credit_success:
                        flash('Error menyimpan jurnal rugi!', 'error')
                        return redirect(url_for('closing_entries'))
            
            # Commit all transactions
            commit_success = execute_query("COMMIT", commit=True)
            if commit_success:
                flash(f'Jurnal Penutup untuk periode {period} berhasil dibuat!', 'success')
            else:
                flash('Error commit transaksi penutup!', 'error')
            
        except Exception as e:
            # Rollback on error
            execute_query("ROLLBACK", commit=True)
            flash(f'Error: {str(e)}', 'error')
    
    # Get closing entries history
    closing_entries = execute_query("""
        SELECT j.entry_no, j.date, j.description, 
               GROUP_CONCAT(a.name || ' (D: ' || jd.debit || ', C: ' || jd.credit || ')') as details
        FROM journals j
        LEFT JOIN journal_details jd ON j.id = jd.journal_id
        LEFT JOIN accounts a ON jd.account_code = a.code
        WHERE j.user_id = ? AND j.description LIKE '[PENUTUP]%'
        GROUP BY j.id
        ORDER BY j.date DESC, j.entry_no DESC
        LIMIT 50
    """, (session['user_id'],), fetch=True)
    
    # Get current period
    current_period = datetime.now().strftime('%Y-%m')
    
    return render_template('closing_entries.html',
                         current_period=current_period,
                         closing_entries=closing_entries)

# ============ UPDATE DATABASE SCHEMA ============
# Update your init_db() function to include adjustments table
def init_db():
    # Users table
    execute_query('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''', commit=True)
    
    # Accounts table (Chart of Accounts)
    execute_query('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(50) NOT NULL,
            normal_balance VARCHAR(10) NOT NULL,
            balance DECIMAL(15,2) DEFAULT 0,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''', commit=True)
    
    # Journals table
    execute_query('''
        CREATE TABLE IF NOT EXISTS journals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_no VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            description TEXT,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(entry_no, user_id)
        )
    ''', commit=True)
    
    # Journal Details table
    execute_query('''
        CREATE TABLE IF NOT EXISTS journal_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_id INTEGER NOT NULL,
            account_code VARCHAR(20) NOT NULL,
            debit DECIMAL(15,2) DEFAULT 0,
            credit DECIMAL(15,2) DEFAULT 0,
            FOREIGN KEY (journal_id) REFERENCES journals(id),
            FOREIGN KEY (account_code) REFERENCES accounts(code)
        )
    ''', commit=True)
    
    # Adjustments table
    execute_query('''
        CREATE TABLE IF NOT EXISTS adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            account_code TEXT NOT NULL,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (account_code) REFERENCES accounts(code),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''', commit=True)
    
    # Add Income Summary account if it doesn't exist
    income_summary_results = execute_query(
        "SELECT COUNT(*) as count FROM accounts WHERE code = '3-3200'", 
        fetch=True
    )
    
    if income_summary_results and income_summary_results[0]['count'] == 0:
        execute_query(
            "INSERT INTO accounts (code, name, type, normal_balance) VALUES (?, ?, ?, ?)",
            ('3-3200', 'Ikhtisar Laba Rugi', 'Equity', 'Credit'),
            commit=True
        )
    
    print("Database initialized successfully!")
    
# ============ TRIAL BALANCE ============
@app.route('/trial_balance')
def trial_balance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get all accounts with their balances
    accounts_data = execute_query(
        "SELECT code, name, type, normal_balance FROM accounts ORDER BY code", 
        fetch=True
    )
    
    accounts = []
    total_debit = 0
    total_credit = 0
    
    if accounts_data:
        for account in accounts_data:
            balance = get_account_balance(account['code'])
            
            # Determine debit/credit based on account type and normal balance
            if account['normal_balance'] == 'Debit':  # Asset & Expense
                debit = balance if balance >= 0 else 0
                credit = abs(balance) if balance < 0 else 0
            else:  # Liability, Equity, Revenue (Credit normal balance)
                debit = abs(balance) if balance < 0 else 0
                credit = balance if balance >= 0 else 0
            
            accounts.append({
                'code': account['code'],
                'name': account['name'],
                'type': account['type'],
                'debit': debit,
                'credit': credit
            })
            
            total_debit += debit
            total_credit += credit
    
    return render_template('trial_balance.html',
                         accounts=accounts,
                         total_debit=total_debit,
                         total_credit=total_credit)

# ============ ADJUSTED TRIAL BALANCE ============
@app.route('/adjusted_trial_balance')
def adjusted_trial_balance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get all accounts with their balances (including adjustments)
        accounts_data = execute_query(
            "SELECT code, name, type, normal_balance FROM accounts ORDER BY code", 
            fetch=True
        )
        
        accounts = []
        total_debit = 0
        total_credit = 0
        
        if accounts_data:
            for account in accounts_data:
                balance = get_account_balance(account['code'])
                
                # Determine debit/credit based on account type and normal balance
                if account['normal_balance'] == 'Debit':  # Asset & Expense
                    debit = balance if balance >= 0 else 0
                    credit = abs(balance) if balance < 0 else 0
                else:  # Liability, Equity, Revenue (Credit normal balance)
                    debit = abs(balance) if balance < 0 else 0
                    credit = balance if balance >= 0 else 0
                
                accounts.append({
                    'code': account['code'],
                    'name': account['name'],
                    'type': account['type'],
                    'debit': debit,
                    'credit': credit
                })
                
                total_debit += debit
                total_credit += credit
        
        return render_template('adjusted_trial_balance.html',
                             accounts=accounts,
                             total_debit=total_debit,
                             total_credit=total_credit)
                             
    except Exception as e:
        print(f"Adjusted trial balance error: {e}")
        flash('Error loading trial balance', 'error')
        return redirect(url_for('dashboard'))

@app.route('/cash_payment', methods=['GET', 'POST'])
def cash_payment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        payment_no = request.form['payment_no']
        date = request.form['date']
        description = request.form['description']
        account_code = request.form['account_code']
        amount = safe_float(request.form['amount'])
        
        if not payment_no or not date or not description or not account_code or amount <= 0:
            flash('Mohon isi semua field dengan benar!', 'error')
            return redirect(url_for('cash_payment'))
        
        try:
            # Insert cash payment
            success = execute_query("""
                INSERT INTO cash_payments (payment_no, date, description, account_code, amount, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (payment_no, date, description, account_code, amount, session['user_id']), commit=True)
            
            if not success:
                flash('Gagal mencatat cash payment!', 'error')
                return redirect(url_for('cash_payment'))
            
            journal_entry_no = f"CP{payment_no}"
            
            # Insert journal entry
            journal_success = execute_query("""
                INSERT INTO journals (entry_no, date, description, user_id)
                VALUES (%s, %s, %s, %s)
            """, (journal_entry_no, date, f"Cash Payment: {description}", session['user_id']), commit=True)
            
            if not journal_success:
                flash('Gagal mencatat journal entry!', 'error')
                return redirect(url_for('cash_payment'))
            
            # Get the last inserted journal ID
            journal_result = execute_query(
                "SELECT id FROM journals WHERE entry_no = %s AND user_id = %s ORDER BY id DESC LIMIT 1",
                (journal_entry_no, session['user_id']), 
                fetch=True
            )
            
            if not journal_result or len(journal_result) == 0:
                flash('Gagal mendapatkan journal ID!', 'error')
                return redirect(url_for('cash_payment'))
            
            journal_id = journal_result[0]['id']
            
            # Insert journal details (Kas credit)
            execute_query("""
                INSERT INTO journal_details (journal_id, account_code, debit, credit)
                VALUES (%s, %s, %s, %s)
            """, (journal_id, '1-1000', 0, amount), commit=True)
            
            # Insert journal details (Account debit)
            execute_query("""
                INSERT INTO journal_details (journal_id, account_code, debit, credit)
                VALUES (%s, %s, %s, %s)
            """, (journal_id, account_code, amount, 0), commit=True)
            
            flash('Cash Payment berhasil dicatat!', 'success')
            
        except Exception as e:
            print(f"Cash payment error: {e}")
            flash(f'Error: {str(e)}', 'error')
    
    # Get accounts for dropdown
    accounts = execute_query(
        "SELECT code, name FROM accounts WHERE type IN ('Expense', 'Asset') AND code != '1-1000' ORDER BY code",
        fetch=True
    )
    
    # Get payment count
    payment_count_result = execute_query(
        "SELECT COUNT(*) as count FROM cash_payments WHERE user_id = %s",
        (session['user_id'],),
        fetch=True
    )
    payment_count = payment_count_result[0]['count'] if payment_count_result else 0
    
    # Get recent payments
    payments = execute_query("""
        SELECT cp.payment_no, cp.date, cp.description, a.name as account_name, cp.amount
        FROM cash_payments cp
        JOIN accounts a ON cp.account_code = a.code
        WHERE cp.user_id = %s
        ORDER BY cp.date DESC, cp.payment_no DESC
        LIMIT 50
    """, (session['user_id'],), fetch=True)
    
    return render_template('cash_payment.html',
                         accounts=accounts or [],
                         payment_count=payment_count,
                         today=datetime.now().strftime('%Y-%m-%d'),
                         payments=payments or [])

@app.route('/cash_receipt', methods=['GET', 'POST'])
def cash_receipt():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        receipt_no = request.form['receipt_no']
        date = request.form['date']
        description = request.form['description']
        account_code = request.form['account_code']
        amount = safe_float(request.form['amount'])
        
        if not receipt_no or not date or not description or not account_code or amount <= 0:
            flash('Mohon isi semua field dengan benar!', 'error')
            return redirect(url_for('cash_receipt'))
        
        try:
            # Insert cash receipt
            success = execute_query("""
                INSERT INTO cash_receipts (receipt_no, date, description, account_code, amount, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (receipt_no, date, description, account_code, amount, session['user_id']), commit=True)
            
            if not success:
                flash('Gagal mencatat cash receipt!', 'error')
                return redirect(url_for('cash_receipt'))
            
            journal_entry_no = f"CR{receipt_no}"
            
            # Insert journal entry
            journal_success = execute_query("""
                INSERT INTO journals (entry_no, date, description, user_id)
                VALUES (%s, %s, %s, %s)
            """, (journal_entry_no, date, f"Cash Receipt: {description}", session['user_id']), commit=True)
            
            if not journal_success:
                flash('Gagal mencatat journal entry!', 'error')
                return redirect(url_for('cash_receipt'))
            
            # Get the last inserted journal ID
            journal_result = execute_query(
                "SELECT id FROM journals WHERE entry_no = %s AND user_id = %s ORDER BY id DESC LIMIT 1",
                (journal_entry_no, session['user_id']), 
                fetch=True
            )
            
            if not journal_result or len(journal_result) == 0:
                flash('Gagal mendapatkan journal ID!', 'error')
                return redirect(url_for('cash_receipt'))
            
            journal_id = journal_result[0]['id']
            
            # Insert journal details (Kas debit)
            execute_query("""
                INSERT INTO journal_details (journal_id, account_code, debit, credit)
                VALUES (%s, %s, %s, %s)
            """, (journal_id, '1-1000', amount, 0), commit=True)
            
            # Insert journal details (Account credit)
            execute_query("""
                INSERT INTO journal_details (journal_id, account_code, debit, credit)
                VALUES (%s, %s, %s, %s)
            """, (journal_id, account_code, 0, amount), commit=True)
            
            flash('Cash Receipt berhasil dicatat!', 'success')
            
        except Exception as e:
            print(f"Cash receipt error: {e}")
            flash(f'Error: {str(e)}', 'error')
    
    # Get accounts for dropdown
    accounts = execute_query(
        "SELECT code, name FROM accounts WHERE type IN ('Revenue', 'Liability') ORDER BY code",
        fetch=True
    )
    
    # Get receipt count
    receipt_count_result = execute_query(
        "SELECT COUNT(*) as count FROM cash_receipts WHERE user_id = %s",
        (session['user_id'],),
        fetch=True
    )
    receipt_count = receipt_count_result[0]['count'] if receipt_count_result else 0
    
    # Get recent receipts
    receipts = execute_query("""
        SELECT cr.receipt_no, cr.date, cr.description, a.name as account_name, cr.amount
        FROM cash_receipts cr
        JOIN accounts a ON cr.account_code = a.code
        WHERE cr.user_id = %s
        ORDER BY cr.date DESC, cr.receipt_no DESC
        LIMIT 50
    """, (session['user_id'],), fetch=True)
    
    return render_template('cash_receipt.html',
                         accounts=accounts or [],
                         receipt_count=receipt_count,
                         today=datetime.now().strftime('%Y-%m-%d'),
                         receipts=receipts or [])

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        qty = safe_int(request.form['qty'])
        price = safe_float(request.form['price'])
        
        if not code or not name or qty <= 0 or price <= 0:
            flash('Isi data barang dengan benar!', 'error')
            return redirect(url_for('inventory'))
        
        try:
            # Check if item already exists
            existing_items = execute_query(
                "SELECT id, qty FROM inventory WHERE code = %s AND user_id = %s",
                (code, session['user_id']),
                fetch=True
            )
            
            if existing_items and len(existing_items) > 0:
                # Update existing item
                existing = existing_items[0]
                new_qty = existing['qty'] + qty
                success = execute_query(
                    "UPDATE inventory SET qty = %s, price = %s, name = %s WHERE id = %s",
                    (new_qty, price, name, existing['id']),
                    commit=True
                )
                if success:
                    flash('Barang berhasil diupdate!', 'success')
                else:
                    flash('Gagal mengupdate barang!', 'error')
            else:
                # Insert new item
                success = execute_query(
                    "INSERT INTO inventory (code, name, qty, price, user_id) VALUES (%s, %s, %s, %s, %s)",
                    (code, name, qty, price, session['user_id']),
                    commit=True
                )
                if success:
                    flash('Barang berhasil ditambahkan!', 'success')
                else:
                    flash('Gagal menambahkan barang!', 'error')
                    
        except Exception as e:
            print(f"Inventory error: {e}")
            flash(f'Error: {str(e)}', 'error')
    
    # Get inventory items
    items = execute_query(
        "SELECT code, name, qty, price FROM inventory WHERE user_id = %s ORDER BY code",
        (session['user_id'],),
        fetch=True
    )
    
    return render_template('inventory.html', items=items or [])

@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get revenue accounts with balances
        revenues = execute_query("""
            SELECT a.code, a.name, 
                   COALESCE((SELECT COALESCE(SUM(jd.credit - jd.debit), 0) 
                    FROM journal_details jd 
                    JOIN journals j ON jd.journal_id = j.id
                    WHERE jd.account_code = a.code AND j.user_id = %s), 0) as balance
            FROM accounts a
            WHERE a.type = 'Revenue'
        """, (session['user_id'],), fetch=True)
        
        # Get expense accounts with balances
        expenses = execute_query("""
            SELECT a.code, a.name, 
                   COALESCE((SELECT COALESCE(SUM(jd.debit - jd.credit), 0) 
                    FROM journal_details jd 
                    JOIN journals j ON jd.journal_id = j.id
                    WHERE jd.account_code = a.code AND j.user_id = %s), 0) as balance
            FROM accounts a
            WHERE a.type = 'Expense'
        """, (session['user_id'],), fetch=True)
        
        # Calculate totals
        total_revenue = sum(row['balance'] for row in revenues) if revenues else 0
        total_expense = sum(row['balance'] for row in expenses) if expenses else 0
        net_income = total_revenue - total_expense
        
        # Get asset accounts with balances
        asset_accounts = execute_query(
            "SELECT code, name, type FROM accounts WHERE type = 'Asset' ORDER BY code",
            fetch=True
        )
        assets = [(row['code'], row['name'], get_account_balance(row['code'])) for row in asset_accounts] if asset_accounts else []
        
        # Get liability accounts with balances
        liability_accounts = execute_query(
            "SELECT code, name, type FROM accounts WHERE type = 'Liability' ORDER BY code",
            fetch=True
        )
        liabilities = [(row['code'], row['name'], get_account_balance(row['code'])) for row in liability_accounts] if liability_accounts else []
        
        # Get equity accounts with balances
        equity_accounts = execute_query(
            "SELECT code, name, type FROM accounts WHERE type = 'Equity' ORDER BY code",
            fetch=True
        )
        equities = [(row['code'], row['name'], get_account_balance(row['code'])) for row in equity_accounts] if equity_accounts else []
        
        # Calculate balance sheet totals
        total_assets = sum(balance for _, _, balance in assets)
        total_liabilities = sum(balance for _, _, balance in liabilities)
        total_equity = sum(balance for _, _, balance in equities)
        
        # Equity Change Report
        beginning_equity = get_account_balance('3-3000')  # Modal account
        
        # Get owner's contributions (additional investments)
        investments_result = execute_query("""
            SELECT COALESCE(SUM(jd.credit - jd.debit), 0) as investments
            FROM journal_details jd
            JOIN journals j ON jd.journal_id = j.id
            WHERE jd.account_code = '3-3000' AND j.user_id = %s
        """, (session['user_id'],), fetch=True)
        additional_investments = investments_result[0]['investments'] if investments_result else 0
        
        # Get owner's withdrawals (prive)
        withdrawals_result = execute_query("""
            SELECT COALESCE(SUM(jd.debit - jd.credit), 0) as withdrawals
            FROM journal_details jd
            JOIN journals j ON jd.journal_id = j.id
            WHERE jd.account_code = '3-3300' AND j.user_id = %s
        """, (session['user_id'],), fetch=True)
        owner_withdrawals = withdrawals_result[0]['withdrawals'] if withdrawals_result else 0
        
        # Calculate ending equity
        ending_equity = beginning_equity + net_income + additional_investments - owner_withdrawals
        
        return render_template('reports.html',
                             revenues=revenues or [],
                             expenses=expenses or [],
                             total_revenue=total_revenue,
                             total_expense=total_expense,
                             net_income=net_income,
                             assets=assets,
                             liabilities=liabilities,
                             equities=equities,
                             total_assets=total_assets,
                             total_liabilities=total_liabilities,
                             total_equity=total_equity,
                             beginning_equity=beginning_equity,
                             additional_investments=additional_investments,
                             owner_withdrawals=owner_withdrawals,
                             ending_equity=ending_equity,
                             today=datetime.now().strftime('%Y-%m-%d'))
                             
    except Exception as e:
        print(f"Reports error: {e}")
        flash('Error loading reports', 'error')
        return redirect(url_for('dashboard'))
    
@app.route('/ledger')
def ledger():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    account_code = request.args.get('account_code', '')
    
    try:
        # Get all accounts for dropdown
        accounts = execute_query(
            "SELECT code, name FROM accounts ORDER BY code",
            fetch=True
        )
        
        ledger_data = []
        if account_code:
            # Get ledger entries for selected account
            ledger_data = execute_query("""
                SELECT j.date, j.entry_no, j.description, jd.debit, jd.credit
                FROM journal_details jd
                JOIN journals j ON jd.journal_id = j.id
                WHERE jd.account_code = %s AND j.user_id = %s
                ORDER BY j.date, j.entry_no
            """, (account_code, session['user_id']), fetch=True)
        
        return render_template('ledger.html', 
                             accounts=accounts or [], 
                             selected_account=account_code,
                             ledger_data=ledger_data or [])
                             
    except Exception as e:
        print(f"Ledger error: {e}")
        flash('Error loading ledger data', 'error')
        return redirect(url_for('dashboard'))

# ============ POST-CLOSING TRIAL BALANCE ============
@app.route('/post_closing_trial_balance')
def post_closing_trial_balance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get only permanent accounts (Asset, Liability, Equity) after closing entries
        accounts_data = execute_query(
            "SELECT code, name, type, normal_balance FROM accounts WHERE type IN ('Asset', 'Liability', 'Equity') ORDER BY code",
            fetch=True
        )
        
        accounts = []
        total_debit = 0
        total_credit = 0
        
        if accounts_data:
            for account in accounts_data:
                balance = get_account_balance(account['code'])
                
                # For post-closing, we only show permanent accounts
                # Determine debit/credit based on account type and normal balance
                if account['normal_balance'] == 'Debit':  # Asset accounts
                    debit = balance if balance >= 0 else 0
                    credit = abs(balance) if balance < 0 else 0
                else:  # Liability & Equity accounts (Credit normal balance)
                    debit = abs(balance) if balance < 0 else 0
                    credit = balance if balance >= 0 else 0
                
                accounts.append({
                    'code': account['code'],
                    'name': account['name'],
                    'type': account['type'],
                    'debit': debit,
                    'credit': credit
                })
                
                total_debit += debit
                total_credit += credit
        
        # Check if temporary accounts have zero balances (proper closing)
        revenue_balances = execute_query("""
            SELECT a.code, a.name, 
                   COALESCE(SUM(jd.credit - jd.debit), 0) as balance
            FROM accounts a
            LEFT JOIN journal_details jd ON a.code = jd.account_code
            LEFT JOIN journals j ON jd.journal_id = j.id
            WHERE a.type = 'Revenue' AND j.user_id = %s
            GROUP BY a.code, a.name
        """, (session['user_id'],), fetch=True)
        
        expense_balances = execute_query("""
            SELECT a.code, a.name, 
                   COALESCE(SUM(jd.debit - jd.credit), 0) as balance
            FROM accounts a
            LEFT JOIN journal_details jd ON a.code = jd.account_code
            LEFT JOIN journals j ON jd.journal_id = j.id
            WHERE a.type = 'Expense' AND j.user_id = %s
            GROUP BY a.code, a.name
        """, (session['user_id'],), fetch=True)
        
        # Check if all temporary accounts have zero balance
        all_temporary_zero = True
        temporary_accounts_with_balance = []
        
        if revenue_balances:
            for revenue in revenue_balances:
                if abs(revenue['balance']) > 0.01:  # Allow for rounding differences
                    all_temporary_zero = False
                    temporary_accounts_with_balance.append(revenue)
        
        if expense_balances:
            for expense in expense_balances:
                if abs(expense['balance']) > 0.01:  # Allow for rounding differences
                    all_temporary_zero = False
                    temporary_accounts_with_balance.append(expense)
        
        return render_template('post_closing_trial_balance.html',
                             accounts=accounts,
                             total_debit=total_debit,
                             total_credit=total_credit,
                             all_temporary_zero=all_temporary_zero,
                             temporary_accounts_with_balance=temporary_accounts_with_balance or [])
                             
    except Exception as e:
        print(f"Post-closing trial balance error: {e}")
        flash('Error loading post-closing trial balance', 'error')
        return redirect(url_for('dashboard'))

# ============ DELETE ROUTES ============

@app.route('/delete_journal/<entry_no>')
def delete_journal(entry_no):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get journal ID first
        journal_result = execute_query(
            "SELECT id FROM journals WHERE entry_no = %s AND user_id = %s",
            (entry_no, session['user_id']),
            fetch=True
        )
        
        if journal_result and len(journal_result) > 0:
            journal_id = journal_result[0]['id']
            
            # Delete journal details first (foreign key constraint)
            success_details = execute_query(
                "DELETE FROM journal_details WHERE journal_id = %s",
                (journal_id,),
                commit=True
            )
            
            if success_details:
                # Delete journal
                success_journal = execute_query(
                    "DELETE FROM journals WHERE id = %s",
                    (journal_id,),
                    commit=True
                )
                
                if success_journal:
                    flash('Jurnal berhasil dihapus!', 'success')
                else:
                    flash('Gagal menghapus jurnal!', 'error')
            else:
                flash('Gagal menghapus detail jurnal!', 'error')
        else:
            flash('Jurnal tidak ditemukan!', 'error')
            
    except Exception as e:
        print(f"Delete journal error: {e}")
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('journal'))

@app.route('/delete_adjusting_entry/<entry_no>')
def delete_adjusting_entry(entry_no):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get journal ID first
        journal_result = execute_query(
            "SELECT id FROM journals WHERE entry_no = %s AND user_id = %s",
            (entry_no, session['user_id']),
            fetch=True
        )
        
        if journal_result and len(journal_result) > 0:
            journal_id = journal_result[0]['id']
            
            # Delete journal details first
            success_details = execute_query(
                "DELETE FROM journal_details WHERE journal_id = %s",
                (journal_id,),
                commit=True
            )
            
            if success_details:
                # Delete journal
                success_journal = execute_query(
                    "DELETE FROM journals WHERE id = %s",
                    (journal_id,),
                    commit=True
                )
                
                if success_journal:
                    flash('Jurnal penyesuaian berhasil dihapus!', 'success')
                else:
                    flash('Gagal menghapus jurnal penyesuaian!', 'error')
            else:
                flash('Gagal menghapus detail jurnal penyesuaian!', 'error')
        else:
            flash('Jurnal penyesuaian tidak ditemukan!', 'error')
            
    except Exception as e:
        print(f"Delete adjusting entry error: {e}")
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('adjusting_entries'))

@app.route('/delete_cash_payment/<payment_no>')
def delete_cash_payment(payment_no):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get cash payment details first
        payment_result = execute_query(
            "SELECT id, amount FROM cash_payments WHERE payment_no = %s AND user_id = %s",
            (payment_no, session['user_id']),
            fetch=True
        )
        
        if payment_result and len(payment_result) > 0:
            payment_id = payment_result[0]['id']
            journal_entry_no = f"CP{payment_no}"
            
            # Get associated journal
            journal_result = execute_query(
                "SELECT id FROM journals WHERE entry_no = %s AND user_id = %s",
                (journal_entry_no, session['user_id']),
                fetch=True
            )
            
            # Delete journal entries if they exist
            if journal_result and len(journal_result) > 0:
                journal_id = journal_result[0]['id']
                
                # Delete journal details first
                execute_query(
                    "DELETE FROM journal_details WHERE journal_id = %s",
                    (journal_id,),
                    commit=True
                )
                
                # Delete journal
                execute_query(
                    "DELETE FROM journals WHERE id = %s",
                    (journal_id,),
                    commit=True
                )
            
            # Delete cash payment
            success_payment = execute_query(
                "DELETE FROM cash_payments WHERE id = %s",
                (payment_id,),
                commit=True
            )
            
            if success_payment:
                flash('Cash payment berhasil dihapus!', 'success')
            else:
                flash('Gagal menghapus cash payment!', 'error')
        else:
            flash('Cash payment tidak ditemukan!', 'error')
            
    except Exception as e:
        print(f"Delete cash payment error: {e}")
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('cash_payment'))

@app.route('/delete_cash_receipt/<receipt_no>')
def delete_cash_receipt(receipt_no):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get receipt data first
        receipt_result = execute_query(
            "SELECT id, amount FROM cash_receipts WHERE receipt_no = %s AND user_id = %s",
            (receipt_no, session['user_id']),
            fetch=True
        )
        
        if receipt_result and len(receipt_result) > 0:
            receipt_id = receipt_result[0]['id']
            
            # Delete corresponding journal entries
            journal_entry_no = f"CR{receipt_no}"
            journal_result = execute_query(
                "SELECT id FROM journals WHERE entry_no = %s AND user_id = %s",
                (journal_entry_no, session['user_id']),
                fetch=True
            )
            
            # Delete journal entries if they exist
            if journal_result and len(journal_result) > 0:
                journal_id = journal_result[0]['id']
                
                # Delete journal details first
                execute_query(
                    "DELETE FROM journal_details WHERE journal_id = %s",
                    (journal_id,),
                    commit=True
                )
                
                # Delete journal
                execute_query(
                    "DELETE FROM journals WHERE id = %s",
                    (journal_id,),
                    commit=True
                )
            
            # Delete cash receipt
            success_receipt = execute_query(
                "DELETE FROM cash_receipts WHERE id = %s",
                (receipt_id,),
                commit=True
            )
            
            if success_receipt:
                flash('Cash receipt berhasil dihapus!', 'success')
            else:
                flash('Gagal menghapus cash receipt!', 'error')
        else:
            flash('Cash receipt tidak ditemukan!', 'error')
            
    except Exception as e:
        print(f"Delete cash receipt error: {e}")
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('cash_receipt'))

@app.route('/delete_inventory/<code>')
def delete_inventory(code):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        success = execute_query(
            "DELETE FROM inventory WHERE code = %s AND user_id = %s",
            (code, session['user_id']),
            commit=True
        )
        
        if success:
            flash('Barang berhasil dihapus!', 'success')
        else:
            flash('Gagal menghapus barang!', 'error')
            
    except Exception as e:
        print(f"Delete inventory error: {e}")
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('inventory'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)