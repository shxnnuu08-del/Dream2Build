import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dream2build.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    seed_demo_user()

def seed_demo_user():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', ('demo@dream2build.ai',))
    row = cursor.fetchone()
    conn.close()
    if not row:
        create_user('Demo Architect', 'demo@dream2build.ai', 'password123')


def create_user(name, email, password):
    """
    Registers a new user. Returns (user_dict, None) on success or (None, error_message) on failure.
    """
    email_clean = email.strip().lower()
    name_clean = name.strip()
    
    if not name_clean:
        return None, "Please enter your full name."
    if not email_clean or '@' not in email_clean or '.' not in email_clean:
        return None, "Please provide a valid email address."
    if not password or len(password) < 6:
        return None, "Password must be at least 6 characters long."
        
    pwd_hash = generate_password_hash(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            (name_clean, email_clean, pwd_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.execute('SELECT id, name, email, created_at FROM users WHERE id = ?', (user_id,))
        user = dict(cursor.fetchone())
        conn.close()
        return user, None
    except sqlite3.IntegrityError:
        conn.close()
        return None, "An account with this email already exists. Please log in."
    except Exception as e:
        conn.close()
        return None, f"Registration failed: {str(e)}"

def verify_user(email, password):
    """
    Verifies user login credentials. Returns (user_dict, None) on success or (None, error_message).
    """
    email_clean = email.strip().lower()
    if not email_clean or not password:
        return None, "Please provide both email and password."
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email_clean,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None, "No account found with this email. Please register."
        
    user = dict(row)
    if not check_password_hash(user['password_hash'], password):
        return None, "Incorrect password. Please try again."
        
    return {
        "id": user['id'],
        "name": user['name'],
        "email": user['email'],
        "created_at": user['created_at']
    }, None

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, created_at FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None
