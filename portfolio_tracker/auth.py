import functools
import re
from werkzeug.security import check_password_hash, generate_password_hash
from portfolio_tracker.db import get_db
from portfolio_tracker.controller import controller
from datetime import datetime
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET','POST'))
def register():
    '''Register with username and password.
    A unique username and password >= 8 characters is required
    '''
    username=''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        db = get_db()
        error = ''

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif len(password) < 8:
            error = 'Password must be at least 8 characters long. '
        elif password != password2:
            error = 'Passwords do not match.'
        
        if error == '':
            try:
                db.execute(
                    "INSERT INTO user (username, password, role) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), 'standard'),
                )
                db.commit()
                flash('Account created!','success')
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error,'error')

    return render_template('auth/register.html', username=username)

@bp.route('/login', methods=('GET','POST'))
def login():
    '''Log in with username and password.
    Username must exist in the database and password (hash) must match.
    '''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            db.execute('''UPDATE user SET last_login = ? WHERE id = ?''', (datetime.today().strftime('%Y-%m-%d'), user['id']))
            db.commit()

            # Update data
            load_logged_in_user()
            controller.update_info([])
            controller.update_history([], None)
            controller.update_transactions(None,None)
            return redirect(url_for('index'))

        flash(error,'error')

    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    '''Set global user information
    '''
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

@bp.route('/logout')
def logout():
    '''Clear session to log out
    '''
    session.clear()
    return redirect(url_for('main.index'))

def login_required(view):
    '''Wrapper to require login for certain functions
    '''
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('main.index'))

        return view(**kwargs)

    return wrapped_view