import yfinance as yf
import numpy as np
import pandas as pd
from portfolio_tracker.db import get_db
from portfolio_tracker import cache
from flask import g, Response
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import time
import functools


class Controller:
    def __init__(self, cache):
        pass

    def check_transaction(self, action, tran):
        self.errors = []

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

            # update history
            self.update_history(tran['symbol'], tran['tran_date'])

            # update transactions and positions
            self.update_transactions(action, tran)
            self.update_positions()
            if len(self.errors)>0:
                return self.errors
            
            # update database
            self.update_database(action, tran)

        elif action == 'delete':
            self.update_transactions('delete', None)
            self.update_positions()
            self.update_database(None, None)

        return self.errors

    def update_info(self, symbols):
        ''' Check and update information for symbols
        '''
        if not hasattr(self, 'errors'):
            self.errors = []
        if not symbols:
            db = get_db()
            positions = db.execute('''SELECT DISTINCT symbol FROM positions WHERE user_id = ? ''', (g.user['id'],)).fetchall()
            symbols = [p[0] for p in positions]
        if type(symbols) == str:
            symbols = [symbols]
        info = cache.get('info')
        updates = []
        
        # info doesn't exist
        if not info:
            for symbol in symbols:
                updates.append(symbol)
            info = {}

        # new symbol
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
        print(info)
        cache.set('info',info)

    def update_history(self, new_symbols, dt):
        '''Check and update price histories for symbols
        '''
        if not hasattr(self, 'errors'):
            self.errors = []
        if type(new_symbols) == str:
            new_symbols = [new_symbols]
        elif not new_symbols:
            db = get_db()
            positions = db.execute('''SELECT DISTINCT symbol FROM positions WHERE user_id = ? ''', (g.user['id'],)).fetchall()
            new_symbols = [p[0] for p in positions]
        if not dt:
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
                print(history)
                cache.set('history',history)
            except:
                self.errors.append('Failed to update history')

    def update_transactions(self, action, tran):
        '''Handle splits and cache recomputed transactions
        '''
        transactions_df = cache.get('transactions_df')
        db = get_db()
        if not isinstance(transactions_df, pd.DataFrame):
            transactions_df = pd.read_sql_query('''SELECT tran_date, symbol, quantity, share_price, tran_type, id  FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))
        if action == 'enter':
            transactions_df = pd.concat([transactions_df, pd.DataFrame(tran, index=[0])]) 
        elif action == 'edit':
            transactions_df = pd.read_sql_query('''SELECT tran_date, symbol, quantity, share_price, tran_type, id  FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))
            ind = transactions_df[transactions_df['id']==tran['id']].index
            transactions_df.loc[ind, 'tran_date'] = tran['tran_date']
            transactions_df.loc[ind, 'symbol'] = tran['symbol']
            transactions_df.loc[ind, 'quantity'] = tran['quantity']
            transactions_df.loc[ind, 'share_price'] = tran['share_price']
            transactions_df.loc[ind, 'tran_type'] = tran['tran_type']
        elif action == 'delete':
            transactions_df = pd.read_sql_query('''SELECT tran_date, symbol, quantity, share_price, tran_type, id  FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))

        if len(transactions_df) > 0:
            splits = cache.get('splits')
            transactions_df['tran_date'] = transactions_df['tran_date'].apply(pd.Timestamp)
            transactions_df['quantity'] = transactions_df.apply(lambda x: x['quantity'] if x['tran_type'] == 'BUY' else x['quantity']*-1, axis=1)
            for ind, row in transactions_df.iterrows():
                try:
                    s=splits[row['symbol']]
                    s.index=s.index.tz_localize(None)
                    mult = np.cumprod(s[s.index > row['tran_date']]).values[-1]
                    transactions_df.loc[ind,'quantity'] = row['quantity']*mult
                    transactions_df.loc[ind,'share_price'] = row['share_price']/mult
                except:
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
        # calculate positions
        transactions_df = cache.get('transactions_df')
        if isinstance(transactions_df,pd.DataFrame):
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
                SET tran_date = ?, symbol = ?, quantity = ?, share_price = ?
                WHERE id = ? ''', (tran['tran_date'], tran['symbol'], tran['quantity'], tran['share_price'], tran['id']))
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

