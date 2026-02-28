from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'digital_library_secret_key_2024'

def datubazes_izveide():
    savienojums = sqlite3.connect('biblioteka.db')
    kursors = savienojums.cursor()

    kursors.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT
        )
    """)

    kursors.execute("""
        CREATE TABLE IF NOT EXISTS books(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            genre TEXT,
            status TEXT,
            user_id INTEGER,
            added_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    kursors.execute("""
        CREATE TABLE IF NOT EXISTS tobuy(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            genre TEXT,
            user_id INTEGER,
            added_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    kursors.execute("SELECT COUNT(*) FROM users")
    if kursors.fetchone()[0] == 0:
        kursors.execute(
            "INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
            ('admin', 'admin123', 'admin', datetime.now().isoformat())
        )
        kursors.execute(
            "INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
            ('lietotajs', 'lasitajs123', 'user', datetime.now().isoformat())
        )

    savienojums.commit()
    savienojums.close()

def izpildit_vaicajumu(vaicajums, parametri=(), viens=False, visi=False):
    savienojums = sqlite3.connect('biblioteka.db')
    savienojums.row_factory = sqlite3.Row
    kursors = savienojums.cursor()
    kursors.execute(vaicajums, parametri)
    savienojums.commit()

    rezultats = None
    if viens:
        rezultats = kursors.fetchone()
    elif visi:
        rezultats = kursors.fetchall()

    savienojums.close()
    return rezultats

def ieladet_tulkojumus(lapa, valoda='lv'):
    try:
        if valoda not in ['lv', 'en']:
            valoda = 'lv'
        faila_cels = os.path.join('/home/elexanderaa/DigitalLibrary/static', f'{valoda}.json')
        with open(faila_cels, 'r', encoding='utf-8') as f:
            visi_tulkojumi = json.load(f)
            return visi_tulkojumi.get(lapa, {})
    except:
        return {}

@app.route('/')
def index():
    datubazes_izveide()
    valoda = request.args.get('lang', 'lv')
    if valoda not in ['lv', 'en']:
        valoda = 'lv'

    kļuda = request.args.get('error', None)
    kļudas_teksts = None

    if kļuda:
        if kļuda == 'invalid_data':
            kļudas_teksts = "Nepareizs lietotājvārds vai parole!"
        elif kļuda == 'short_username':
            kļudas_teksts = "Lietotājvārds pārāk īss (min 3 simboli)!"
        elif kļuda == 'short_password':
            kļudas_teksts = "Parole pārāk īsa (min 4 simboli)!"
        elif kļuda == 'password_mismatch':
            kļudas_teksts = "Paroles nesakrīt!"
        elif kļuda == 'user_exists':
            kļudas_teksts = "Lietotājs jau eksistē!"

    return render_template('index.html',
                         t=ieladet_tulkojumus('index', valoda),
                         lang=valoda,
                         error=kļudas_teksts)

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    password1 = request.form.get('password', '').strip()
    password2 = request.form.get('password2', '').strip()
    lang = request.args.get('lang', 'lv')

    if len(username) < 3:
        return redirect(url_for('index', lang=lang, error='short_username'))
    if len(password1) < 4:
        return redirect(url_for('index', lang=lang, error='short_password'))
    if password1 != password2:
        return redirect(url_for('index', lang=lang, error='password_mismatch'))


    existing_user = izpildit_vaicajumu(
        "SELECT id FROM users WHERE username = ?",
        (username,),
        viens=True
    )

    if existing_user:

        return redirect(url_for('index', lang=lang, error='user_exists'))

    izpildit_vaicajumu(
        "INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
        (username, password1, 'user', datetime.now().isoformat())
    )

    user = izpildit_vaicajumu(
        "SELECT * FROM users WHERE username = ?",
        (username,),
        viens=True
    )

    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']

    return redirect(url_for('profile', username=username, lang=lang))

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    lang = request.args.get('lang', 'lv')

    user = izpildit_vaicajumu(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password),
        viens=True
    )

    if not user:
        return redirect(url_for('index', lang=lang, error='invalid_data'))

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']

    return redirect(url_for('profile', username=username, lang=lang))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    lang = request.args.get('lang', 'lv')
    username = request.args.get('username')

    if username != session['username'] and session.get('role') != 'admin':
        return redirect(url_for('profile', username=session['username'], lang=lang))

    user = izpildit_vaicajumu(
        "SELECT * FROM users WHERE username=?",
        (username,),
        viens=True
    )

    if not user:
        return redirect(url_for('index'))

    books_count = izpildit_vaicajumu(
        "SELECT COUNT(*) FROM books WHERE user_id=?",
        (user['id'],),
        viens=True
    )

    tobuy_count = izpildit_vaicajumu(
        "SELECT COUNT(*) FROM tobuy WHERE user_id=?",
        (user['id'],),
        viens=True
    )

    return render_template(
        'profile.html',
        t=ieladet_tulkojumus('profile', lang),
        user=user,
        books_count=books_count[0] if books_count else 0,
        tobuy_count=tobuy_count[0] if tobuy_count else 0,
        lang=lang,
        session=session
    )

@app.route('/books')
def books():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    lang = request.args.get('lang', 'lv')
    books_list = izpildit_vaicajumu(
        "SELECT * FROM books WHERE user_id=? ORDER BY title",
        (session['user_id'],),
        visi=True
    )

    return render_template(
        'books.html',
        t=ieladet_tulkojumus('books', lang),
        books=books_list,
        user_role=session.get('role'),
        lang=lang,
        session=session
    )

@app.route('/books/search')
def search_books():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    search_term = request.args.get('q', '').lower()
    lang = request.args.get('lang', 'lv')

    if search_term:
        books_list = izpildit_vaicajumu(
            """SELECT * FROM books
               WHERE user_id=? AND (
                   LOWER(title) LIKE ? OR
                   LOWER(author) LIKE ? OR
                   LOWER(genre) LIKE ?
               ) ORDER BY title""",
            (session['user_id'], f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'),
            visi=True
        )
    else:
        books_list = izpildit_vaicajumu(
            "SELECT * FROM books WHERE user_id=? ORDER BY title",
            (session['user_id'],),
            visi=True
        )

    return render_template(
        'books.html',
        t=ieladet_tulkojumus('books', lang),
        books=books_list,
        user_role=session.get('role'),
        lang=lang,
        search=search_term,
        session=session
    )

@app.route('/books/add', methods=['POST'])
def add_book():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()
    genre = request.form.get('genre', '').strip()
    status = request.form.get('status', 'Read')
    lang = request.args.get('lang', 'lv')

    if not title or not author or not genre:
        return redirect(url_for('profile', username=session['username'], lang=lang, error='empty_fields'))

    existing = izpildit_vaicajumu(
        "SELECT * FROM books WHERE title=? AND author=? AND user_id=?",
        (title, author, session['user_id']),
        viens=True
    )

    if existing:
        return redirect(url_for('profile', username=session['username'], lang=lang, error='book_exists'))

    if status == 'To buy':
        izpildit_vaicajumu(
            "INSERT INTO tobuy (title, author, genre, user_id, added_at) VALUES (?, ?, ?, ?, ?)",
            (title, author, genre, session['user_id'], datetime.now().isoformat())
        )
    else:
        izpildit_vaicajumu(
            "INSERT INTO books (title, author, genre, status, user_id, added_at) VALUES (?, ?, ?, ?, ?, ?)",
            (title, author, genre, status, session['user_id'], datetime.now().isoformat())
        )

    return redirect(url_for('profile', username=session['username'], lang=lang, success=1))

@app.route('/books/update/<int:book_id>', methods=['POST'])
def update_book_status(book_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    new_status = request.form.get('status')
    lang = request.args.get('lang', 'lv')

    book = izpildit_vaicajumu(
        "SELECT * FROM books WHERE id=? AND user_id=?",
        (book_id, session['user_id']),
        viens=True
    )

    if book:
        izpildit_vaicajumu(
            "UPDATE books SET status=? WHERE id=?",
            (new_status, book_id)
        )

    return redirect(url_for('books', lang=lang))

@app.route('/books/delete/<int:book_id>')
def delete_book(book_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    lang = request.args.get('lang', 'lv')

    if session.get('role') == 'admin':
        izpildit_vaicajumu("DELETE FROM books WHERE id=?", (book_id,))
    else:
        izpildit_vaicajumu(
            "DELETE FROM books WHERE id=? AND user_id=?",
            (book_id, session['user_id'])
        )

    return redirect(url_for('books', lang=lang))

@app.route('/tobuy')
def tobuy():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    lang = request.args.get('lang', 'lv')

    books_list = izpildit_vaicajumu(
        "SELECT * FROM tobuy WHERE user_id=? ORDER BY title",
        (session['user_id'],),
        visi=True
    )

    return render_template(
        'tobuy.html',
        t=ieladet_tulkojumus('tobuy', lang),
        books=books_list,
        lang=lang,
        session=session
    )

@app.route('/tobuy/move/<int:book_id>')
def move_to_main(book_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    lang = request.args.get('lang', 'lv')

    book = izpildit_vaicajumu(
        "SELECT * FROM tobuy WHERE id=? AND user_id=?",
        (book_id, session['user_id']),
        viens=True
    )

    if book:
        izpildit_vaicajumu(
            "INSERT INTO books (title, author, genre, status, user_id, added_at) VALUES (?, ?, ?, ?, ?, ?)",
            (book['title'], book['author'], book['genre'], 'Not read', session['user_id'], datetime.now().isoformat())
        )

        izpildit_vaicajumu(
            "DELETE FROM tobuy WHERE id=? AND user_id=?",
            (book_id, session['user_id'])
        )

    return redirect(url_for('tobuy', lang=lang))

@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    lang = request.args.get('lang', 'lv')

    users_list = izpildit_vaicajumu(
        "SELECT id, username, role, created_at FROM users ORDER BY id",
        visi=True
    )

    users_with_stats = []
    for u in users_list:
        books_count = izpildit_vaicajumu(
            "SELECT COUNT(*) FROM books WHERE user_id=?",
            (u['id'],),
            viens=True
        )
        tobuy_count = izpildit_vaicajumu(
            "SELECT COUNT(*) FROM tobuy WHERE user_id=?",
            (u['id'],),
            viens=True
        )
        users_with_stats.append({
            'id': u['id'],
            'username': u['username'],
            'role': u['role'],
            'created_at': u['created_at'],
            'books_count': books_count[0] if books_count else 0,
            'tobuy_count': tobuy_count[0] if tobuy_count else 0
        })

    return render_template(
        'admin.html',
        t=ieladet_tulkojumus('admin', lang),
        users=users_with_stats,
        lang=lang,
        session=session
    )

@app.route('/admin/add_user', methods=['POST'])
def add_user():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'user')
    lang = request.args.get('lang', 'lv')

    if username and password:
        try:
            izpildit_vaicajumu(
                "INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                (username, password, role, datetime.now().isoformat())
            )
        except sqlite3.IntegrityError:
            pass

    return redirect(url_for('admin_panel', lang=lang))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)