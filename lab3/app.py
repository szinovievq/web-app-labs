from flask import Flask, render_template, redirect, url_for, session, flash, request, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import timedelta

app = Flask(__name__)

app.config['SECRET_KEY'] = 'key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['REMEMBER_COOKIE_NAME'] = 'remember_token'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Для доступа к запрашиваемой странице необходимо пройти процедуру аутентификации."
login_manager.login_message_category = "info"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

users_db = {"user": "qwerty"}

@login_manager.user_loader
def load_user(user_id):
    if user_id in users_db:
        return User(user_id)
    return None

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/counter')
def counter():
    if 'visits' in session:
        session['visits'] = session.get('visits') + 1
    else:
        session['visits'] = 1
    return render_template('counter.html', count=session['visits'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if username in users_db and users_db[username] == password:
            user = User(username)
            session.permanent = remember
            login_user(user, remember=remember)
            flash('Вы успешно вошли в систему!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))

        flash('Неверно введенные данные. Попробуйте еще раз.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()

    session.clear()
    session.permanent = False

    flash('Вы вышли из системы.', 'info')

    response = make_response(redirect(url_for('index')))
    response.set_cookie('session', '', expires=0)
    response.set_cookie('remember_token', '', expires=0)

    return response

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html')

if __name__ == '__main__':
    app.run(debug=True)