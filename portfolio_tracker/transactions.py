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
        else:
            if float(quantity) < 0:
                errors.append('quantity must be a positive number.')
        if not share_price:
            errors.append('share price is required.')
        else:
            if float(share_price) < 0:
                errors.append('share price must be a positive number.')
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
        tran['tran_type'] = request.form['tran_type'].upper()
        tran['quantity'] = request.form['quantity']
        tran['share_price'] = request.form['share-price']
        
        errors = check_transaction('enter', symbol=tran['symbol'], tran_date=tran['tran_date'], quantity=tran['quantity'], share_price=tran['share_price'])

        if errors is None:
            db = get_db()
            #check_transaction('enter',tran['symbol'], tran['tran_date'])
            db.execute(
                    '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price, tran_type) 
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (g.user['id'], tran['tran_date'], tran['symbol'], tran['quantity'], tran['share_price'], tran['tran_type']),
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

@bp.route('/deleteall', methods=('GET', 'POST'))
@login_required
def delete_all():
    '''Delete all of user's transactions
    '''
    if g.user:
        db = get_db()
        db.execute('''DELETE FROM transactions WHERE user_id = ? ''', (g.user['id'],))
        db.commit()
        return redirect(url_for('transactions.view'))

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

@bp.route('/upload', methods=('GET', 'POST'))
@login_required
def upload():
    if request.method == 'POST':
        try:
            df = pd.read_csv(request.files.get('formFile'))
        except:
            flash('Unable to parse file')
            return render_template('transactions/upload.html')

        date_col = request.form.get('tran_date_select')
        symb_col = request.form.get('symbol_select')
        q_col = request.form.get('quantity_select')
        price_col = request.form.get('price_select')
        type_col = request.form.get('type_select')
        if date_col == 'Select column' or symb_col == 'Select column' or q_col == 'Select column' or price_col == 'Select column':
            flash('Please select columns')
            return render_template('transactions/upload.html')
        
        errors = []
        print(symb_col)
        try:
            df[date_col] = df[date_col].apply(lambda x: pd.Timestamp(x).strftime('%Y-%m-%d'))
        except:
            errors.append(f'Unable to convert column {date_col} to date')
        try:
            df[symb_col] = df[symb_col].astype(str)
        except:
            errors.append(f'Unable to convert column {symb_col} to string')
        try:
            df[q_col] = df[q_col].astype(float)
            if len(df[df[q_col]<0]) > 0:
                errors.append('Quantity must be positive.')
        except:
            errors.append(f'Unable to convert column {q_col} to numeric')
        try:
            if df[price_col].dtype == object:
                df[price_col] = df[price_col].apply(lambda x: x.replace('$','').replace(',','').replace('(','').replace(')',''))
            df[price_col] = df[price_col].astype(float)
            if len(df[df[price_col]<0]) > 0:
                errors.append('Price must be positive.')
        except:
            errors.append(f'Unable to convert column {price_col} to numeric')
        try:
            df[type_col] = df[type_col].astype(str).apply(lambda x: x.upper())
            if len(df[(df[type_col]!='BUY')&(df[type_col]!='SELL')&(df[type_col]!='FEE')]) > 0:
                errors.append('Transaction type must be BUY, SELL, or FEE')
        except:
            errors.append(f'Unable to convert column {type_col} to numeric')
        if len(errors) > 0:
            flash('\n'.join(errors))
            return render_template('transactions/upload.html')
        
        for symbol in df[symb_col].unique():
            try:
                test = yf.Ticker(symbol).history(period='7d',interval='1d')
                if len(test) == 0:
                    errors.append(f"symbol {symbol} not found")
            except:
                errors.append(f"error retrieving data for {symbol}")
        if len(errors) > 0:
            flash('\n'.join(errors))
            return render_template('transactions/upload.html')
        
        db = get_db()
        for ind, row in df.iterrows():
            db.execute(
                        '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price, tran_type) 
                        VALUES (?, ?, ?, ?, ?, ?)''',
                        (g.user['id'], row[date_col], row[symb_col], row[q_col], row[price_col], row[type_col]),
                )
            db.commit()
        cache.set('updates_needed',['transactions', 'info', 'history'])
        flash(f'{len(df)} Transactions Uploaded')

    return render_template('transactions/upload.html')

