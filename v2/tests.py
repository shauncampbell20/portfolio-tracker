from portfolio_tracker.helpers import Controller
from portfolio_tracker import cache
from portfolio_tracker.db import get_db
from . import create_app
import click
from flask import g
import pandas as pd

@click.command('test')
def test_command():
    app = create_app()
    with app.app_context():
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (1,)
        ).fetchone()
        controller = Controller(cache)
        test1 = False
        test2 = True
        if test1:
            print('# invalid transaction')
            errors = controller.check_transaction('enter',
                {'tran_date': '2025-01-02',
                'symbol': 'SPY',
                'tran_type': 'BUY',
                'quantity': '1',
                'share_price': '-350'}
            )
            print(errors)
            print('# invalid symbol')
            errors = controller.check_transaction('enter',
                {'tran_date': '2025-01-02',
                'symbol': 'FAKESYMBOL',
                'tran_type': 'BUY',
                'quantity': '1',
                'share_price': '350'}
            )
            print(errors)
            print('# valid transaction')
            errors = controller.check_transaction('enter',
                {'tran_date': '2025-01-02',
                'symbol': 'SPY',
                'tran_type': 'BUY',
                'quantity': '1',
                'share_price': '350'}
            )
            print(errors)
            print('# same symbol')
            errors = controller.check_transaction('enter',
                {'tran_date': '2025-01-02',
                'symbol': 'SPY',
                'tran_type': 'BUY',
                'quantity': '1',
                'share_price': '350'}
            )
            print(errors)
            print('# same symbol, new min date')
            errors = controller.check_transaction('enter',
                {'tran_date': '2024-01-02',
                'symbol': 'SPY',
                'tran_type': 'BUY',
                'quantity': '1',
                'share_price': '350'}
            )
            print(errors)
            print('# new symbol')
            errors = controller.check_transaction('enter',
                {'tran_date': '2025-01-02',
                'symbol': 'TSLA',
                'tran_type': 'BUY',
                'quantity': '1',
                'share_price': '350'}
            )
            print(errors)
            print('# not enough shares to sell')
            errors = controller.check_transaction('enter',
                {'tran_date': '2025-01-02',
                'symbol': 'MSFT',
                'tran_type': 'SELL',
                'quantity': '1',
                'share_price': '350'}
            )
            print(errors)
        elif test2:
            # tran = {'tran_date': '2025-01-02',
            #     'symbol': 'TSLA',
            #     'tran_type': 'BUY',
            #     'quantity': '1',
            #     'share_price': '350'}
            # controller.check_transaction('enter', tran)
            tran = {'tran_date': '2025-01-02',
                'symbol': 'TSLA',
                'tran_type': 'BUY',
                'quantity': '10',
                'share_price': '350',
                'tran_id':2}
            errors=controller.check_transaction('edit', tran)
            print(errors)

def init_app(app):
    app.cli.add_command(test_command)