import os
import re
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-12345'
app.config['DATABASE'] = os.path.join(app.root_path, 'database.db')

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = 'Для выполнения этого действия необходимо авторизоваться.'
login_manager.login_message_category = 'danger'
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, user_id, login, role_id):
        self.id = user_id
        self.login = login
        self.role_id = role_id


def get_db_conn():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_conn()
    table_check = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()

    if not table_check:
        with app.open_resource('schema.sql', mode='r', encoding='utf-8') as f:
            conn.cursor().executescript(f.read())
        conn.commit()

    correct_hash = generate_password_hash('Admin12345')
    conn.execute('UPDATE users SET password_hash = ? WHERE login = ?', (correct_hash, 'admin'))
    conn.commit()
    conn.close()


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_conn()
    res = conn.execute('SELECT id, login, role_id FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if res:
        return User(res['id'], res['login'], res['role_id'])
    return None


def validate_password(password):
    errors = []
    if not (8 <= len(password) <= 128):
        errors.append("Пароль должен быть длиной от 8 до 128 символов.")
    if not re.search(r'[A-ZА-ЯЁ]', password):
        errors.append("Пароль должен содержать минимум одну заглавную букву.")
    if not re.search(r'[a-zа-яё]', password):
        errors.append("Пароль должен содержать минимум одну строчную букву.")
    if not re.search(r'\d', password):
        errors.append("Пароль должен содержать минимум одну цифру.")
    if re.search(r'\s', password):
        errors.append("Пароль не должен содержать пробелов.")

    allowed_chars = r"A-Za-zА-Яа-яЁё0-9~!?@#\$%^&*\_\-\+\(\)\[\]\{\}><\/\\\|\"'\.,:;"
    if not re.match(rf'^[{allowed_chars}]+$', password):
        errors.append("Пароль содержит недопустимые символы.")

    return errors


def validate_login(login):
    errors = []
    if not login or len(login) < 5:
        errors.append("Логин должен быть не менее 5 символов.")
    if not re.match(r'^[A-Za-z0-9]+$', login):
        errors.append("Логин должен состоять только из латинских букв и цифр.")
    return errors


@app.route('/')
def index():
    conn = get_db_conn()
    users = conn.execute('''
        SELECT u.id, u.login, u.last_name, u.first_name, u.middle_name, r.name as role_name 
        FROM users u 
        LEFT JOIN roles r ON u.role_id = r.id
    ''').fetchall()
    conn.close()
    return render_template('index.html', users=users)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if username:
            username = username.strip()

        conn = get_db_conn()
        user_row = conn.execute('SELECT * FROM users WHERE login = ?', (username,)).fetchone()
        conn.close()

        if user_row and check_password_hash(user_row['password_hash'], password):
            user_obj = User(user_row['id'], user_row['login'], user_row['role_id'])
            login_user(user_obj, remember=remember)
            flash('Вы успешно вошли в систему.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


@app.route('/users/<int:user_id>')
def view_user(user_id):
    conn = get_db_conn()
    user_row = conn.execute('''
        SELECT u.id, u.login, u.last_name, u.first_name, u.middle_name, r.name as role_name 
        FROM users u 
        LEFT JOIN roles r ON u.role_id = r.id 
        WHERE u.id = ?
    ''', (user_id,)).fetchone()
    conn.close()
    if not user_row:
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('index'))
    return render_template('view.html', user=user_row)


@app.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    conn = get_db_conn()
    roles = conn.execute('SELECT id, name FROM roles').fetchall()

    errors = {}
    form_data = {}

    if request.method == 'POST':
        form_data = {
            'login': request.form.get('login', '').strip(),
            'last_name': request.form.get('last_name', '').strip(),
            'first_name': request.form.get('first_name', '').strip(),
            'middle_name': request.form.get('middle_name', '').strip(),
            'role_id': request.form.get('role_id')
        }
        password = request.form.get('password', '')

        if not form_data['login']: errors['login'] = 'Поле не может быть пустым.'
        if not password: errors['password'] = 'Поле не может быть пустым.'
        if not form_data['first_name']: errors['first_name'] = 'Поле не может быть пустым.'

        if form_data['login'] and not errors.get('login'):
            login_errs = validate_login(form_data['login'])
            if login_errs: errors['login'] = " ".join(login_errs)

        if password and not errors.get('password'):
            pass_errs = validate_password(password)
            if pass_errs: errors['password'] = " ".join(pass_errs)

        if not errors.get('login'):
            existing = conn.execute('SELECT id FROM users WHERE login = ?', (form_data['login'],)).fetchone()
            if existing:
                errors['login'] = 'Пользователь с таким логином уже существует.'

        if not errors:
            try:
                p_hash = generate_password_hash(password)
                r_id = int(form_data['role_id']) if form_data['role_id'] else None

                conn.execute('''
                    INSERT INTO users (login, password_hash, last_name, first_name, middle_name, role_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (form_data['login'], p_hash, form_data['last_name'] or None,
                      form_data['first_name'], form_data['middle_name'] or None, r_id))
                conn.commit()
                conn.close()
                flash('Пользователь успешно создан!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Ошибка записи в БД: {str(e)}', 'danger')
        else:
            flash('Пожалуйста, исправьте ошибки в форме.', 'danger')

    conn.close()
    return render_template('create.html', roles=roles, errors=errors, form_data=form_data)


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    conn = get_db_conn()
    user_row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    roles = conn.execute('SELECT id, name FROM roles').fetchall()

    if not user_row:
        conn.close()
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('index'))

    errors = {}
    form_data = {
        'last_name': user_row['last_name'] or '',
        'first_name': user_row['first_name'] or '',
        'middle_name': user_row['middle_name'] or '',
        'role_id': str(user_row['role_id']) if user_row['role_id'] else ''
    }

    if request.method == 'POST':
        form_data = {
            'last_name': request.form.get('last_name', '').strip(),
            'first_name': request.form.get('first_name', '').strip(),
            'middle_name': request.form.get('middle_name', '').strip(),
            'role_id': request.form.get('role_id')
        }

        if not form_data['first_name']:
            errors['first_name'] = 'Поле не может быть пустым.'

        if not errors:
            try:
                r_id = int(form_data['role_id']) if form_data['role_id'] else None
                conn.execute('''
                    UPDATE users 
                    SET last_name = ?, first_name = ?, middle_name = ?, role_id = ?
                    WHERE id = ?
                ''', (form_data['last_name'] or None, form_data['first_name'],
                      form_data['middle_name'] or None, r_id, user_id))
                conn.commit()
                conn.close()
                flash('Данные пользователя успешно обновлены!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Ошибка обновления БД: {str(e)}', 'danger')
        else:
            flash('Пожалуйста, исправьте ошибки в форме.', 'danger')

    conn.close()
    return render_template('edit.html', roles=roles, errors=errors, form_data=form_data, user_id=user_id)


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    conn = get_db_conn()
    user_row = conn.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user_row:
        conn.close()
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('index'))

    try:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        flash('Пользователь успешно удален.', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении пользователя из БД: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('index'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    errors = {}
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        conn = get_db_conn()
        user_row = conn.execute('SELECT password_hash FROM users WHERE id = ?', (current_user.id,)).fetchone()

        if not old_password:
            errors['old_password'] = 'Введите старый пароль.'
        elif not check_password_hash(user_row['password_hash'], old_password):
            errors['old_password'] = 'Неверно указан старый пароль.'

        if not new_password:
            errors['new_password'] = 'Введите новый пароль.'
        else:
            pass_errs = validate_password(new_password)
            if pass_errs:
                errors['new_password'] = " ".join(pass_errs)

        if new_password != confirm_password:
            errors['confirm_password'] = 'Пароли не совпадают.'

        if not errors:
            try:
                new_hash = generate_password_hash(new_password)
                conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, current_user.id))
                conn.commit()
                conn.close()
                flash('Пароль успешно изменен!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Ошибка смены пароля in БД: {str(e)}', 'danger')
        else:
            conn.close()
            flash('Ошибка смены пароля. Проверьте правильность заполнения полей.', 'danger')

    return render_template('change_password.html', errors=errors)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)