def color_positive_green(val):
    '''Return color style based on val
    '''
    if isinstance(val, (int, float)):
        if val > 0:
            color = 'green'
        elif val < 0:
            color = 'red'
        else:
            color = 'black'
    else:
        color = 'black'
    return f'color: {color}'

def get_positions_table():
    '''Calculate and format the user's table of positions
    '''
    if g.user:
        info = cache.get('info')
        if not info:
            controller.update_info(None)
            controller.update_history(None, None)
            controller.update_transactions(None,None)
        prices = {}
        previous_closes = {}
        for symbol in info.keys():
            prices[symbol] = info[symbol]['price']
            previous_closes[symbol] = info[symbol]['previous_close']

        #transactions_df = cache.get('transactions_df')
        db = get_db()
        positions = pd.read_sql_query('''SELECT * FROM positions WHERE user_id = ?''', db, params=(g.user['id'],))
        if len(positions) > 0:
            positions['cost_basis']=positions['cost_basis'].apply(lambda x: round(x,2))
            positions['last_price']=positions['symbol'].map(prices)
            positions['mk_val']=(positions['last_price']*positions['quantity']).apply(lambda x: round(x,2))
            positions['previous_close'] = positions['symbol'].map(previous_closes)
            positions['previous_val']=positions['previous_close']*positions['quantity']
            positions['daily_gain_loss']=positions['mk_val']-positions['previous_val']
            positions['daily_gain_loss_pct']=round(positions['daily_gain_loss']/positions['previous_val'],4)
            positions['daily_gain_loss_pct']=positions['daily_gain_loss_pct'].fillna(0)
            positions['rlz_gain_loss']=positions['realized_value']-positions['realized_cost_basis']
            positions['urlz_gain_loss']=positions['mk_val']-positions['cost_basis']
            positions['tot_gain_loss']=positions['rlz_gain_loss']+positions['urlz_gain_loss']
            positions['tot_cost_basis']=positions['cost_basis']+positions['realized_cost_basis']
            positions['gain_loss_pct']=round(positions['tot_gain_loss']/positions['tot_cost_basis'],4)
            positions.drop(['id','user_id','realized_cost_basis','realized_value','previous_val','previous_close','cost_basis'],axis=1,inplace=True)
            positions.rename(columns={'symbol':'Symbol', 'quantity':'Qty', 'tot_cost_basis':'Cost Basis', 'last_price':'Price', 'mk_val':'Mkt Val', 
                                    'daily_gain_loss':'Day Chng $', 'daily_gain_loss_pct':'Day Chng %', 'rlz_gain_loss':'Rlz Gain Loss $', 'urlz_gain_loss':'Urlz Gain Loss $', 
                                    'tot_gain_loss':'Tot Gain Loss $', 'gain_loss_pct':'Tot Gain Loss %'}, inplace=True)
            #positions.columns = ['Symbol','Qty','Cost Basis','Price','Mkt Val','Day Chng $','Day Chng %','Gain Loss $','Gain Loss %']
            positions = positions[['Symbol','Qty','Price','Mkt Val','Day Chng $','Day Chng %','Cost Basis','Rlz Gain Loss $','Urlz Gain Loss $','Tot Gain Loss $','Tot Gain Loss %']]
            positions.sort_values('Mkt Val',ascending=False,inplace=True)

            styles = [
                dict(selector="th", props=[("font-size", "12px")]) 
            ]

            html = (
                positions.style
                .set_properties(**{'font-size': '10pt'})
                .map(color_positive_green, subset=['Day Chng $','Day Chng %','Rlz Gain Loss $', 'Urlz Gain Loss $', 'Tot Gain Loss $', 'Tot Gain Loss %'])
                .format({'Qty': '{:,.2f}', 'Price': '${:,.2f}', 'Mkt Val': '${:,.2f}', 'Day Chng $': '${:,.2f}', 'Cost Basis': '${:,.2f}', 'Rlz Gain Loss $': '${:,.2f}',
                        'Urlz Gain Loss $': '${:,.2f}', 'Tot Gain Loss $': '${:,.2f}', 'Day Chng %': "{:.2%}", 'Tot Gain Loss %': "{:.2%}"})
                .hide(axis='index')
                .set_table_styles(styles)
                .set_properties(header="true",index=False, justify='left')
                .set_table_attributes('class="table table-hover table-sm"')
                .to_html()
            )

            return html
        else:
            return ''

