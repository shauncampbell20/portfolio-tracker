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

class CacheControl:
    '''Class to facilitate updating cached data
    '''
    def __init__(self, cache):
        cache.set('status','')

    def __call__(self):
        '''Run check method if class is called
        '''
        print(cache.get('status'))
        self.check()

    def check(self):
        '''Check to see if updates are needed
        '''
        if cache.get('status') == 'updating':
            self.wait()
        else:
            if g.user:
                
                # Check for updates
                updates_needed = cache.get('updates_needed')
                if updates_needed == None:
                    updates_needed = ['transactions','info','history']
                print(updates_needed)
                if len(updates_needed) > 0:
                    cache.set('status','updating')
                    db = get_db()
                    self.df = pd.read_sql_query('''SELECT * FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))
                    if 'info' in updates_needed:
                        self.update_info()
                    if 'history' in updates_needed:
                        self.update_history()
                    if 'transactions' in updates_needed:
                        self.update_transactions()
                    self.update_positions()
                    cache.set('updates_needed',[])
                    cache.set('status','')

    def update_info(self):
        '''Update info (prices, previous closes, splits)
        '''
        if len(self.df) > 0:
            prices = {}
            previous_closes = {}
            splits = {}
            sectors = {}
            assets = {}
            # cache info for each symbol
            for symbol in self.df['symbol'].unique():
                ticker = yf.Ticker(symbol)
                prices[symbol] = round(ticker.fast_info.last_price,2)
                previous_closes[symbol] = round(ticker.fast_info.previous_close,2)
                splits[symbol] = ticker.splits
                s, a = self._get_sectors_assets(ticker)
                sectors[symbol] = s
                assets[symbol] = a
            cache.set("prices", prices)
            cache.set("previous_closes", previous_closes)
            cache.set('splits',splits)
            cache.set('sectors',sectors)
            cache.set('assets',assets)
        else:
            cache.set('prices',{})
            cache.set('previous_closes',{})
            cache.set('splits',{})
            cache.set('sectors',{})
            cache.set('assets',{})

    def update_history(self):
        '''Update price history
        '''
        if len(self.df) > 0:
            tickers=yf.Tickers(' '.join(self.df['symbol'].unique()))
            history = tickers.history(start=min(self.df['tran_date']),period=None,interval='1d')#,end=(datetime.today()+timedelta(days=1)).strftime('%Y-%m-%d')
            history=history['Close'].dropna()
            cache.set('history',history)
        else:
            cache.set('history',None)

    def update_transactions(self):
        '''Handle splits and cache recomputed transactions
        '''
        if len(self.df) > 0:
            df = self.df.copy()
            splits = cache.get('splits')
            df['tran_date']=df['tran_date'].apply(pd.Timestamp)
            df['quantity'] = df.apply(lambda x: x['quantity'] if x['tran_type'] == 'BUY' else x['quantity']*-1, axis=1)
            for ind, row in df.iterrows():
                try:
                    s=splits[row['symbol']]
                    s.index=s.index.tz_localize(None)
                    mult = np.cumprod(s[s.index > row['tran_date']]).values[-1]
                    df.loc[ind,'quantity'] = row['quantity']*mult
                    df.loc[ind,'share_price'] = row['share_price']/mult
                except:
                    pass
            cache.set('transactions_df',df)
        else:
            cache.set('transactions_df',None)

    def update_positions(self):
        '''Update positions table for user
        '''
        db=get_db()
        db.execute('''DELETE FROM positions WHERE user_id = ? ''', (g.user['id'],))
        db.commit()
        
        # calculate positions
        transactions_df = cache.get('transactions_df')
        if isinstance(transactions_df,pd.DataFrame):
            transactions_df = transactions_df.sort_values('tran_date')
            positions = {}
            for row in transactions_df.values:
                symb = row[3]
                if symb not in positions.keys():
                    positions[symb] = {'ur':[],'r':[]}
                # BUY
                if row[6] == 'BUY':
                    positions[symb]['ur'].append([row[4],row[5]])
                    
                # SELL
                elif row[6] == 'SELL':
                    shares_to_sell = -row[4]
                    for trade in positions[symb]['ur']:
                        sold = min(shares_to_sell, trade[0])
                        shares_to_sell -= sold
                        trade[0] -= sold
                        positions[symb]['r'].append([sold, sold*trade[1], sold*row[5]])
                        if shares_to_sell == 0:
                            break
                    if shares_to_sell != 0:
                        raise ValueError('Not enough shares to sell')

                # FEE
                elif row[6] == 'FEE':
                    shares_to_sell = -row[4]
                    for trade in positions[symb]['ur']:
                        sold = min(shares_to_sell, trade[0])
                        shares_to_sell -= sold
                        trade[0] -= sold
                        positions[symb]['r'].append([sold, sold*trade[1], 0])
                        if shares_to_sell == 0:
                            break
                    if shares_to_sell != 0:
                        raise ValueError('Not enough shares to sell')

            # update database
            print(positions)
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

    def wait(self):
        '''Method to wait for update to finish 
        '''
        while True:
            if cache.get('status') == '':
                break
            else:
                time.sleep(.1)

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

CacheController = CacheControl(cache)

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
        CacheController()
        
        prices = cache.get('prices')
        previous_closes = cache.get('previous_closes')
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
        CacheController()

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
            cache.set('value_history',value_history)

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
                prices = cache.get('prices')
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
        CacheController()

        # get positions
        db = get_db()
        positions = positions=pd.read_sql_query('''SELECT * FROM positions WHERE user_id = ?''',db,params=(g.user['id'],))
        if len(positions) > 0:
            prices = cache.get('prices')
            sectors = cache.get('sectors')
            assets = cache.get('assets')
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
        CacheController()

        db = get_db()
        positions = positions=pd.read_sql_query('''SELECT * FROM positions WHERE user_id = ?''',db,params=(g.user['id'],))
        prices = cache.get('prices')
        positions['mkt_val'] = positions['symbol'].map(prices)*positions['quantity']
        curr_value = sum(positions['mkt_val'])
        curr_value_str = f"${curr_value:,.2f}"

        previous_closes = cache.get('previous_closes')
        positions['previous_close'] = positions['symbol'].map(previous_closes)
        positions['previous_val']=positions['previous_close']*positions['quantity']
        positions['daily_gain_loss']=positions['mkt_val']-positions['previous_val']
        daily_gain_loss = sum(positions['daily_gain_loss'])
        daily_gain_loss_pct = (sum(positions['daily_gain_loss'])/sum(positions['previous_val']))
        daily_prefix = '+'
        if daily_gain_loss < 0:
            daily_prefix = '-'
        daily_str = f"{daily_prefix}${daily_gain_loss:,.2f} ({daily_gain_loss_pct:.2%})"

        positions['rlz_gain_loss']=positions['realized_value']-positions['realized_cost_basis']
        positions['urlz_gain_loss']=positions['mkt_val']-positions['cost_basis']
        positions['tot_gain_loss']=positions['rlz_gain_loss']+positions['urlz_gain_loss']
        positions['tot_cost_basis']=positions['cost_basis']+positions['realized_cost_basis']
        tot_gain_loss = sum(positions['tot_gain_loss'])
        tot_gain_loss_pct = sum(positions['tot_gain_loss'])/sum(positions['tot_cost_basis'])
        tot_prefix = '+'
        if tot_gain_loss < 0:
            tot_prefix = '-'
        tot_str = f"{tot_prefix}${tot_gain_loss:,.2f} ({tot_gain_loss_pct:.2%})"

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