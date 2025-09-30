from werkzeug.exceptions import abort
from portfolio_tracker.auth import login_required
from portfolio_tracker.db import get_db
import pandas as pd
import yfinance as yf
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

bp = Blueprint('transactions', __name__, url_prefix='/transactions')

@bp.route('/enter', methods=('GET','POST'))
@login_required
def enter():
    tran = {}
    if request.method == 'POST':
        tran['tran_date'] = request.form['date']
        tran['symbol'] = request.form['symbol']
        tran['quantity'] = request.form['quantity']
        tran['share_price'] = request.form['share-price']
        db = get_db()
        error = None

        if not tran['tran_date']:
            error = 'Date is required.'
        elif not tran['quantity']:
            error = 'quantity is required.'
        elif not tran['share_price']:
            error = 'share price is required.'
        elif not tran['symbol']:
            error = 'symbol is required.'

        # check symbol
        test = yf.Ticker(tran['symbol']).history(period='7d',interval='1d')
        if len(test) == 0:
            error = f"symbol {tran['symbol']} not found"

        if error is None:
            db.execute(
                    '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price) 
                    VALUES (?, ?, ?, ?, ?)''',
                    (g.user['id'], tran['tran_date'], tran['symbol'].upper(), tran['quantity'], tran['share_price']),
            )
            db.commit()    
            flash('Transaction Saved')
            tran = {}
            
        else:
            flash(error)

    return render_template('transactions/enter.html', tran=tran)