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

def get_positions_table(excluded=None):
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

        if excluded:
            to_exclude = excluded.split(',')
            positions = positions[~positions['symbol'].isin(to_exclude)]

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

def calculate_value_history(transactions_df, history):
    transactions_df['cost'] = transactions_df['quantity']*transactions_df['share_price']
    trades=transactions_df.groupby(['tran_date','symbol'],as_index=False).agg({'quantity':'sum','cost':'sum'})
    trades['tran_date']=pd.to_datetime(trades['tran_date'])
    history.index = pd.to_datetime(history.index)
    trades=trades.pivot(columns='symbol',index='tran_date')
    total_cost = sum(transactions_df.apply(lambda x: abs(x['quantity'])*x['share_price'] if x['tran_type'] == 'BUY' else 0, axis=1))
    total_sell = sum(transactions_df.apply(lambda x: abs(x['quantity'])*x['share_price'] if x['tran_type'] == 'SELL' else 0, axis=1))

    qhistory=pd.DataFrame(index=history.index).merge(trades['quantity'],left_index=True, right_index=True,how='outer')
    qhistory=qhistory.fillna(0).cumsum(axis=0)
    qhistory=qhistory[qhistory.index.isin(history.index)]
    value_history=pd.DataFrame((history*qhistory).sum(axis=1), columns=['value'])

    chistory=pd.DataFrame(index=history.index).merge(trades['cost'],left_index=True, right_index=True,how='outer')
    chistory=chistory.fillna(0).cumsum(axis=0)
    chistory=chistory[chistory.index.isin(history.index)]
    cost_history = pd.DataFrame(chistory.sum(axis=1),columns=['cost'])

    value_history = value_history.merge(cost_history,left_index=True, right_index=True)
    value_history['adj_value'] = value_history['value']-value_history['cost']+total_cost-total_sell
    value_history['adj_value2'] = value_history['value']-value_history['cost']+total_cost
    start_ind = value_history[value_history['value'] != 0].index[0]
    value_history = value_history[start_ind:]
    return value_history

