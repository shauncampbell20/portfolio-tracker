from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
)

from werkzeug.exceptions import abort
import pandas as pd
from portfolio_tracker.auth import login_required
from portfolio_tracker.db import get_db
from portfolio_tracker.helpers import get_positions_table, cache, get_history_graph

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