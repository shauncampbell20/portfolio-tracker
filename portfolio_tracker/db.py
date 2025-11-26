import sqlite3
from datetime import datetime
import click
from flask import current_app, g
from werkzeug.security import check_password_hash, generate_password_hash

def get_db():
    '''Get and return a database connection
    '''
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    '''Close database connection
    '''
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    '''Initialize the database tables
    '''
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

    # Sample accounts and transactions
    db.execute(
        "INSERT INTO user (username, password, role) VALUES (?, ?, ?)",
        ('admin', generate_password_hash('12345678'), 'admin'),
    )
    db.execute(
        "INSERT INTO user (username, password, role, last_login) VALUES (?, ?, ?, ?)",
        ('test1', generate_password_hash('12345678'), 'standard', '2025-11-15'),
    )
    db.execute(
        "INSERT INTO user (username, password, role, last_login) VALUES (?, ?, ?, ?)",
        ('test2', generate_password_hash('12345678'), 'standard','2025-10-07'),
    )
    db.execute(
        '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price, tran_type) VALUES (?, ?, ?, ?, ?, ?)''',
        (2,'2022-11-15','GLD',20,165.5,'BUY')
    )
    db.execute(
        '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price, tran_type) VALUES (?, ?, ?, ?, ?, ?)''',
        (2,'2022-11-15','SPY',100,382.43,'BUY')
    )
    db.execute(
        '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price, tran_type) VALUES (?, ?, ?, ?, ?, ?)''',
        (2,'2022-11-15','BTC-USD',0.1,16884.61,'BUY')
    )
    db.execute(
        '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price, tran_type) VALUES (?, ?, ?, ?, ?, ?)''',
        (2,'2022-11-15','BND',200,64.63,'BUY')
    )
    db.execute(
        '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price, tran_type) VALUES (?, ?, ?, ?, ?, ?)''',
        (2,'2022-11-15','AAPL',100,150.04,'BUY')
    )
    db.commit()


@click.command('init-db')
def init_db_command():
    '''Clear the existing data and create new tables
    '''
    init_db()
    click.echo('Initialized the database.')


sqlite3.register_converter(
    "timestamp", lambda v: datetime.fromisoformat(v.decode())
)

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)