def get_history_graph(timeframe, adj=False, comp=None, excluded=None):
    '''Calculate and format the user's portfolio history graph
    '''
    if comp == 'undefined':
        comp = None
    if g.user:
        history = pd.DataFrame(session.get('history'))
        transactions_df = pd.DataFrame(session.get('transactions_df'))
        info = session.get('info')
        if not info:
            return Response(status=204)

        if isinstance(transactions_df, pd.DataFrame) and len(transactions_df) > 0:
            if excluded:
                to_exclude = excluded.split(',')
                transactions_df = transactions_df[~transactions_df['symbol'].isin(to_exclude)]
                if len(transactions_df) == 0:
                    return Response(status=204)

            value_history = calculate_value_history(transactions_df, history)
            value_history['value']=pd.to_numeric(value_history['value'])
            
            # timeframe
            if timeframe:
                try:
                    value_history = value_history[value_history.index >= datetime.today()-timedelta(days=int(timeframe))]
                    
                except:
                    pass

            history = history[history.index >= value_history.index[0]]
            value_history['s&p'] = np.cumprod(history['^GSPC'].pct_change().fillna(0)+1)*value_history['adj_value'].iloc[0]
            value_history['dji'] = np.cumprod(history['^DJI'].pct_change().fillna(0)+1)*value_history['adj_value'].iloc[0]
            value_history['nasdaq'] = np.cumprod(history['^IXIC'].pct_change().fillna(0)+1)*value_history['adj_value'].iloc[0]
            # adjusted
            plot_col = 'value'
            if adj == "True":
                plot_col = 'adj_value'

            color = 'green'
            if value_history['adj_value'].astype(float).values[-1] < value_history['adj_value'].astype(float).values[0]:
                color = 'red'
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=value_history.index,
                y=value_history[plot_col].astype(float).values.tolist(),
                mode='lines',
                name='Your Portfolio',
                line=dict(
                    color=color,  
                    width=2,       
                    dash='solid'   
                )
            ))
            
            # comparison
            if comp:
                fig.add_trace(go.Scatter(
                x=value_history.index,
                y=value_history[comp].astype(float).values.tolist(),
                mode='lines',
                name=comp.upper(),
                line=dict(
                    color='blue',  
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

def get_allocations_graph(disp, excluded=None):
    if g.user:
        
        # get positions
        db = get_db()
        info = session.get('info')
        if not info:
            return Response(status=204)
        
        positions = positions=pd.read_sql_query('''SELECT * FROM positions WHERE user_id = ?''',db,params=(g.user['id'],))
        if excluded:
            to_exclude = excluded.split(',')
            positions = positions[~positions['symbol'].isin(to_exclude)]

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

def get_summary_numbers(excluded=None):
    if g.user:

        db = get_db()
        positions = positions=pd.read_sql_query('''SELECT * FROM positions WHERE user_id = ?''',db,params=(g.user['id'],))
        if excluded:
            to_exclude = excluded.split(',')
            positions = positions[~positions['symbol'].isin(to_exclude)]
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

def get_summary_numbers2(excluded=None):
    curr_value_str, daily_str, tot_str, dgl_col, tot_col = get_summary_numbers(excluded)
    return {
        'curr_value_str':curr_value_str,
        'daily_str':daily_str,
        'tot_str':tot_str,
        'dgl_col':dgl_col,
        'tot_col':tot_col
    }

def calc_ror(data, offset):
    if offset == 'all':
        offset = (data.index[-1]-data.index[0]).days
    start = datetime.today()-timedelta(days=int(offset))
    if start < data.index[0]:
        return 0
    data = data[data.index >= start]
    total_r=data.iloc[-1]/data.iloc[0]
    N = offset/365.25
    return total_r**(1/N)-1

def simple_linear_regression(x, y):
    n = len(x)
    
    mean_x = np.mean(x)
    mean_y = np.mean(y)
    
    numerator = np.sum((x - mean_x) * (y - mean_y))
    denominator = np.sum((x - mean_x)**2)
    
    if denominator == 0:  
        return 0, mean_y  
    
    m = numerator / denominator
    c = mean_y - m * mean_x
    
    return m, c

def calc_beta_alpha(data, col, offset):
    if offset != 'all':
        start = datetime.today()-timedelta(days=int(offset))
        if start < data.index[0]:
            return 0,0
        data = data[data.index >= start]
    porto_returns = data[col].pct_change().dropna()
    comp_returns = data['s&p'].pct_change().dropna()
    beta, alpha = simple_linear_regression(comp_returns, porto_returns)
    return beta, alpha

def calculate_sharpe_ratio(data, col, offset):
    if offset != 'all':
        start = datetime.today()-timedelta(days=int(offset))
        if start < data.index[0]:
            return 0
        data = data[data.index >= start]
    rx = np.mean(data[col].pct_change().dropna())
    rf = np.mean(data['tips'])/100/252
    std = np.std(data[col].pct_change().dropna())
    print(offset, rx, rf, std)
    return ((rx-rf)/std)*np.sqrt(252)

def get_metrics(comp=None, excluded=None):
    if comp == 'undefined':
        comp = None
    if g.user:
    
        history = pd.DataFrame(session.get('history'))
        transactions_df = pd.DataFrame(session.get('transactions_df'))
        if isinstance(transactions_df, pd.DataFrame) and len(transactions_df) > 0:
            if excluded:
                to_exclude = excluded.split(',')
                transactions_df = transactions_df[~transactions_df['symbol'].isin(to_exclude)]
                if len(transactions_df) == 0:
                    return Response(status=204)

            value_history = calculate_value_history(transactions_df, history)
            value_history['s&p'] = history['^GSPC']
            value_history['dji'] = history['^DJI']
            value_history['nasdaq'] = history['^IXIC']
            value_history['tips'] = history['^TNX']
            print(value_history)
            ror = [calc_ror(value_history['adj_value2'], off) for off in [30,91,182,365,1095,'all']]
            alpha_beta = [calc_beta_alpha(value_history, 'value', off) for off in [30,91,182,365,1095,'all']]
            sharpe = [calculate_sharpe_ratio(value_history,'adj_value2', off) for off in [30,91,182,365,1095,'all']]
            
            if comp:
                ror_comp = [calc_ror(value_history['s&p'], off) for off in [30,91,182,365,1095,'all']]
                alpha_beta_comp = [calc_beta_alpha(value_history, comp, off) for off in [30,91,182,365,1095,'all']]
                sharpe_comp = [calculate_sharpe_ratio(value_history, comp, off) for off in [30,91,182,365,1095,'all']]
                metrics=pd.concat([pd.DataFrame(ror).T, pd.DataFrame(ror_comp).T, pd.DataFrame(alpha_beta).T, pd.DataFrame(alpha_beta_comp).T, pd.DataFrame(sharpe).T, pd.DataFrame(sharpe_comp).T])
                metrics.index=['Annualized ROR',comp.upper()+' Annualized ROR','Beta','Alpha',comp.upper()+' Beta',comp.upper()+' Alpha','Sharpe Ratio',comp.upper()+' Sharpe Ratio']
                metrics = metrics.reindex(['Annualized ROR',comp.upper()+' Annualized ROR','Beta',comp.upper()+' Beta','Alpha',comp.upper()+' Alpha','Sharpe Ratio',comp.upper()+' Sharpe Ratio'])
                pctsubset = ['Annualized ROR',comp.upper()+' Annualized ROR']
                fltsubset = ['Beta','Alpha','Sharpe Ratio',comp.upper()+' Beta',comp.upper()+' Alpha',comp.upper()+' Sharpe Ratio']
                #fillsubset = [comp.upper()+' Annualized ROR',comp.upper()+' Beta',comp.upper()+' Alpha',comp.upper()+' Sharpe Ratio']
                attr = 'class="table table table-striped table-sm'
            else:
                metrics=pd.concat([pd.DataFrame(ror).T, pd.DataFrame(alpha_beta).T, pd.DataFrame(sharpe).T])
                metrics.index=['Annualized ROR','Beta','Alpha','Sharpe Ratio']
                pctsubset = ['Annualized ROR']
                fltsubset = ['Beta','Alpha','Sharpe Ratio']
                #fillsubset=[]
                attr = 'class="table table-hover table-sm'
            metrics.columns=['1M','3M','6M','1Y','3Y','All']
            print(metrics)
            styles = [
                dict(selector="th", props=[("font-size", "12px")]) 
            ]

            if comp:
                html = (
                    metrics.style
                    .set_properties(**{'font-size': '10pt'})
                    .map(color_positive_green, subset=(['Annualized ROR',comp.upper()+' Annualized ROR'], slice(None)))
                    .format("{:.2%}", subset=(['Annualized ROR',comp.upper()+' Annualized ROR'], slice(None)))
                    .format("{:.3f}", subset=(['Beta',comp.upper()+' Beta','Alpha',comp.upper()+' Alpha','Sharpe Ratio',comp.upper()+' Sharpe Ratio'], slice(None)))
                    .set_table_styles(styles)
                    .set_properties(header="true", justify='left')
                    .set_table_attributes('class="table table-hover table-striped table-sm"')
                    .to_html()
                )
            else:
                html = (
                    metrics.style
                    .set_properties(**{'font-size': '10pt'})
                    .map(color_positive_green, subset=(['Annualized ROR'], slice(None)))
                    .format("{:.2%}", subset=(['Annualized ROR'], slice(None)))
                    .format("{:.3f}", subset=(['Beta','Alpha','Sharpe Ratio'], slice(None)))
                    .set_table_styles(styles)
                    .set_properties(header="true", justify='left')
                    .set_table_attributes('class="table table-hover table-sm"')
                    .to_html()
                )
            
            return html
