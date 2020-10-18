import datetime as dt

from unittest import TestCase

from markets.realistic import Clock
from markets.realistic.Statistician import Statistician
from markets.realistic.abstract import AbstractStatistician

SWKS = 'SWKS'
SOME_DAY = dt.date.today()


class StatisticianTest(TestCase):

    def setUp(self) -> None:
        self.stat: AbstractStatistician = Statistician()

    def test_report_single_transaction(self):

        price = 153.15
        volume = 100

        self.stat.report_transaction(SWKS, volume, price, Clock())

        df = self.stat.get_chart_data(SWKS, dt.date.today())

        self.assertEqual(df['Open'][0], price)
        self.assertEqual(df['Close'][0], price)
        self.assertEqual(df['High'][0], price)
        self.assertEqual(df['Low'][0], price)
        self.assertEqual(df['Volume'][0], volume)

    def test_late_arrival_of_open__and_hlv(self):

        sec_10 = Clock().tick(10)
        self.stat.report_transaction(SWKS, 100, 200.0, sec_10)

        # Late arrivals should override entries with later time stamps
        sec_0 = Clock().tick(0)
        self.stat.report_transaction(SWKS, 100, 100.0, sec_0)
        df = self.stat.get_chart_data(SWKS, SOME_DAY)
        self.assertEqual(df['Open'][0], 100.0)

        #  but not the one with same timestamp
        self.stat.report_transaction(SWKS, 100, 40.0, sec_0)
        df = self.stat.get_chart_data(SWKS, SOME_DAY)
        self.assertEqual(df['Open'][0], 100.0)

        # Asserting high, low and volume en passant
        self.assertEqual(df['High'][0], 200.0)
        self.assertEqual(df['Low'][0], 40.0)
        self.assertEqual(df['Volume'][0], 300)

    def test_early_arrival_of_close__and_hlv(self):

        sec_59 = Clock().tick(59)
        self.stat.report_transaction(SWKS, 110, 40.0, sec_59)

        sec_30 = Clock().tick(30)
        # arrived later but 'as of' earlier -> don't override Close
        self.stat.report_transaction(SWKS, 120, 50.0, sec_30)
        df = self.stat.get_chart_data(SWKS, SOME_DAY)
        self.assertEqual(df['Close'][0], 40.0)

        # arrived later with same time stamp -> override Close
        self.stat.report_transaction(SWKS, 130, 60.0, sec_59)
        df = self.stat.get_chart_data(SWKS, SOME_DAY)
        self.assertEqual(df['Close'][0], 60.0)

        # Asserting high, low and volume en passant
        self.assertEqual(df['High'][0], 60.0)
        self.assertEqual(df['Low'][0], 40.0)
        self.assertEqual(df['Volume'][0], 360)
