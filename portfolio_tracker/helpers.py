import yfinance as yf
from flask_caching import Cache
import numpy as np
import pandas as pd
from portfolio_tracker.db import get_db
from flask import g 
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

cache = Cache()

def get_transactions():
    if g.user:

        db = get_db()
        df = pd.read_sql_query('''SELECT * FROM transactions WHERE user_id = ?''', db, params=(g.user['id'],))

        # Load from cache
        prices = cache.get('prices')
        previous_closes = cache.get('previous_closes')
        splits = cache.get('splits')
        if not prices:
            prices = {}
        if not previous_closes:
            previous_closes = {}
        if not splits:
            splits = {}

        # Get data if not in cache
        for tick in df['symbol'].unique():
            if tick not in prices.keys() or tick not in previous_closes.keys() or tick not in splits.keys():
                info = yf.Ticker(tick)
                prices[tick] = round(info.fast_info.last_price,2)
                previous_closes[tick] = round(info.fast_info.regular_market_previous_close,2)
                splits[tick] = info.splits

        # handle splits
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

        # Compile table
        df['last_price']=df['symbol'].map(prices)
        df['previous_close'] = df['symbol'].map(previous_closes)
        df['mk_val']=df['last_price']*df['quantity']
        df['previous_val']=df['previous_close']*df['quantity']
        df['cost_basis']=df['quantity']*df['share_price']

        # Update cache
        cache.set("prices", prices)
        cache.set("previous_closes", previous_closes)
        cache.set('splits',splits)
        cache.set('transactions',df)
    
        return df


def get_positions_table():
    # Generate positions table from dataframe of transactions
    df = get_transactions()
    
    if len(df) > 0:
        positions=df.groupby('symbol',as_index=False).agg({'quantity':'sum', 'mk_val':'sum', 'cost_basis':'sum', 'last_price':'max','previous_val':'sum'})
        positions['mk_val']=positions['mk_val'].apply(lambda x: round(x,2))
        positions['cost_basis']=positions['cost_basis'].apply(lambda x: round(x,2))
        positions['gain_loss']=positions['mk_val']-positions['cost_basis']
        positions['gain_loss_pct']=round(positions['gain_loss']/positions['cost_basis']*100,2)
        positions['daily_gain_loss']=positions['mk_val']-positions['previous_val']
        positions['daily_gain_loss_pct']=round(positions['daily_gain_loss']/positions['previous_val']*100,2)
        positions.drop('previous_val',axis=1,inplace=True)
        positions.columns = ['Symbol','Qty','Mkt Val','Cost Basis','Price','Gain Loss $','Gain Loss %','Day Chng $','Day Chng %']
        positions = positions[['Symbol','Qty','Price','Mkt Val','Day Chng $','Day Chng %','Cost Basis','Gain Loss $','Gain Loss %']]
        positions.sort_values('Mkt Val',ascending=False,inplace=True)

        return positions.to_html(classes='table', header="true",index=False)

def get_historical():
    df = get_transactions()
    history = cache.get('history')
    if not isinstance(history, pd.DataFrame):
        tickers=yf.Tickers(' '.join(df['symbol'].unique()))
        history = tickers.history(start=min(df['tran_date']),end=datetime.today().strftime('%Y-%m-%d'),period=None)
        history=history['Close']
        cache.set('history',history)
    
    return history

def get_history_graph():
    df = get_transactions()
    if len(df) > 0:
        history = get_historical()
        trades=df.groupby(['tran_date','symbol'],as_index=False).agg({'quantity':sum})
        trades['tran_date']=pd.DatetimeIndex(trades['tran_date'])
        trades=trades.pivot(columns='symbol',index='tran_date')
        qhistory=pd.DataFrame(index=history.index).merge(trades['quantity'],left_index=True, right_index=True,how='outer')
        qhistory=qhistory.fillna(0).cumsum(axis=0)
        qhistory=qhistory[qhistory.index.isin(history.index)]
        value_history=pd.DataFrame((history*qhistory).sum(axis=1), columns=['value'])
        #fig = px.line(value_history, x=value_history.index, y="value", title='Portfolio Value')
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=value_history.index,
            y=value_history['value'],
            mode='lines',
            name='Solid Line',
            line=dict(
                color='green',  
                width=2,       
                dash='solid'   
            )
        ))
        fig.update_layout(template='plotly_white')
        return fig.to_html()