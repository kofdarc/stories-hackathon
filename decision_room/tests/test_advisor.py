from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading
import unittest
import pandas as pd
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError

from decision_room.advisor import read_upload,build_report
from decision_room.server import handler_factory

ROOT=Path(__file__).resolve().parents[2]


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content=(ROOT/'stories_transactions.csv').read_bytes()
        cls.data,cls.ignored=read_upload(cls.content)
        cls.report=build_report(cls.data)

    def test_six_layers_and_plain_reasoning(self):
        self.assertEqual({c['key'] for c in self.report['cards']},{'hours','closure','restock','waste','pricing','combos'})
        for card in self.report['cards']:
            self.assertTrue(card['action'] and card['reason'] and card['next_step'])
        self.assertEqual(self.report['summary']['orders'],33887)
        self.assertEqual(self.report['summary']['revenue'],'$305,925')

    def test_missing_costs_do_not_become_a_closure_recommendation(self):
        closure=next(c for c in self.report['cards'] if c['key']=='closure')
        self.assertEqual(closure['status'],'Need operating costs')
        self.assertIn('Keep branches open',closure['action'])
        waste=next(c for c in self.report['cards'] if c['key']=='waste')
        self.assertEqual(waste['status'],'Need waste records')

    def test_restock_uses_all_recent_calendar_days(self):
        card=next(c for c in self.report['cards'] if c['key']=='restock')
        row=card['table'][0]
        cutoff=self.data.date.max()-pd.Timedelta(days=55)
        actual=self.data[self.data.date.ge(cutoff)&self.data.branch.eq(row['branch'])&self.data['product'].eq(row['item'])].quantity.sum()/56
        self.assertEqual(row['daily_units'],f'{actual:.1f}')

    def test_pair_timing_and_replication_are_explicit(self):
        combos=next(c for c in self.report['cards'] if c['key']=='combos')
        self.assertTrue(combos['table'])
        for row in combos['table']:
            self.assertGreaterEqual(row['earlier'],5)
            self.assertGreaterEqual(row['later'],3)
            self.assertIn(':00',row['when'])
        self.assertIn('not proof',combos['reason'])

    def test_price_increases_and_cuts_have_break_even_gates(self):
        prices=next(c for c in self.report['cards'] if c['key']=='pricing')
        for row in prices['table']:
            self.assertIn('%',row['sales_loss_limit'])
            self.assertIn('%',row['price_cut_extra_sales'])

    def test_report_has_no_customer_or_order_identifiers(self):
        encoded=json.dumps(self.report,allow_nan=False)
        self.assertNotIn(str(self.data.transaction.iloc[0]),encoded)
        self.assertNotIn(str(self.data.customer.dropna().iloc[0]),encoded)

    def test_upload_rejects_bad_schema_and_finances(self):
        for content in (b'',b'foo,bar\n1,2\n',b'\xff\xfe'):
            with self.assertRaises(ValueError):read_upload(content)
        bad=self.content.replace(b',0.0,',b',2.0,',1)
        with self.assertRaises(ValueError):read_upload(bad)


class UploadHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler_factory(None))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def test_upload_works_without_bundled_csv_or_gemini(self):
        browser=build_opener(HTTPCookieProcessor(CookieJar()))
        with browser.open(self.base+'/api/meta') as r:
            meta=json.load(r)
            self.assertFalse(meta['existing_available'])
            self.assertFalse(meta['chat_configured'])
        request=Request(self.base+'/api/upload',data=(ROOT/'stories_transactions.csv').read_bytes(),headers={'Content-Type':'text/csv'})
        with browser.open(request) as r:
            report=json.load(r)
            self.assertEqual(len(report['cards']),6)
        with browser.open(self.base+'/sales-template.csv') as r:self.assertIn(b'Transaction ID',r.read())


if __name__=='__main__':unittest.main()
