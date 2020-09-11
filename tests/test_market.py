from unittest import TestCase

from markets.stocks_model import create_stocks
from markets.dynamic_market import Stock


class MarketTest(TestCase):

    def test_sth(self):
        stocks = create_stocks(10)

        self.assertEquals(10, len(stocks))

        stock = stocks[0]

        stock.sentiments

        pass
