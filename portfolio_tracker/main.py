from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from werkzeug.exceptions import abort
import pandas as pd
from portfolio_tracker.auth import login_required
from portfolio_tracker.db import get_db
from portfolio_tracker.helpers import get_positions_table, cache, get_history_graph

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Render main index
    positions_table = None
    history_graph = None
    if g.user:
        db = get_db()
        #df = pd.read_sql_query('''SELECT * FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))
        positions_table = get_positions_table()
        history_graph = get_history_graph()
    return render_template('main/index.html',table=positions_table, graph=history_graph)