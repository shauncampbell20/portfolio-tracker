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

def check_transaction(tran_type, **kwargs):
    '''Check transaction for validity and
    determine what data updates are needed based on a transaction
    '''
    errors = []
    db = get_db()
    updates_needed = ['transactions']

    if tran_type in ['enter','edit']:
        symbol = kwargs['symbol']
        tran_date = kwargs['tran_date']
        quantity = kwargs['quantity']
        share_price = kwargs['share_price']

        if not tran_date:
            errors.append('Date is required.')
        if not quantity:
            errors.append('quantity is required.')
        if not share_price:
            errors.append('share price is required.')
        if not symbol:
            errors.append('symbol is required.')
        # check that symbol exists
        if symbol:
            test = yf.Ticker(symbol).history(period='7d',interval='1d')
            if len(test) == 0:
                errors.append(f"symbol {symbol} not found")

        if len(errors) > 0:
            return ' '.join(errors)

        symbols = db.execute('''SELECT DISTINCT symbol FROM transactions WHERE  user_id = ? ''', (g.user['id'],)).fetchall()
        if symbol not in [s['symbol'] for s in symbols]:
            updates_needed.extend(['info','history'])
        else:
            min_date = db.execute('''SELECT MIN(tran_date) as tran_date FROM transactions WHERE  user_id = ? ''', (g.user['id'],)).fetchone()
            min_date = pd.Timestamp(min_date['tran_date'])
            if pd.Timestamp(tran_date) < min_date:
                updates_needed.append('history') 

    elif tran_type == 'delete':
        tran_id = kwargs['tran_id']
        tran = db.execute('''SELECT * FROM transactions WHERE id = ? AND user_id = ? ''', (tran_id,g.user['id'])).fetchone()
        if not tran: 
            return '401 Unauthorized'
    
    cache.set('updates_needed',updates_needed)

@bp.route('/enter', methods=('GET','POST'))
@login_required
def enter():
    '''Enter transactions
    '''
    tran = {}
    if request.method == 'POST':
        tran['tran_date'] = request.form['date']
        tran['symbol'] = request.form['symbol'].upper()
        tran['quantity'] = request.form['quantity']
        tran['share_price'] = request.form['share-price']
        
        errors = check_transaction('enter', symbol=tran['symbol'], tran_date=tran['tran_date'], quantity=tran['quantity'], share_price=tran['share_price'])

        if errors is None:
            db = get_db()
            #check_transaction('enter',tran['symbol'], tran['tran_date'])
            db.execute(
                    '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price) 
                    VALUES (?, ?, ?, ?, ?)''',
                    (g.user['id'], tran['tran_date'], tran['symbol'], tran['quantity'], tran['share_price']),
            )
            db.commit()   
            flash('Transaction Saved','success')
            tran = {}

        else:
            flash(errors,'error')

    return render_template('transactions/enter.html', tran=tran)

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
            symbol = request.form['symbol'].upper()
            quantity = request.form['quantity']
            share_price = request.form['share-price']
            
            errors = check_transaction('enter', symbol=tran['symbol'], tran_date=tran['tran_date'], quantity=tran['quantity'], share_price=tran['share_price'])

            if errors is None:
                db.execute('''UPDATE transactions
                SET tran_date = ?, symbol = ?, quantity = ?, share_price = ?
                WHERE id = ? ''', (tran_date, symbol, quantity, share_price, tran_id))
                db.commit()    
                flash('Transaction Updated','success')
                return redirect(url_for('transactions.view'))   
            else:
                flash(error,'error')
        return render_template('transactions/enter.html', tran=tran)
    else:
        return Response('401 Unauthorized',status=401)

@bp.route('/delete/<tran_id>', methods=('GET', 'POST'))
@login_required
def delete(tran_id):
    '''Delete transaction
    ''' 
    errors = check_transaction('delete',tran_id=tran_id)
    if errors is None:
        db = get_db()
        db.execute('''DELETE FROM transactions WHERE id = ? AND user_id = ? ''', (tran_id,g.user['id']))
        db.commit()
        flash('Transaction deleted','success')
        return redirect(url_for('transactions.view'))
    else:
        return Response(errors,status=401)

@bp.route('/view', methods=('GET', 'POST'))
@login_required
def view():
    '''View transactions
    '''
    db = get_db()
    df = pd.read_sql_query('''SELECT * FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))
    trans = df.sort_values('tran_date', ascending=False)
    trans['tran_date'] = trans['tran_date'].apply(lambda x: pd.Timestamp(x).strftime('%m/%d/%Y'))
    trans = trans.to_dict('records')
    return render_template('transactions/view.html', trans=trans)



