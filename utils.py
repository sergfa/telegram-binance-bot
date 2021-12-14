from typing import List
import prettytable as pt


def symbols_to_table(symbols: List) -> str:
    table = pt.PrettyTable(['Symbol'])
    table.align['Symbol'] = 'l'
    for symbol in symbols:
       table.add_row([symbol])

    return f'<pre>{table}</pre>'

def symbols_alerts_to_table(data: List) -> str:
    table = pt.PrettyTable(['Symbol', 'Buy', 'Sell'])
    table.align['Symbol'] = 'l'
    table.align['Buy'] = 'r'
    table.align['Sell'] = 'r'
    
    for symbol, buy, sell in data:
       table.add_row([symbol, str(buy), str(sell)])

    return f'<pre>{table}</pre>'

