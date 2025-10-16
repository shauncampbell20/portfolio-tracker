from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from werkzeug.exceptions import abort

from portfolio_tracker.auth import login_required
from portfolio_tracker.db import get_db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Render main index
    return render_template('main/index.html')