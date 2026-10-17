from http.server import ThreadingHTTPServer
import json
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from decision_room.engine import DecisionEngine, attachment, closure, price_scenario
from decision_room.server import chat, handler_factory, ProviderError


class ArithmeticTests(unittest.TestCase):
    def test_closing_recapture_and_avoidable_costs(self):
        r=closure(30,1,24,.3)
        self.assertAlmostEqual(r['net'],3)
        self.assertAlmostEqual(r['break_even_hourly_cost'],21)
        self.assertAlmostEqual(closure(30,1,0,0)['net'],-30)
        self.assertEqual(closure(30,1,40,0)['break_even_recapture'],0)

    def test_unnecessary_combo_rebate_erases_gain(self):
        # 50 add-ons earn $2 each; 100 existing pair buyers get $1 off.
        r=attachment(1000,100,.05,3,7,3,.1,0)
        self.assertAlmostEqual(r['net'],0)
        self.assertAlmostEqual(r['break_even_adoption'],.05)

    def test_full_price_prompt_and_negative_unit_profit(self):
        self.assertEqual(attachment(100,20,.1,5,5,2,0,0)['net'],20)
        r=attachment(100,20,.1,5,5,2,.5,0)
        self.assertLess(r['net'],0)
        self.assertIsNone(r['break_even_adoption'])

    def test_price_break_even(self):
        r=price_scenario(500,200,0,.1,0,0)
        self.assertAlmostEqual(r['net'],50)
        self.assertAlmostEqual(r['break_even_item_loss'],1-300/350)

    def test_whole_basket_exit_includes_other_items_once(self):
        r=price_scenario(500,200,100,.1,0,1)
        self.assertEqual(r['net'],-400)
        self.assertEqual(r['other_basket_gp_lost'],100)

    def test_unchanged_policy_cannot_cause_treatment_exit(self):
        self.assertEqual(price_scenario(500,200,100,0,-1,.5)['net'],0)


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.engine=DecisionEngine()

    def test_real_data_and_zero_cost_hours(self):
        r=self.engine.run({'hourly_saving':0,'recapture':0})
        self.assertEqual(r['best']['label'],'07:00–24:00')
        self.assertEqual(r['best']['net'],0)
        self.assertAlmostEqual(r['audit']['recorded_gp'],r['audit']['recomputed_gp'],places=5)
        self.assertEqual(r['period']['active_days'],28)

    def test_weekday_calendar_weights(self):
        r=self.engine.run({'weekdays':[0,1,2,3,4],'days':28,'start_hour':8,'hourly_saving':10})
        self.assertEqual(r['period']['active_days'],20)
        self.assertEqual(r['selected']['removed_hours'],20)
        self.assertEqual(r['selected']['savings'],200)

    def test_combos_include_no_offer_and_no_fake_probability(self):
        r=self.engine.run({'module':'combos','adoption':0,'combo_discount':.1})
        self.assertEqual(r['best']['label'],'No offer')
        self.assertTrue(all(row['net']<=0 for row in r['rows']))
        self.assertNotIn('probability',r)

    def test_price_scenario_reconciles_with_formula(self):
        r=self.engine.run({'module':'pricing','product':'Espresso','price_change':.05,'elasticity':-1})
        a=r['selected']
        expected=(a['affected_revenue']*1.05-a['affected_cost'])/1.05-(a['affected_revenue']-a['affected_cost'])
        self.assertAlmostEqual(a['net'],expected)
        self.assertIn('+2.5% price',[row['label'] for row in r['rows']])

    def test_input_validation(self):
        for state in ({'recapture':float('nan')},{'days':True},{'days':7.5},{'weekdays':[]},
                      {'weekdays':[True]},{'branch':'unknown'},{'start_hour':23,'end_hour':8},
                      {'start_date':'2026-01-01'},{'product':'unknown'},{'new_key':1}):
            with self.subTest(state=state),self.assertRaises(ValueError):self.engine.run(state)

    def test_json_finite_and_backtest(self):
        for module in ('hours','combos','pricing'):
            json.dumps(self.engine.run({'module':module}),allow_nan=False)
        self.assertGreater(self.engine.backtest['last_week_wape'],0)
        self.assertGreater(self.engine.backtest['weekday_mean_wape'],0)

    def test_gemini_tool_loop_preserves_model_parts_and_state(self):
        content={'role':'model','parts':[{'functionCall':{'name':'compare_decisions','args':{'module':'hours','recapture':.3}},'thoughtSignature':'opaque-signature'}]}
        replies=[{'candidates':[{'content':content}]},{'candidates':[{'content':{'parts':[{'text':'Conditional result from the calculator.'}]}}]}]
        state=dict(self.engine.metadata()['defaults'],hourly_saving=12)
        with patch('decision_room.server.google_request',side_effect=replies) as request:
            r=chat(self.engine,state,[{'role':'user','content':'Assume 30% return later'}],'test-key','gemini-3.8-flash')
        self.assertEqual(r['state']['hourly_saving'],12)
        self.assertEqual(r['state']['recapture'],.3)
        self.assertEqual(request.call_args_list[1].args[2]['contents'][-2],content)
        self.assertEqual(request.call_args_list[0].args[2]['generationConfig']['thinkingConfig'],{'thinkingLevel':'low'})
        self.assertNotIn('test-key',json.dumps(r))

    def test_no_tool_call_does_not_show_unverified_answer(self):
        with patch('decision_room.server.google_request',return_value={'candidates':[{'content':{'parts':[{'text':'Invented $100 profit'}]}}]}):
            with self.assertRaises(ProviderError):
                chat(self.engine,{},[{'role':'user','content':'recommend something'}],'key','model')


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler_factory(DecisionEngine()))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls): cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def test_html_metadata_and_simulation(self):
        with urlopen(self.base) as response:self.assertIn(b'Stories',response.read())
        with urlopen(self.base+'/api/meta') as response:
            meta=json.load(response)
            self.assertFalse(meta['chat_configured'])
            self.assertNotIn('key',meta)
        request=Request(self.base+'/api/simulate',data=json.dumps({'state':{'module':'pricing'}}).encode(),headers={'Content-Type':'application/json'})
        with urlopen(request) as response:self.assertIn('best',json.load(response))

    def test_no_raw_files_cross_origin_or_chat_without_key(self):
        for path in ('/../stories_transactions.csv','/stories_transactions.csv','/server.py'):
            with self.assertRaises(HTTPError) as error:urlopen(self.base+path)
            self.assertEqual(error.exception.code,404)
            error.exception.close()
        request=Request(self.base+'/api/simulate',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://other.example'})
        with self.assertRaises(HTTPError) as error:urlopen(request)
        self.assertEqual(error.exception.code,403)
        error.exception.close()
        request=Request(self.base+'/api/chat',data=b'{}',headers={'Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as error:urlopen(request)
        self.assertEqual(error.exception.code,409)
        error.exception.close()


if __name__=='__main__': unittest.main()