def get_history_graph(timeframe):
    '''Calculate and format the user's portfolio history graph
    '''
    if g.user:

        history = cache.get('history')
        transactions_df = cache.get('transactions_df')

        if isinstance(transactions_df, pd.DataFrame):
            trades=transactions_df.groupby(['tran_date','symbol'],as_index=False).agg({'quantity':'sum'})
            trades['tran_date']=pd.DatetimeIndex(trades['tran_date'])
            trades=trades.pivot(columns='symbol',index='tran_date')
            qhistory=pd.DataFrame(index=history.index).merge(trades['quantity'],left_index=True, right_index=True,how='outer')
            qhistory=qhistory.fillna(0).cumsum(axis=0)
            qhistory=qhistory[qhistory.index.isin(history.index)]
            value_history=pd.DataFrame((history*qhistory).sum(axis=1), columns=['value'])

            if timeframe:
                try:
                    value_history = value_history[value_history.index >= datetime.today()-timedelta(days=int(timeframe))]
                except:
                    pass

            value_history['value']=pd.to_numeric(value_history['value'])

            # append current value
            if value_history.index[-1] != pd.Timestamp.today().normalize():
                db = get_db()
                positions = pd.read_sql_query('''SELECT * FROM positions WHERE user_id = ?''',db,params=(g.user['id'],))
                prices = {}
                info = cache.get('info')
                for symbol in info.keys():
                    prices[symbol] = info[symbol]['price']
                positions['mkt_val'] = positions['symbol'].map(prices)*positions['quantity']
                curr_value = sum(positions['mkt_val'])
                value_history = pd.concat([value_history,pd.DataFrame({'value':curr_value}, index=[pd.Timestamp.today().normalize()])])

            color = 'green'
            if value_history['value'].astype(float).values[-1] < value_history['value'].astype(float).values[0]:
                color = 'red'
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=value_history.index,
                y=value_history['value'].astype(float).values.tolist(),
                mode='lines',
                name='Solid Line',
                line=dict(
                    color=color,  
                    width=2,       
                    dash='solid'   
                )
            ))
            fig.update_layout(
                template='plotly_white', 
                margin=dict(l=20, r=20, t=20, b=20), 
                autosize=True, 
                height=275, 
                yaxis_tickprefix = '$',
                yaxis_tickformat = ',.0f'
            )
            #fig.update_yaxes(tickformat=".4s")
            return fig.to_json()
        else:
            return Response(status=204)

