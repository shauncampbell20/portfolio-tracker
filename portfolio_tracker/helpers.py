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


class CacheControl:
    '''Class to facilitate updating cached data
    '''
    def __init__(self, cache):
        cache.set('status','')

    def __call__(self):
        '''Run check method if class is called
        '''
        self.check()

    def check(self):
        '''Method to check the cache and database to see if an update 
        is needed
        '''
        if cache.get('status') == 'updating':
            self.wait()
        else:
            if g.user:
                
                # Check for triggered update
                if cache.get('update_needed'):
                    self.update()
                    return

                # Check cache for presence of data elements
                prices = cache.get('prices')
                if not prices:
                    self.update()
                    return
                previous_closes = cache.get('previous_closes')
                if not previous_closes:
                    self.update()
                    return
                splits = cache.get('splits')
                if not splits:
                    self.update()
                    return
                transactions_df = cache.get('transactions_df')
                if not isinstance(transactions_df, pd.DataFrame):
                    self.update()
                    return
                history = cache.get('history')
                if not isinstance(history, pd.DataFrame):
                    self.update()
                    return
                
                # Check database for new tickers
                db = get_db()
                df = pd.read_sql_query('''SELECT * FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))
                for tick in df['symbol'].unique():
                    if tick not in prices.keys() or tick not in previous_closes.keys() or tick not in splits.keys():
                        self.update()
                        return

    def update(self):
        '''Method to update cached data
        '''
        cache.set('status','updating')
        if g.user:

            db = get_db()
            df = pd.read_sql_query('''SELECT * FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))

            if len(df) > 0:
                prices = {}
                previous_closes = {}
                splits = {}

                # cache info for each symbol
                for tick in df['symbol'].unique():
                    info = yf.Ticker(tick)
                    prices[tick] = round(info.fast_info.last_price,2)
                    previous_closes[tick] = round(info.fast_info.regular_market_previous_close,2)
                    splits[tick] = info.splits
                cache.set("prices", prices)
                cache.set("previous_closes", previous_closes)
                cache.set('splits',splits)

                # cache historical data for each symbol
                tickers=yf.Tickers(' '.join(df['symbol'].unique()))
                history = tickers.history(start=min(df['tran_date']),end=datetime.today().strftime('%Y-%m-%d'),period=None)
                history=history['Close']
                cache.set('history',history)

                # handle splits and cache recomputed transactions
                df['tran_date']=df['tran_date'].apply(pd.Timestamp)
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
                cache.set('update_needed', False)
            else:
                cache.set("prices", {})
                cache.set("previous_closes", {})
                cache.set('splits',{})
                cache.set('history',None)
                cache.set('transactions_df',None)

        cache.set('status','')

    def wait(self):
        '''Method to wait for update to finish 
        '''
        while True:
            if cache.get('status') == '':
                break
            else:
                time.sleep(.1)

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
        transactions_df = cache.get('transactions_df')

        if isinstance(transactions_df, pd.DataFrame):
            transactions_df['cost_basis']=transactions_df['quantity']*transactions_df['share_price']
            positions = transactions_df.groupby('symbol',as_index=False).agg({'quantity':'sum', 'cost_basis':'sum'})
            positions['cost_basis']=positions['cost_basis'].apply(lambda x: round(x,2))
            positions['last_price']=positions['symbol'].map(prices)
            positions['mk_val']=(positions['last_price']*positions['quantity']).apply(lambda x: round(x,2))
            positions['previous_close'] = positions['symbol'].map(previous_closes)
            positions['previous_val']=positions['previous_close']*positions['quantity']
            positions['gain_loss']=positions['mk_val']-positions['cost_basis']
            positions['gain_loss_pct']=round(positions['gain_loss']/positions['cost_basis'],4)
            positions['daily_gain_loss']=positions['mk_val']-positions['previous_val']
            positions['daily_gain_loss_pct']=round(positions['daily_gain_loss']/positions['previous_val'],4)
            positions.drop(['previous_val','previous_close'],axis=1,inplace=True)
            positions.columns = ['Symbol','Qty','Cost Basis','Price','Mkt Val','Gain Loss $','Gain Loss %','Day Chng $','Day Chng %']
            positions = positions[['Symbol','Qty','Price','Mkt Val','Day Chng $','Day Chng %','Cost Basis','Gain Loss $','Gain Loss %']]
            positions.sort_values('Mkt Val',ascending=False,inplace=True)

            styles = [
                dict(selector="th", props=[("font-size", "12px")]) 
            ]

            html = (
                positions.style
                .set_properties(**{'font-size': '10pt'})
                .map(color_positive_green, subset=['Day Chng $','Day Chng %','Gain Loss $','Gain Loss %'])
                .format({'Qty': '{:,.2f}', 'Price': '${:,.2f}', 'Mkt Val': '${:,.2f}', 'Day Chng $': '${:,.2f}', 'Cost Basis': '${:,.2f}', 'Gain Loss $': '${:,.2f}',
                        'Day Chng %': "{:.2%}", 'Gain Loss %': "{:.2%}"})
                .hide(axis='index')
                .set_table_styles(styles)
                .set_properties(header="true",index=False, justify='left')
                .set_table_attributes('class="table table-hover table-sm"')
                .to_html()
            )
            cache.set('positions_table',html)
            
            html = cache.get('positions_table')
            return html
        else:
            return ''

def get_history_graph(timeframe):
    '''Calculate and format the user's portfolio history graph
    '''
    if g.user:
        CacheController()

        history = cache.get('history')
        df = cache.get('transactions_df')
        if isinstance(df, pd.DataFrame):
            trades=df.groupby(['tran_date','symbol'],as_index=False).agg({'quantity':'sum'})
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
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=value_history.index,
                y=value_history['value'].astype(float).values.tolist(),
                mode='lines',
                name='Solid Line',
                line=dict(
                    color='green',  
                    width=2,       
                    dash='solid'   
                )
            ))
            fig.update_layout(template='plotly_white', margin=dict(l=20, r=20, t=20, b=20), autosize=True, height=275)
            return fig.to_json()
        else:
            return Response(status=204)