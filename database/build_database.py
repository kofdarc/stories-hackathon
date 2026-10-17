#!/usr/bin/env python3
"""Build a verified SQLite database and portable SQL dump using only Python stdlib."""
import argparse
import csv
import hashlib
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import date, time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parent / 'stories_transactions.csv'
HEADERS = ['Transaction ID', 'Date', 'Time', 'Branch', 'Customer ID', 'Order Type',
           'Product', 'Category', 'Quantity', 'Unit Price (USD)', 'Discount Rate',
           'Unit Cost (USD)', 'Line Revenue (USD)', 'Line Gross Profit (USD)']


def scaled(value, factor):
    result = Decimal(value) * factor
    if not result.is_finite() or result != result.to_integral_value():
        raise ValueError(f'Value cannot be represented exactly: {value!r}')
    return int(result)


def build(source, output):
    records, metadata = [], {}
    source_bytes = source.read_bytes()
    with source.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADERS:
            raise ValueError('CSV columns do not match the expected schema')
        for line_id, row in enumerate(reader, start=1):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'Malformed CSV record {line_id}')
            for field in HEADERS:
                if field != 'Customer ID' and not row[field]:
                    raise ValueError(f'Missing {field} at record {line_id}')
            date.fromisoformat(row['Date'])
            time.fromisoformat(row['Time'])
            customer = row['Customer ID'] or None
            order_metadata = (row['Date'], row['Time'], row['Branch'], customer, row['Order Type'])
            transaction_id = row['Transaction ID']
            if transaction_id in metadata and metadata[transaction_id] != order_metadata:
                raise ValueError(f'Conflicting order metadata for {transaction_id}')
            metadata[transaction_id] = order_metadata
            quantity = scaled(row['Quantity'], 1)
            price = scaled(row['Unit Price (USD)'], 100)
            discount = scaled(row['Discount Rate'], 10000)
            cost = scaled(row['Unit Cost (USD)'], 100)
            revenue = scaled(row['Line Revenue (USD)'], 100)
            profit = scaled(row['Line Gross Profit (USD)'], 100)
            expected = (Decimal(quantity * price) * (1 - Decimal(discount) / 10000)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            # Permit one cent of source rounding, but preserve source amounts verbatim.
            if abs(revenue - expected) > 1 or abs(profit - (revenue - quantity * cost)) > 1:
                raise ValueError(f'Financial arithmetic mismatch at record {line_id}')
            records.append((line_id, transaction_id, *order_metadata[:3], customer,
                            row['Order Type'], row['Product'], row['Category'],
                            quantity, price, discount, cost, revenue, profit))
    if not records:
        raise ValueError('The source contains no transactions')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.stories-', suffix='.sqlite', dir=output.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        with closing(sqlite3.connect(temporary)) as connection:
            connection.executescript(HERE.joinpath('schema.sql').read_text())
            connection.executemany('INSERT INTO transaction_lines VALUES (' + ','.join(['?'] * 15) + ')', records)
            connection.execute('INSERT INTO source_metadata VALUES (?, ?, ?, ?, ?, ?)',
                               (source.name, hashlib.sha256(source_bytes).hexdigest(), len(records),
                                len(metadata), min(x[2] for x in records), max(x[2] for x in records)))
            connection.commit()
            assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            expected_totals = (len(records), sum(x[13] for x in records), sum(x[14] for x in records))
            actual_totals = connection.execute('SELECT COUNT(*), SUM(line_revenue_cents), SUM(line_gross_profit_cents) FROM transaction_lines').fetchone()
            assert actual_totals == expected_totals, (actual_totals, expected_totals)
            assert connection.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == len(metadata)
            assert connection.execute('SELECT SUM(order_revenue_cents), SUM(order_gross_profit_cents) FROM orders').fetchone() == expected_totals[1:]
            # Run all sample queries, so documentation remains executable.
            connection.executescript(HERE.joinpath('queries.sql').read_text())
            connection.execute('VACUUM')
            dump = '\n'.join(connection.iterdump()) + '\n'
        # Check that the SQL dump independently reconstructs the same data.
        with closing(sqlite3.connect(':memory:')) as restored:
            restored.executescript(dump)
            assert restored.execute('SELECT COUNT(*), SUM(line_revenue_cents), SUM(line_gross_profit_cents) FROM transaction_lines').fetchone() == expected_totals
            assert restored.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == len(metadata)
            assert restored.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        output.with_suffix('.sql').write_text(dump, encoding='utf-8')
        os.replace(temporary, output)
        print(f'Built {output.name} and {output.with_suffix(".sql").name}: {len(records):,} item lines, {len(metadata):,} orders; revenue ${expected_totals[1] / 100:,.2f}; gross profit ${expected_totals[2] / 100:,.2f}')
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=HERE / 'stories.sqlite')
    args = parser.parse_args()
    build(args.source, args.output)
