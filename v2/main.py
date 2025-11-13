from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, jsonify, Response
)

from werkzeug.exceptions import abort
import pandas as pd
from portfolio_tracker.auth import login_required
from portfolio_tracker.db import get_db
from portfolio_tracker.helpers import get_positions_table, cache, get_history_graph, get_allocations_graph, get_summary_numbers, get_summary_numbers2

bp = Blueprint('main', __name__)

@bp.route('/', methods=('GET', 'POST'))
def index(tf=None):
    return render_template('main/index.html')

@bp.route('/history', methods=('GET','POST'))
def history_endpoint():
    timeframe = request.args.get('tf')
    return get_history_graph(timeframe)

@bp.route('/positions', methods=('GET','POST'))
def positions_endpoint():
    return get_positions_table()

@bp.route('/allocations', methods=('GET','POST'))
def allocations_endpoint():
    disp = request.args.get('disp')
    return get_allocations_graph(disp)

@bp.route('/summary', methods=('GET','POST'))
def summary_endpoint():
    return get_summary_numbers2()

@bp.route('/users', methods=('GET','POST'))
def users():
    if g.user['role'] == 'admin':
        db = get_db()
        user = pd.read_sql_query('''SELECT 
                                    user.id, user.username, user.role, user.last_login,
                                    COUNT(transactions.id) as transactions
                                    FROM user
                                    LEFT JOIN transactions ON user.id = transactions.user_id
                                    GROUP BY 
                                    user.id, user.username, user.role, user.last_login
                                    ''',db)
        user['last_login'] = user['last_login'].apply(lambda x: pd.Timestamp(x).strftime('%m/%d/%Y') if not pd.isna(x) else '')
        user = user.to_dict('records')
        print(user)
        return render_template('main/users.html', user=user)
    else:
        return Response('401 Unauthorized',status=401)