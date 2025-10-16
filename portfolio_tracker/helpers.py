import yfinance as yf
from flask_caching import Cache

cache = Cache()

def get_positions_table(df):
    # Generate positions table from dataframe of transactions

    # Load from cache
    prices = cache.get('prices')
    previous_closes = cache.get('previous_closes')
    if not prices:
        prices = {}
    if not previous_closes:
        previous_closes = {}
    
    # Get data if not in cache
    for tick in df['symbol'].unique():
        if tick not in prices.keys():
            prices[tick] = round(yf.Ticker(tick).fast_info.last_price,2)
        if tick not in previous_closes.keys():
            previous_closes[tick] = round(yf.Ticker(tick).fast_info.regular_market_previous_close,2)
    
    # Compile table
    df['last_price']=df['symbol'].map(prices)
    df['previous_close'] = df['symbol'].map(previous_closes)
    df['mk_val']=df['last_price']*df['quantity']
    df['previous_val']=df['previous_close']*df['quantity']
    df['cost_basis']=df['quantity']*df['share_price']
    positions=df.groupby('symbol',as_index=False).agg({'quantity':'sum', 'mk_val':'sum', 'cost_basis':'sum', 'last_price':'max','previous_val':'sum'})
    positions['gain_loss']=positions['mk_val']-positions['cost_basis']
    positions['gain_loss_pct']=round(positions['gain_loss']/positions['cost_basis']*100,2)
    positions['daily_gain_loss']=positions['mk_val']-positions['previous_val']
    positions['daily_gain_loss_pct']=round(positions['daily_gain_loss']/positions['previous_val']*100,2)
    positions.drop('previous_val',axis=1,inplace=True)
    positions.columns = ['Symbol','Qty','Mkt Val','Cost Basis','Price','Gain Loss $','Gain Loss %','Day Chng $','Day Chng %']
    positions = positions[['Symbol','Qty','Price','Mkt Val','Day Chng $','Day Chng %','Cost Basis','Gain Loss $','Gain Loss %']]
    positions.sort_values('Mkt Val',ascending=False,inplace=True)
    
    # Update cache
    cache.set("prices", prices)
    cache.set("previous_closes", previous_closes)

    return positions.to_html(classes='data', header="true")