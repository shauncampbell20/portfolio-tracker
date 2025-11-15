import yfinance as yf
import numpy as np
import pandas as pd
from portfolio_tracker.db import get_db
from portfolio_tracker import cache
from flask import g, Response, session
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import time
import functools

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
        info = session.get('info')
        if not info:
            return ''
        prices = {}
        previous_closes = {}
        for symbol in info.keys():
            prices[symbol] = info[symbol]['price']
            previous_closes[symbol] = info[symbol]['previous_close']

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
                .format({'Qty': '{:,.3f}', 'Price': '${:,.2f}', 'Mkt Val': '${:,.2f}', 'Day Chng $': '${:,.2f}', 'Cost Basis': '${:,.2f}', 'Rlz Gain Loss $': '${:,.2f}',
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

        history = pd.DataFrame(session.get('history'))
        transactions_df = pd.DataFrame(session.get('transactions_df'))
        info = session.get('info')
        if not info:
            return Response(status=204)

        if isinstance(transactions_df, pd.DataFrame) and len(transactions_df) > 0:
            trades=transactions_df.groupby(['tran_date','symbol'],as_index=False).agg({'quantity':'sum'})
            trades['tran_date']=pd.to_datetime(trades['tran_date'])
            history.index = pd.to_datetime(history.index)
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
        info = session.get('info')
        if not info:
            return Response(status=204)
        positions = positions=pd.read_sql_query('''SELECT * FROM positions WHERE user_id = ?''',db,params=(g.user['id'],))
        if len(positions) > 0:
            
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

            if disp == 'sector' or disp == '[object Event]':
                categories = ['Real Estate','Consumer Discretionary','Materials','Consumer Staples','Technology',
                'Communication Services','Financials','Utilities','Industrials','Energy','Healthcare']
                values = list(sector_positions.values())
            elif disp == 'asset':
                categories = ['Cash','Equities','Bonds','Preferred Stock','Convertible Bonds','Commodities','Crypto']
                values = list(asset_positions.values())
            categories=[x for _, x in sorted(zip(values, categories),reverse=False)]
            values=sorted(values,reverse=False)

            bar_trace = go.Bar(x=values, y=categories, orientation='h',marker_color='#0d6efd')
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
        info = session.get('info')
        if not info:
            return None, None, None, None, None
        for symbol in info.keys():
            prices[symbol] = info[symbol]['price']
            previous_closes[symbol] = info[symbol]['previous_close']
        try:
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
        except:
            return None, None, None, None, None
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