def get_allocations_graph(disp):
    if g.user:
        
        # get positions
        db = get_db()
        positions = positions=pd.read_sql_query('''SELECT * FROM positions WHERE user_id = ?''',db,params=(g.user['id'],))
        if len(positions) > 0:
            info = cache.get('info')
            prices = {}
            sectors = {}
            assets = {}
            for symbol in info.keys():
                prices[symbol] = info[symbol]['price']
                sectors[symbol] = info[symbol]['sectors']
                assets[symbol] = info[symbol]['assets']
            positions['mkt_val'] = positions['symbol'].map(prices)*positions['quantity']

            # empty sector/asset allocations
            sector_positions = {
                'realestate':0,
                'consumer_cyclical':0,
                'basic_materials':0,
                'consumer_defensive':0,
                'technology':0,
                'communication_services':0,
                'financial_services':0,
                'utilities':0,
                'industrials':0,
                'energy':0,
                'healthcare':0
            }
            asset_positions = {
                'cashPosition': 0,
                'stockPosition': 0,
                'bondPosition': 0,
                'preferredPosition': 0,
                'convertiblePosition': 0,
                'otherPosition': 0,
                'crypto':0
            }

            # add to allocations
            for row in positions.values:
                for sect in sector_positions.keys():
                    if sect in sectors[row[2]].keys():
                        sector_positions[sect] += sectors[row[2]][sect]*row[7]
                for asset in asset_positions.keys():
                    if asset in assets[row[2]].keys():
                        asset_positions[asset] += assets[row[2]][asset]*row[7]
            
            # convert to percentage
            total = sum(positions['mkt_val'])
            for sect in sector_positions.keys():
                sector_positions[sect] = sector_positions[sect]/total
            for asset in asset_positions.keys():
                asset_positions[asset] = asset_positions[asset]/total
            print('disp:',type(disp))
            if disp == 'sector' or disp == '[object Event]':
                categories = ['Real Estate','Consumer Discretionary','Materials','Consumer Staples','Technology',
                'Communication Services','Financials','Utilities','Industrials','Energy','Healthcare']
                values = list(sector_positions.values())
            elif disp == 'asset':
                categories = ['Cash','Equities','Bonds','Preferred Stock','Convertible Bonds','Commodities','Crypto']
                values = list(asset_positions.values())
            categories=[x for _, x in sorted(zip(values, categories),reverse=False)]
            values=sorted(values,reverse=False)

            bar_trace = go.Bar(x=values, y=categories, orientation='h')
            fig = go.Figure(data=[bar_trace])
            fig.update_layout(
                template='plotly_white', 
                margin=dict(l=20, r=20, t=20, b=20),
                 autosize=True, 
                 height=275,
                 xaxis_tickformat=".1%"
            )
            return fig.to_json()
        else:
            return Response(status=204)

def get_summary_numbers():
    if g.user:

        db = get_db()
        positions = positions=pd.read_sql_query('''SELECT * FROM positions WHERE user_id = ?''',db,params=(g.user['id'],))
        prices = {}
        previous_closes = {}
        info = cache.get('info')
        for symbol in info.keys():
            prices[symbol] = info[symbol]['price']
            previous_closes[symbol] = info[symbol]['previous_close']

        positions['mkt_val'] = positions['symbol'].map(prices)*positions['quantity']
        curr_value = sum(positions['mkt_val'])
        curr_value_str = f"${curr_value:,.2f}"

        positions['previous_close'] = positions['symbol'].map(previous_closes)
        positions['previous_val']=positions['previous_close']*positions['quantity']
        positions['daily_gain_loss']=positions['mkt_val']-positions['previous_val']
        daily_gain_loss = sum(positions['daily_gain_loss'])
        daily_gain_loss_pct = (sum(positions['daily_gain_loss'])/sum(positions['previous_val']))
        daily_prefix = '+'
        if daily_gain_loss < 0:
            daily_prefix = '-'
        daily_str = f"{daily_prefix}${abs(daily_gain_loss):,.2f} ({abs(daily_gain_loss_pct):.2%})"

        positions['rlz_gain_loss']=positions['realized_value']-positions['realized_cost_basis']
        positions['urlz_gain_loss']=positions['mkt_val']-positions['cost_basis']
        positions['tot_gain_loss']=positions['rlz_gain_loss']+positions['urlz_gain_loss']
        positions['tot_cost_basis']=positions['cost_basis']+positions['realized_cost_basis']
        tot_gain_loss = sum(positions['tot_gain_loss'])
        tot_gain_loss_pct = sum(positions['tot_gain_loss'])/sum(positions['tot_cost_basis'])
        tot_prefix = '+'
        if tot_gain_loss < 0:
            tot_prefix = '-'
        tot_str = f"{tot_prefix}${abs(tot_gain_loss):,.2f} ({abs(tot_gain_loss_pct):.2%})"

        dgl_col = 'color-green'
        tot_col = 'color-green'
        if daily_gain_loss < 0:
            dgl_col = 'color-red'
        if tot_gain_loss < 0:
            tot_col = 'color-red'
        return curr_value_str, daily_str, tot_str, dgl_col, tot_col
    else:
        return None, None, None, None, None

def get_summary_numbers2():
    curr_value_str, daily_str, tot_str, dgl_col, tot_col = get_summary_numbers()
    return {
        'curr_value_str':curr_value_str,
        'daily_str':daily_str,
        'tot_str':tot_str,
        'dgl_col':dgl_col,
        'tot_col':tot_col
    }