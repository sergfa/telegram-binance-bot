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
    table.align['Buy'] = 'l'
    table.align['Sell'] = 'l'
    
    for symbol, buy, sell in data:
       table.add_row([symbol, boolAsYorNo(buy), boolAsYorNo(sell)])

    return f'<pre>{table}</pre>'

def split_list_to_chunks(data: List, chunkSize: int) -> List:
    chunks = [data[x:x + chunkSize] for x in range(0, len(data), chunkSize)]
    return chunks


def list_to_tables(data:List, chunkSize: int, converter) -> List:
    chunks = split_list_to_chunks(data, chunkSize)
    tables = [ converter(chunk) for chunk in chunks]
    return tables

def boolAsYorNo(value: bool) -> str:
    return 'Y' if value  else 'N'