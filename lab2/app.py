import re
from flask import Flask, render_template, request, make_response

app = Flask(__name__)

def format_phone(phone_digits):
    d = re.sub(r'\D', '', phone_digits)
    if len(d) == 11:
        d = d[1:]
    return f"8-{d[0:3]}-{d[3:6]}-{d[6:8]}-{d[8:10]}"

@app.route('/', methods=['GET', 'POST'])
def form_params():
    auth_data = None
    if request.method == 'POST':
        auth_data = request.form
    return render_template('form_view.html', auth_data=auth_data)

@app.route('/url-params')
def url_params():
    return render_template('data_view.html', title="Параметры URL", data=request.args)

@app.route('/headers')
def headers_view():
    return render_template('data_view.html', title="Заголовки запроса", data=request.headers)

@app.route('/cookies')
def cookies_view():
    res = make_response(render_template('data_view.html', title="Cookie", data=request.cookies))
    res.set_cookie('User_Status', 'Student_Active')
    res.set_cookie('Session_ID', '12345ABCDE')
    return res


@app.route('/phone', methods=['GET', 'POST'])
def phone_check():
    phone_raw = ""
    error_msg = None
    formatted_phone = None

    if request.method == 'POST':
        phone_raw = request.form.get('phone', '').strip()

        if not re.fullmatch(r'[0-9\s\(\)\-\.\+]+', phone_raw):
            error_msg = "Недопустимый ввод. В номере телефона встречаются недопустимые символы."
        else:
            digits = re.sub(r'\D', '', phone_raw)
            length = len(digits)

            has_plus = '+' in phone_raw

            if length == 10:
                if has_plus:
                    error_msg = "Недопустимый ввод. Неверное количество цифр."
                else:
                    formatted_phone = format_phone(digits)
            elif length == 11:
                if phone_raw.startswith('+7') or phone_raw.startswith('8'):
                    formatted_phone = format_phone(digits)
                else:
                    error_msg = "Недопустимый ввод. Неверное количество цифр."
            else:
                error_msg = "Недопустимый ввод. Неверное количество цифр."

    return render_template('phone_check.html', phone_raw=phone_raw, error_msg=error_msg,
                           formatted_phone=formatted_phone)

if __name__ == '__main__':
    app.run(debug=True)