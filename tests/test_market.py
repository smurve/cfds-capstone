from unittest import TestCase

from markets.stocks_model import create_stocks, rnd_sentiments
from markets.dynamic_market import Stock, Segment, GeoMarket, MomentumInvestor, Market


class MarketTest(TestCase):

    def explore_sth(self):
        sentiments = rnd_sentiments()       # quarterly impacted stock sentiments
        beta_geo = .15       # exposure (beta) to the US market
        beta_it = .25       # exposure (beta) to the IT sector
        e_cagr = 1e-4
        max_effect = 3.0
        psi0 = 70
        it = Segment('Information Technology', {0: (.0, .001)})
        us = GeoMarket('US',  # A name
                       {0: (.1, 0.001),  # Market sentiment over time, starting slightly bullish
                        150: (-.1, -0.001),
                        300: (-.13, 0),  # Not too bad yet
                        380: (-.1, -0.005),  # A period of hope
                        450: (.15, 0.003),
                        500: (.25, 0),  # And more hope
                        620: (.1, 0.004),
                        700: (.1, 0.001),
                        830: (.05, 0.007)
                        })

        ticker = 'AAPL'
        stock = Stock(name=ticker, e_cagr=e_cagr, max_effect=max_effect, psi0=psi0,
                      segments={it: beta_it}, markets={us: beta_geo},
                      sentiments=sentiments, noise=.4)

        stocks = {ticker: stock}

        portfolio = {stock.name: 10000}

        michael = MomentumInvestor(
            name="Michael Burry",
            wealth=1000000,
            portfolio=portfolio)

        market = Market(stocks=list(stocks.values()), bid_ask=0.2)
        market.open()

        print("Michael's position in %s before acting: %s" % (ticker, michael.portfolio[ticker]))
        print("Current prices (bid, ask): %s, %s" % market.price_for(ticker))

        michael.act_on(market, ticker)
        print()

        print("Michael's position in %s after  acting: %s" % (ticker, michael.portfolio[ticker]))
        print("Current prices (bid, ask): %s, %s" % market.price_for(ticker))

        self.assertTrue(False)
