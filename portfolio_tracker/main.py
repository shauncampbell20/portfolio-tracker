from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, jsonify, Response, session
)

from werkzeug.exceptions import abort
import pandas as pd
from portfolio_tracker.auth import login_required
from portfolio_tracker.db import get_db
from portfolio_tracker.helpers import (
    get_positions_table, get_history_graph, get_allocations_graph, get_summary_numbers, get_summary_numbers2, get_metrics
) 
from portfolio_tracker.controller import controller

bp = Blueprint('main', __name__)

@bp.route('/', methods=('GET', 'POST'))
def index():
    '''Render home page
    '''
    return render_template('main/index.html')

@bp.route('/history', methods=('GET','POST'))
def history_endpoint():
    '''Get history graph
    '''
    timeframe = request.args.get('tf')
    adj = request.args.get('adj')
    comp = request.args.get('comp')
    excluded = request.args.get('excluded')
    if comp == 'sp':
        comp = 's&p'
    return get_history_graph(timeframe, adj, comp, excluded)

@bp.route('/positions', methods=('GET','POST'))
def positions_endpoint():
    '''Get positions table
    '''
    excluded = request.args.get('excluded')
    return get_positions_table(excluded)

@bp.route('/allocations', methods=('GET','POST'))
def allocations_endpoint():
    '''Get allocations graph
    '''
    disp = request.args.get('disp')
    excluded = request.args.get('excluded')
    return get_allocations_graph(disp, excluded)

@bp.route('/summary', methods=('GET','POST'))
def summary_endpoint():
    '''Get summary data for cards
    '''
    excluded = request.args.get('excluded')
    return get_summary_numbers2(excluded)

@bp.route('/metrics', methods=('GET','POST'))
def metrics_endpoint():
    '''Get summary data for cards
    '''
    comp = request.args.get('comp')
    if comp == 'sp':
        comp = 's&p'
    excluded = request.args.get('excluded')
    return get_metrics(comp, excluded)

@bp.route('/refresh', methods=('GET','POST'))
def refresh():
    '''Refresh data
    '''
    session['info'] = None
    session['positions'] = {}
    session['transactions_df'] = None
    controller.update_info([])
    controller.update_transactions(None,None)
    controller.update_positions()
    controller.update_database(None,None)
    return redirect(url_for("main.index")) 

@bp.route('/users', methods=('GET','POST'))
def users():
    '''Get list of users if user role is admin
    '''
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
        return render_template('main/users.html', user=user)
    else:
        return Response('401 Unauthorized',status=401)