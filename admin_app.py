import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from dotenv import load_dotenv
from database import Database

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('ADMIN_SECRET_KEY', 'change_this_secret_key_in_production')

# Настройки админа
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin')
DB_PATH = os.getenv('DATABASE_PATH', 'psymatch.db')

db = Database(DB_PATH)


def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница авторизации"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.pop('logged_in', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Главная страница с фича-флагами"""
    flags = db.get_all_feature_flags()
    stats = db.get_statistics()
    return render_template('index.html', flags=flags, stats=stats)


@app.route('/toggle_flag/<flag_name>', methods=['POST'])
@login_required
def toggle_flag(flag_name):
    """Переключение фича-флага"""
    enabled = request.form.get('enabled') == 'on'
    db.set_feature_flag(flag_name, enabled)
    
    status = 'включен' if enabled else 'выключен'
    flash(f'Фича-флаг "{flag_name}" {status}', 'success')
    
    return redirect(url_for('index'))


@app.route('/users')
@login_required
def users():
    """Страница со списком пользователей"""
    users_list = db.get_all_users_with_stats()
    return render_template('users.html', users=users_list)


@app.route('/user/<int:user_id>')
@login_required
def user_detail(user_id):
    """Детали профиля пользователя"""
    user = db.get_user(user_id)
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users'))
    
    if user['user_type'] == 'psychologist':
        profile = db.get_psychologist_info(user_id)
    else:
        profile = db.get_patient_info(user_id)
    
    stats = {
        'likes_sent': len(db.get_connection().execute('SELECT * FROM likes WHERE from_user_id = ?', (user_id,)).fetchall()),
        'likes_received': len(db.get_connection().execute('SELECT * FROM likes WHERE to_user_id = ?', (user_id,)).fetchall()),
        'mutual_matches': len(db.get_connection().execute('SELECT * FROM likes WHERE (from_user_id = ? OR to_user_id = ?) AND is_mutual = 1', (user_id, user_id)).fetchall()) // 2
    }
    
    is_blocked = db.is_user_blocked(user_id)
    
    return render_template('user_detail.html', user=user, profile=profile, stats=stats, is_blocked=is_blocked)


@app.route('/user/<int:user_id>/block', methods=['POST'])
@login_required
def block_user(user_id):
    """Заблокировать пользователя"""
    db.block_user(user_id)
    flash(f'Пользователь {user_id} заблокирован', 'success')
    return redirect(url_for('user_detail', user_id=user_id))


@app.route('/user/<int:user_id>/unblock', methods=['POST'])
@login_required
def unblock_user(user_id):
    """Разблокировать пользователя"""
    db.unblock_user(user_id)
    flash(f'Пользователь {user_id} разблокирован', 'success')
    return redirect(url_for('user_detail', user_id=user_id))


if __name__ == '__main__':
    # В продакшене используйте gunicorn или другой WSGI-сервер
    app.run(host='0.0.0.0', port=5001, debug=False)

