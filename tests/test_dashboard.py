"""Streamlit integration checks for every page, filter scope and scenario controls."""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class DashboardTests(unittest.TestCase):
    def test_pages_filters_and_scenario(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        for page in app.sidebar.radio[0].options:
            app.sidebar.radio[0].set_value(page).run()
            self.assertFalse(app.exception,msg=page)
        app.sidebar.radio[0].set_value('Sales & Transactions').run()
        full=app.metric[0].value
        app.sidebar.multiselect[0].set_value(['Garden']).run()
        self.assertFalse(app.exception);self.assertNotEqual(full,app.metric[0].value)
        branch_value=app.metric[0].value
        app.sidebar.multiselect[1].set_value(['Bakery']).run()
        self.assertFalse(app.exception);self.assertNotEqual(branch_value,app.metric[0].value)
        category_value=app.metric[0].value
        app.sidebar.multiselect[2].set_value(['Takeaway']).run()
        self.assertFalse(app.exception);self.assertNotEqual(category_value,app.metric[0].value)
        from datetime import date
        type_value=app.metric[0].value
        app.sidebar.date_input[0].set_value((date(2026,1,1),date(2026,1,31))).run()
        self.assertFalse(app.exception);self.assertNotEqual(type_value,app.metric[0].value)
        app.sidebar.radio[0].set_value('Opportunity Simulator').run()
        before=app.metric[2].value
        app.slider[0].set_value(0).run()
        self.assertNotEqual(before,app.metric[2].value)
        app.sidebar.multiselect[0].set_value([]).run()
        self.assertFalse(app.exception)

if __name__=='__main__':unittest.main()
