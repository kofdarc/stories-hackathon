"""Portable checks: synthetic test fixtures only; no private dataset or API key."""
import csv
from datetime import date,timedelta
from io import StringIO
import json
import unittest
from unittest.mock import patch

from src.analytics import RENAME
from decision_room.advisor import read_upload,build_report
from decision_room.server import answer_followup,compact_report,ProviderError


def fixture():
    buf=StringIO();writer=csv.writer(buf);writer.writerow(RENAME)
    for day in range(42):
        for branch in ('North','South'):
            for hour in (7,15,20):
                transaction=f'{day}-{branch}-{hour}'
                for product,category,price,cost in [('Coffee','Coffee',5,2),('Croissant','Bakery',4,1)]:
                    writer.writerow([transaction,(date(2026,1,1)+timedelta(days=day)).isoformat(),f'{hour:02d}:00:00',branch,'','Dine-in',product,category,1,price,0,cost,price,price-cost])
    return buf.getvalue().encode()


class SubmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data,_=read_upload(fixture());cls.report=build_report(cls.data)

    def test_six_recommendations_and_python_charts(self):
        self.assertEqual({c['key'] for c in self.report['cards']},{'hours','closure','restock','waste','pricing','combos'})
        for card in self.report['cards']:
            self.assertTrue(card['action'] and card['reason'] and card['next_step'])
            self.assertTrue(card['chart']['src'].startswith('data:image/png;base64,iVBOR'))
            self.assertTrue(card['chart']['caption'])

    def test_different_csv_changes_recommendations_and_charts(self):
        other=build_report(self.data[self.data.branch.eq('North')].copy())
        self.assertEqual(other['summary']['branches'],1)
        self.assertNotEqual(other['summary']['orders'],self.report['summary']['orders'])
        self.assertNotEqual(other['cards'][1]['chart']['src'],self.report['cards'][1]['chart']['src'])
        self.assertNotIn('South',json.dumps(other))

    def test_missing_inputs_are_not_invented(self):
        cards={c['key']:c for c in self.report['cards']}
        self.assertEqual(cards['closure']['status'],'Need operating costs')
        self.assertEqual(cards['waste']['status'],'Need waste records')
        self.assertTrue(cards['pricing']['table'][0]['price_cut_extra_sales'].endswith('%'))

    def test_invalid_csv(self):
        for data in (b'',b'foo,bar\n1,2\n',b'\xff\xfe'):
            with self.assertRaises(ValueError):read_upload(data)

    def test_model_context_omits_images_and_raw_identifiers(self):
        text=json.dumps(compact_report(self.report))
        self.assertNotIn('data:image',text)
        self.assertNotIn('0-North-7',text)

    def test_gemini_success_does_not_call_backup(self):
        response={'candidates':[{'content':{'parts':[{'text':'Check operating costs first.'}]}}]}
        with patch('decision_room.server.google_request',return_value=response),patch('decision_room.server.deepseek_request') as backup:
            answer=answer_followup(self.report,'What first?','primary','gemini-3.8-flash','backup')
        self.assertEqual(answer['provider'],'Gemini');backup.assert_not_called()

    def test_gemini_failure_uses_deepseek(self):
        with patch('decision_room.server.google_request',side_effect=ProviderError('quota')),patch('decision_room.server.deepseek_request',return_value='Check the roster first.') as backup:
            answer=answer_followup(self.report,'What first?','primary','gemini-3.8-flash','backup')
        self.assertEqual(answer['provider'],'DeepSeek');self.assertTrue(answer['fallback_used'])
        self.assertNotIn('data:image',json.dumps(backup.call_args.args[1]))

    def test_no_backup_key_does_not_fake_fallback(self):
        with patch('decision_room.server.google_request',side_effect=ProviderError('quota')):
            with self.assertRaises(ProviderError):answer_followup(self.report,'What first?','primary','gemini-3.8-flash')


if __name__=='__main__':unittest.main()
