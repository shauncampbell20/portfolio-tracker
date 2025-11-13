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
        db = get_db()
        g.user = db.execute(
            'SELECT * FROM user WHERE id = ?', (1,)
        ).fetchone()
        controller = Controller(cache)
        test1 = True
        test2 = False
        db.execute('''DELETE FROM transactions WHERE user_id = ?''', (g.user['id'],))
        db.commit()
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
            print('# valid sell')
            errors = controller.check_transaction('enter',
                {'tran_date': '2025-11-02',
                'symbol': 'SPY',
                'tran_type': 'SELL',
                'quantity': '1',
                'share_price': '500'}
            )
            print(errors)
            print('# valid fee')
            errors = controller.check_transaction('enter',
                {'tran_date': '2025-11-02',
                'symbol': 'SPY',
                'tran_type': 'FEE',
                'quantity': '.01',
                'share_price': '500'}
            )
            print(errors)
            print('# edit transaction, same symbol')
            tran = db.execute('''SELECT * FROM transactions WHERE user_id = ?''',(g.user['id'],)).fetchone()
            tran = dict(tran)
            tran['quantity'] = '2'
            errors = controller.check_transaction('edit',tran)
            print(errors)
            print('# edit transaction, new symbol')
            tran['symbol'] = 'AAPL'
            errors = controller.check_transaction('edit',tran)
            print(errors)
            print('# edit transaction, change to sell')
            tran['tran_type'] = 'SELL'
            errors = controller.check_transaction('edit',tran)
            print(errors)
            print('# delete non-existent transaction')
            db.execute('''DELETE FROM transactions WHERE id = ?''',(999,))
            db.commit()
            errors = controller.check_transaction('delete',None)
            print(errors)
            print('# delete existing transaction')
            db.execute('''DELETE FROM transactions WHERE id = ?''',(tran['id'],))
            db.commit()
            errors = controller.check_transaction('delete',None)
            print(errors)
        elif test2:
            # tran = {'tran_date': '2025-01-02',
            #     'symbol': 'TSLA',
            #     'tran_type': 'BUY',
            #     'quantity': '1',
            #     'share_price': '350'}
            # controller.check_transaction('enter', tran)
            errors = controller.check_transaction('enter',
                {'tran_date': '2021-08-01',
                'symbol': 'TSLA',
                'tran_type': 'BUY',
                'quantity': '3',
                'share_price': '875'}
            )
            print('# valid sell')
            errors = controller.check_transaction('enter',
                {'tran_date': '2025-11-02',
                'symbol': 'TSLA',
                'tran_type': 'SELL',
                'quantity': '3',
                'share_price': '400'}
            )

def init_app(app):
    app.cli.add_command(test_command)