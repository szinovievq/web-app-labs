from flask import Blueprint, render_template, request, send_file, current_app as app
from flask_login import current_user, login_required
import sqlite3
import csv
import io
from io import StringIO

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def get_db_conn():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


@reports_bp.route('/visit-logs')
@login_required
def visit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    conn = get_db_conn()

    if current_user.role_id == 1:
        logs = conn.execute('''
            SELECT v.id, v.path, v.created_at, u.last_name, u.first_name, u.middle_name, u.id as user_id
            FROM visit_logs v
            LEFT JOIN users u ON v.user_id = u.id
            ORDER BY v.created_at DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset)).fetchall()

        total = conn.execute('SELECT COUNT(*) as cnt FROM visit_logs').fetchone()['cnt']
    else:
        logs = conn.execute('''
            SELECT v.id, v.path, v.created_at, u.last_name, u.first_name, u.middle_name, u.id as user_id
            FROM visit_logs v
            LEFT JOIN users u ON v.user_id = u.id
            WHERE v.user_id = ?
            ORDER BY v.created_at DESC
            LIMIT ? OFFSET ?
        ''', (current_user.id, per_page, offset)).fetchall()

        total = conn.execute('SELECT COUNT(*) as cnt FROM visit_logs WHERE user_id = ?', (current_user.id,)).fetchone()[
            'cnt']

    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('visit_logs.html', logs=logs, page=page, total_pages=total_pages, total=total)


@reports_bp.route('/stats/pages')
@login_required
def stats_pages():
    conn = get_db_conn()
    if current_user.role_id == 1:
        stats = conn.execute('''
            SELECT path, COUNT(*) as visits
            FROM visit_logs
            GROUP BY path
            ORDER BY visits DESC
        ''').fetchall()
    else:
        stats = conn.execute('''
            SELECT path, COUNT(*) as visits
            FROM visit_logs
            WHERE user_id = ?
            GROUP BY path
            ORDER BY visits DESC
        ''', (current_user.id,)).fetchall()
    conn.close()
    return render_template('stats_pages.html', stats=stats)


@reports_bp.route('/stats/users')
@login_required
def stats_users():
    conn = get_db_conn()
    if current_user.role_id == 1:
        stats = conn.execute('''
            SELECT 
                u.id,
                u.last_name,
                u.first_name,
                u.middle_name,
                COUNT(v.id) as visits
            FROM users u
            LEFT JOIN visit_logs v ON u.id = v.user_id
            GROUP BY u.id
            ORDER BY visits DESC
        ''').fetchall()
        anon = conn.execute('''
            SELECT COUNT(*) as visits
            FROM visit_logs
            WHERE user_id IS NULL
        ''').fetchone()
        if anon['visits'] > 0:
            stats = list(stats)
            stats.append(
                {'id': None, 'last_name': None, 'first_name': None, 'middle_name': None, 'visits': anon['visits']})
    else:
        stats = conn.execute('''
            SELECT 
                u.id,
                u.last_name,
                u.first_name,
                u.middle_name,
                COUNT(v.id) as visits
            FROM users u
            LEFT JOIN visit_logs v ON u.id = v.user_id
            WHERE u.id = ?
            GROUP BY u.id
        ''', (current_user.id,)).fetchall()
    conn.close()
    return render_template('stats_users.html', stats=stats)


@reports_bp.route('/export/pages-csv')
@login_required
def export_pages_csv():
    conn = get_db_conn()
    if current_user.role_id == 1:
        stats = conn.execute(
            'SELECT path, COUNT(*) as visits FROM visit_logs GROUP BY path ORDER BY visits DESC').fetchall()
    else:
        stats = conn.execute(
            'SELECT path, COUNT(*) as visits FROM visit_logs WHERE user_id = ? GROUP BY path ORDER BY visits DESC',
            (current_user.id,)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Страница', 'Количество посещений'])
    for row in stats:
        writer.writerow([row['path'], row['visits']])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='pages_stats.csv'
    )

@reports_bp.route('/export/users-csv')
@login_required
def export_users_csv():
    conn = get_db_conn()
    if current_user.role_id == 1:
        stats = conn.execute('''
            SELECT 
                u.id,
                u.last_name,
                u.first_name,
                u.middle_name,
                COUNT(v.id) as visits
            FROM users u
            LEFT JOIN visit_logs v ON u.id = v.user_id
            GROUP BY u.id
            ORDER BY visits DESC
        ''').fetchall()
        anon = conn.execute('SELECT COUNT(*) as visits FROM visit_logs WHERE user_id IS NULL').fetchone()
        if anon['visits'] > 0:
            stats = list(stats)
            stats.append(
                {'id': None, 'last_name': None, 'first_name': None, 'middle_name': None, 'visits': anon['visits']})
    else:
        stats = conn.execute('''
            SELECT 
                u.id,
                u.last_name,
                u.first_name,
                u.middle_name,
                COUNT(v.id) as visits
            FROM users u
            LEFT JOIN visit_logs v ON u.id = v.user_id
            WHERE u.id = ?
            GROUP BY u.id
        ''', (current_user.id,)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Пользователь', 'Количество посещений'])
    for row in stats:
        if row['id'] is None:
            name = 'Неаутентифицированный пользователь'
        else:
            name = f"{row['last_name'] or ''} {row['first_name'] or ''} {row['middle_name'] or ''}".strip() or f"ID:{row['id']}"
        writer.writerow([name, row['visits']])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='users_stats.csv'
    )