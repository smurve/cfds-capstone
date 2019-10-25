import numpy as np
from markets.dynamic_market import Market, Stock, Segment, GeoMarket
from markets.environment import TradingEnvironment


def rnd_sentiments(s_max=1, s_min=-10, n_quarters=16):
    offset = np.random.randint(64)  # reporting day within the quarter
    s_c = 0
    q = 64  # a quarter
    s = {0: (0, 0)}
    for i in range(n_quarters):
        dst = np.random.normal(.006, .005) / q
        day = i * q + int(np.random.normal(5)) + offset
        s[day] = (s_c, dst)
        s_c = min(s_max, s_c + np.random.normal(0, .1))
        s_c = max(s_min, s_c)
    s[1024] = (0, 0)
    return s


# US market: bulls and bears
us = GeoMarket('US',                   # A name
               {0: (.1, 0.001),         # Market sentiment over time, starting slightly bullish
                150: (-.1, -0.001),
                300: (-.13, 0),         # Not too bad yet                
                380: (-.1, -0.005),     # A period of hope
                450: (.15, 0.003),
                500: (.25, 0),          # And more hope
                620: (.1, 0.004),
                700: (.1, 0.001),
                830: (.05, 0.007)
                })


# Segment sentiment: IT is calming down - the dawn of the new AI winter?
it = Segment('Information Technology', {0: (.0, .001)})


def create_stocks(n_stocks):
    # creates a set of stock tickers    
    tickers = list(set(
        ["".join([chr(int(np.random.random() * 26 + 65)) for _ in range(4)])
         for _ in range(2 * n_stocks)]))[:n_stocks]
    
    stocks = {}
    for ticker in tickers:
        e_cagr = np.random.normal(6e-2, 4e-2)   # expected compound annual growth rate
        max_effect = 3.0  # Maximum overrating due to sentiment
        psi0 = 50 + 20 * np.random.random()  # initial price
        sentiments = rnd_sentiments()       # quarterly impacted stock sentiments
        beta_geo = np.random.normal(.2, .1)       # exposure (beta) to the US market
        beta_it = np.random.normal(.0, .5)       # exposure (beta) to the IT sector
        stock = Stock(name=ticker, e_cagr=e_cagr, max_effect=max_effect, psi0=psi0,
                      segments={it: beta_it}, markets={us: beta_geo},
                      sentiments=sentiments, noise=.4)
        stocks[ticker] = stock
        
    return stocks


def create_chart_data(stocks, config):

    period = config['num_days']
    
    market = Market(stocks=list(stocks.values()), bid_ask=0.1)

    holdings = {ticker: 10000 for ticker in stocks}
    holdings['cash'] = 1e7

    environment = TradingEnvironment(config, holdings, market, tx_cost=2.5e-3)

    for _ in range(period):
        market.open()
        environment.let_others_trade()
        market.close()

    package = {ticker: {
        "price": np.array(market.history[ticker][:period])[:, 1],
        "epv": np.array([round(stocks[ticker].psi(t), 2) for t in range(period)])}
        for ticker in stocks}

    return package


class MarketFromData:
    """
    creates a market wrapper for an array or list of shape [N_STOCKS, N_PRICES]
    """
    def __init__(self, data, duration, nh, fee):
        """
        data: an array or list of shape [n_stocks, n_prices]
        nh: max. number of prices in history
        duration: the length of the period that can be served
        requires len(data) == duration + nh
        """
        self.duration = duration
        self.nh = nh
        self.data = np.array(data)
        self.n_securities = np.shape(self.data)[0]
        self.fee = fee
        length = np.shape(self.data)[1]
        if length != duration + nh:
            raise ValueError("record length not sum of duration and history.")
        # Need one more for the log returns
        np.append(self.data, self.data[:, -1:], axis=-1)
                    
    def log_return_history(self, nh, t):
        if t < 0 or t >= self.duration:
            raise ValueError("t must be between %s and %s" % (0, self.duration - 1))
        if nh > self.nh or nh <= 0:
            raise ValueError("t must be between %s and %s" % (1, self.nh))
        t += self.nh + 1
        
        h = self.data[:, t - nh - 1: t]
        return np.log(h[:, 1:] / h[:, :-1]).T
        
    def prices(self, t):
        return self.data[:, t]
