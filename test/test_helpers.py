from markets.dynamic_market import Segment, GeoMarket, Stock
from markets.stocks_model import rnd_sentiments


def given_stock(symbol: str, initial_value):
    sentiments = rnd_sentiments()  # quarterly impacted stock sentiments
    beta_geo = .15  # exposure (beta) to the US market
    beta_it = .25  # exposure (beta) to the IT sector
    e_cagr = 1e-4
    max_effect = 3.0
    psi0 = initial_value
    it = Segment('Information Technology', {0: (.0, -.002)})
    us = GeoMarket('US',  # A name
                   {0: (.1, -0.0005),  # Market sentiment over time, starting slightly bullish
                    150: (-.1, -0.001),
                    300: (-.13, 0),  # Not too bad yet
                    380: (-.1, -0.005),  # A period of hope
                    450: (.15, 0.003),
                    500: (.25, 0),  # And more hope
                    620: (.1, 0.004),
                    700: (.1, 0.001),
                    830: (.05, 0.007)
                    })

    return Stock(name=symbol, e_cagr=e_cagr, max_effect=max_effect, psi0=psi0,
                 segments={it: beta_it}, markets={us: beta_geo},
                 sentiments=sentiments, noise=.4)
