from werkzeug.exceptions import abort
from portfolio_tracker.auth import login_required
from portfolio_tracker.db import get_db
from portfolio_tracker import cache
import pandas as pd
import yfinance as yf
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, Response
)

bp = Blueprint('transactions', __name__, url_prefix='/transactions')

@bp.route('/enter', methods=('GET','POST'))
@login_required
def enter():
    '''Enter transactions
    '''
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

        # check that symbol exists
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
            flash('Transaction Saved','success')
            tran = {}
            cache.set('update_needed',True)

        else:
            flash(error,'error')

    return render_template('transactions/enter.html', tran=tran)

@bp.route('/view', methods=('GET', 'POST'))
@login_required
def view():
    '''View transactions
    '''
    db = get_db()
    df = pd.read_sql_query('''SELECT * FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))
    trans = df.sort_values('tran_date')
    trans['tran_date'] = trans['tran_date'].apply(lambda x: pd.Timestamp(x).strftime('%m/%d/%Y'))
    trans = trans.to_dict('records')
    return render_template('transactions/view.html', trans=trans)

@bp.route('/delete/<tran_id>', methods=('GET', 'POST'))
@login_required
def delete(tran_id):
    '''Delete transaction
    ''' 
    db = get_db()
    tran=db.execute('''SELECT * FROM transactions WHERE id = ? AND user_id = ? ''', (tran_id,g.user['id'])).fetchone()
    if tran:
        db.execute('''DELETE FROM transactions WHERE id = ? AND user_id = ? ''', (tran_id,g.user['id']))
        db.commit()
        flash('Transaction deleted','success')
        cache.set('update_needed',True)
        return redirect(url_for('transactions.view'))
    else:
        return Response('401 Unauthorized',status=401)

@bp.route('/edit/<tran_id>', methods=('GET', 'POST'))
@login_required
def edit(tran_id):
    '''Edit transaction
    '''
    db = get_db()
    tran=db.execute('''SELECT * FROM transactions WHERE id = ? AND user_id = ? ''', (tran_id,g.user['id'])).fetchone()
    if tran:
        tran = dict(tran)
        tran['tran_date'] = pd.Timestamp(tran['tran_date']).strftime('%Y-%m-%d')
        
        if request.method == 'POST':
            tran_date = request.form['date']
            symbol = request.form['symbol']
            quantity = request.form['quantity']
            share_price = request.form['share-price']
            error = None

            if not tran_date:
                error = 'Date is required.'
            elif not quantity:
                error = 'quantity is required.'
            elif not share_price:
                error = 'share price is required.'
            elif not symbol:
                error = 'symbol is required.'
            
            # check that symbol exists
            test = yf.Ticker(symbol).history(period='7d',interval='1d')
            if len(test) == 0:
                error = f"symbol {symbol} not found"
            
            if error is None:
                db.execute('''UPDATE transactions
                SET tran_date = ?, symbol = ?, quantity = ?, share_price = ?
                WHERE id = ? ''', (tran_date, symbol, quantity, share_price, tran_id))
                db.commit()    
                flash('Transaction Updated','success')
                cache.set('update_needed',True)
                return redirect(url_for('transactions.view'))
                
            else:
                flash(error,'error')
        return render_template('transactions/enter.html', tran=tran)
    else:
        return Response('401 Unauthorized',status=401)