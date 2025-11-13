import yfinance as yf
import numpy as np
import pandas as pd
from portfolio_tracker.db import get_db
from portfolio_tracker import cache
from flask import g, Response
from datetime import datetime, timedelta

class Controller:
    '''Class to manage getting and updating data and validating transactions
    '''
    def __init__(self, cache):
        pass

    def check_transaction(self, action, tran):
        '''Validate transaction and route updates
        '''
        self.errors = []

        # Enter or Edit
        if action in ['enter','edit']:
            
            # validate transaction data
            if not tran['tran_date']:
                self.errors.append('Date is required.')
            if not tran['quantity']:
                self.errors.append('quantity is required.')
            else:
                tran['quantity'] = float(tran['quantity'])
                if tran['quantity'] < 0:
                    self.errors.append('quantity must be a positive number.')
            if not tran['share_price']:
                self.errors.append('share price is required.')
            else:
                tran['share_price'] = float(tran['share_price'])
                if tran['share_price'] < 0:
                    self.errors.append('share price must be a positive number.')
            if not tran['symbol']:
                self.errors.append('symbol is required.')
            
            if len(self.errors) > 0:
                return self.errors

            # Check if have info for symbol. If not, update cache
            self.update_info(tran['symbol'])
            if len(self.errors) > 0:
                return self.errors

            # check if history update needed
            self.update_history(tran['symbol'], tran['tran_date'])

            # update transactions and positions, if no errors, update database
            self.update_transactions(action, tran)
            self.update_positions()
            if len(self.errors)>0:
                return self.errors
            self.update_database(action, tran)

        # Delete
        elif action == 'delete':
            # update transactions and positions, if no errors, update database
            self.update_transactions(action, tran)
            self.update_positions()
            if len(self.errors) > 0:
                return self.errors
            self.update_database(action, tran)

        # Delete all
        elif action == 'delete-all':
            self.update_transactions(action, None)
            self.update_positions()
            if len(self.errors) > 0:
                return self.errors
            self.update_database(action, tran)

        # Upload
        elif action == 'upload':
            print(tran)
            # Check if have info for all symbol. If not, update cache
            symbols = tran['symbol'].unique()
            self.update_info(symbols)
            if len(self.errors) > 0:
                return self.errors

            # check if history update needed
            print(tran)
            self.update_history(symbols, min(tran['tran_date']))

            # update transactions and positions, if no errors, update database
            self.update_transactions(action, tran)
            self.update_positions()
            if len(self.errors)>0:
                return self.errors
            self.update_database(action, tran)
        return self.errors

    def update_info(self, symbols):
        ''' Check and update information for symbols
        '''
        if not hasattr(self, 'errors'):
            self.errors = []

        if len(symbols) == 0: # No symbols provided
            db = get_db()
            positions = db.execute('''SELECT DISTINCT symbol FROM positions WHERE user_id = ? ''', (g.user['id'],)).fetchall()
            symbols = [p[0] for p in positions]
        if type(symbols) == str: # Single symbol provided
            symbols = [symbols]
        info = cache.get('info')
        updates = []
        
        # info doesn't exist
        if not info:
            for symbol in symbols:
                updates.append(symbol)
            info = {}

        # new symbols
        for symbol in symbols:
            if symbol not in info.keys():
                updates.append(symbol)

        # update
        if len(updates) > 0:
            print('---update info')
            for symbol in symbols:
                try:
                    symbol_info = {}
                    ticker = yf.Ticker(symbol)
                    symbol_info['price'] = round(ticker.fast_info.last_price,2)
                    symbol_info['previous_close'] = round(ticker.fast_info.previous_close,2)
                    symbol_info['splits'] = ticker.splits
                    s, a = self._get_sectors_assets(ticker)
                    symbol_info['sectors'] = s
                    symbol_info['assets'] = a
                    info[symbol] = symbol_info
                except:
                    self.errors.append(f"symbol {symbol} not found")
        cache.set('info',info)

    def update_history(self, new_symbols, dt):
        '''Check and update price histories for symbols
        '''
        if not hasattr(self, 'errors'):
            self.errors = []

        if type(new_symbols) == str: # single symbol provided
            new_symbols = [new_symbols]
        elif len(new_symbols) == 0: # no symbols provided
            db = get_db()
            positions = db.execute('''SELECT DISTINCT symbol FROM positions WHERE user_id = ? ''', (g.user['id'],)).fetchall()
            new_symbols = [p[0] for p in positions]
        if not dt: # no minimum date provided
            db = get_db()
            dt = db.execute('''SELECT MIN(tran_date) FROM transactions WHERE user_id = ? ''', (g.user['id'],)).fetchone()[0]
        dt = pd.Timestamp(dt)
        history = cache.get('history')
        update = False

        # history exists
        if isinstance(history, pd.DataFrame): 
            symbols = list(history.columns)
            min_date = min(history.index)
            new_symbols = [s for s in new_symbols if s not in symbols]
            if len(new_symbols) > 0: # new symbols
                print('--new symbol(s)')
                update = True
                symbols.extend(new_symbols)
            if dt < min_date:
                print('--new min date')
                update = True
                min_date = dt

        # history doesn't exist
        else: 
            print('--history does not exist')
            update = True
            min_date = dt
            symbols = []
            for symbol in new_symbols:
                symbols.append(symbol)
        
        # update
        if update:
            print('---update history')
            try:
                tickers=yf.Tickers(' '.join(symbols))
                history = tickers.history(start=min_date.strftime('%Y-%m-%d'),period=None,interval='1d')
                history=history['Close'].dropna()
                cache.set('history',history)
            except:
                self.errors.append('Failed to update history')

    def update_transactions(self, action, tran):
        '''Handle splits and cache recomputed transactions
        '''
        # get transactions from database and ensure sell/fee transactions are negative
        db = get_db()
        transactions_df = pd.read_sql_query('''SELECT tran_date, symbol, quantity, share_price, tran_type, id  FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))
        transactions_df['quantity'] = transactions_df.apply(lambda x: abs(x['quantity']) if x['tran_type'] == 'BUY' else abs(x['quantity'])*-1, axis=1)
        
        if action == 'enter':
            # append new transaction row
            transactions_df = pd.concat([transactions_df, pd.DataFrame(tran, index=[0])]) 
            transactions_df.reset_index(drop=True, inplace=True)
        
        elif action == 'edit':
            # edit transaction row
            transactions_df = pd.read_sql_query('''SELECT tran_date, symbol, quantity, share_price, tran_type, id  FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))
            ind = transactions_df[transactions_df['id']==tran['id']].index
            transactions_df.loc[ind, 'tran_date'] = tran['tran_date']
            transactions_df.loc[ind, 'symbol'] = tran['symbol']
            transactions_df.loc[ind, 'quantity'] = tran['quantity']
            transactions_df.loc[ind, 'share_price'] = tran['share_price']
            transactions_df.loc[ind, 'tran_type'] = tran['tran_type']
        
        elif action == 'delete':
            # drop transaction row
            ind = transactions_df[transactions_df['id']==tran['id']].index
            transactions_df = transactions_df.drop(ind)

        elif action == 'delete-all':
            # delete all transactions
            transactions_df = pd.DataFrame()

        elif action == 'upload':
            # append new transactions
            transactions_df = pd.concat([transactions_df, tran]) 
            transactions_df.reset_index(drop=True, inplace=True)

        if len(transactions_df) > 0:
            # Handle splits
            info = cache.get('info')
            splits = {}
            for symbol in info.keys():
                splits[symbol] = info[symbol]['splits']
            transactions_df['tran_date'] = transactions_df['tran_date'].apply(pd.Timestamp)
            transactions_df['quantity'] = transactions_df.apply(lambda x: abs(x['quantity']) if x['tran_type'] == 'BUY' else abs(x['quantity'])*-1, axis=1)
            for ind, row in transactions_df.iterrows():
                try:
                    s=splits[row['symbol']]
                    s.index=s.index.tz_localize(None)
                    mult = np.cumprod(s[s.index > row['tran_date']]).values[-1]
                    transactions_df.loc[ind,'quantity'] = row['quantity']*mult
                    transactions_df.loc[ind,'share_price'] = row['share_price']/mult
                except Exception as e:
                    pass
            cache.set('transactions_df',transactions_df)
        else:
            cache.set('transactions_df',None)
        print(transactions_df)

    def update_positions(self):
        '''Update positions 
        '''
        if not hasattr(self, 'errors'):
            self.errors = []

        
        transactions_df = cache.get('transactions_df')
        if isinstance(transactions_df,pd.DataFrame):
            # calculate positions
            transactions_df = transactions_df.sort_values('tran_date')
            positions = {}
            for ind, row in transactions_df.iterrows():
                symb = row['symbol']
                if symb not in positions.keys():
                    positions[symb] = {'ur':[],'r':[]}
                # BUY
                if row['tran_type'] == 'BUY':
                    positions[symb]['ur'].append([row['quantity'],row['share_price']])
                    
                # SELL
                elif row['tran_type'] == 'SELL':
                    shares_to_sell = -row['quantity']
                    for trade in positions[symb]['ur']:
                        sold = min(shares_to_sell, trade[0])
                        shares_to_sell -= sold
                        trade[0] -= sold
                        positions[symb]['r'].append([sold, sold*trade[1], sold*row['share_price']])
                        if shares_to_sell == 0:
                            break
                    if shares_to_sell != 0:
                        self.errors.append('Not enough shares to sell')

                # FEE
                elif row['tran_type'] == 'FEE':
                    shares_to_sell = -row['quantity']
                    for trade in positions[symb]['ur']:
                        sold = min(shares_to_sell, trade[0])
                        shares_to_sell -= sold
                        trade[0] -= sold
                        positions[symb]['r'].append([sold, sold*trade[1], 0])
                        if shares_to_sell == 0:
                            break
                    if shares_to_sell != 0:
                        self.errors.append('Not enough shares to sell')

            if len(self.errors) == 0:
                cache.set('positions',positions)
                print(positions)
            else:
                # unwind
                cache.set('transactions_df',None)
                self.update_transactions(None, None)
        else:
            cache.set('positions',{})

    def update_database(self, action, tran):
        db = get_db()
        if action == 'enter':
            # Save transaction
            db.execute(
                        '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price, tran_type) 
                        VALUES (?, ?, ?, ?, ?, ?)''',
                        (g.user['id'], tran['tran_date'], tran['symbol'], tran['quantity'], tran['share_price'], tran['tran_type']),
                )
            db.commit()
        
        elif action == 'edit':
            # update transaction
            db.execute('''UPDATE transactions
                SET tran_date = ?, symbol = ?, quantity = ?, share_price = ?, tran_type = ?
                WHERE id = ? ''', (tran['tran_date'], tran['symbol'], tran['quantity'], tran['share_price'], tran['tran_type'], tran['id']))
            db.commit()    
        
        elif action == 'delete':
            # delete transaction
            db.execute('''DELETE FROM transactions WHERE id = ? AND user_id = ? ''', (tran['id'], g.user['id']))
            db.commit()

        elif action == 'delete-all':
            # delete all transactions
            db.execute('''DELETE FROM transactions WHERE user_id = ? ''', (g.user['id'],))
            db.commit()

        elif action == 'upload':
            # add multiple transactions
            for ind, row in tran.iterrows():
                db.execute(
                            '''INSERT INTO transactions (user_id, tran_date, symbol, quantity, share_price, tran_type) 
                            VALUES (?, ?, ?, ?, ?, ?)''',
                            (g.user['id'], row['tran_date'], row['symbol'], row['quantity'], row['share_price'], row['tran_type']),
                    )
                db.commit()

        # update positions
        db.execute('''DELETE FROM positions WHERE user_id = ? ''', (g.user['id'],))
        db.commit()
        positions = cache.get('positions')
        for symb in positions.keys():
            q = 0; cb = 0; rcb = 0; rv = 0
            for ur in positions[symb]['ur']:
                q += ur[0]
                cb += ur[0]*ur[1]
            for r in positions[symb]['r']:
                rcb += r[1]
                rv += r[2]
            db.execute(
                    '''INSERT INTO positions (user_id, symbol, quantity, cost_basis, realized_cost_basis, realized_value) 
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (g.user['id'], symb, q, cb, rcb, rv),
            )
            db.commit()        

    def _get_sectors_assets(self, ticker):
        '''Get sector and asset distributions for a ticker
        '''
        info = ticker.info
        ttype = info['typeDisp']

        if ttype == 'Equity':
            sector = info.get('sector')
            sector = sector.lower().replace(' ','_')
            sectors = {sector:1.0}
            assets = {'stockPosition':1.0}

        elif ttype in ['ETF','Fund']:
            fundsdata = ticker.funds_data
            sectors = fundsdata.sector_weightings
            assets = fundsdata.asset_classes

        elif ttype == 'Currency':
            sectors = {}
            assets = {'cashPosition':1.0}

        elif ttype == 'Cryptocurrency':
            sectors = {}
            assets = {'crypto':1.0}
            
        return sectors, assets

controller = Controller(cache)