from typing import Dict, List
import numpy as np

from .Stock import Segment, GeoMarket, Stock
from .abstract import AbstractMarket


class USITMarket(AbstractMarket):

    def __init__(self, stocks: Dict[str, float], noise):
        self.segments = {'IT': Segment('Information Technology', {0: (.0, -.002)})}
        self.geos = {'US': GeoMarket('US',  # A name
                                     {0: (.1, -0.0005),  # Market sentiment over time, starting slightly bullish
                                      150: (-.1, -0.001),
                                      300: (-.13, 0),  # Not too bad yet
                                      380: (-.1, -0.005),  # A period of hope
                                      450: (.15, 0.003),
                                      500: (.25, 0),  # And more hope
                                      620: (.1, 0.004),
                                      700: (.1, 0.001),
                                      830: (.05, 0.007)
                                      })}

        self.beta_us = .15  # exposure (beta) to the US market
        self.beta_it = .25  # exposure (beta) to the IT sector
        self.stocks = {symbol: self.create_stock(symbol,
                                                 initial_value=stocks[symbol],
                                                 segment_betas={self.segments['IT']: self.beta_it},
                                                 geo_betas={self.geos['US']: self.beta_us},
                                                 noise=noise
                                                 ) for symbol in stocks}

    def get_stocks(self) -> List[Stock]:
        return list(self.stocks.values())

    def get_intrinsic_value(self, symbol: str, day: int) -> float:
        return self.stocks[symbol].psi(day)

    @staticmethod
    def create_stock(symbol: str, initial_value: float,
                     segment_betas: Dict[Segment, float],
                     geo_betas: Dict[GeoMarket, float],
                     noise: float) -> Stock:
        sentiments = rnd_sentiments()  # quarterly impacted stock sentiments
        e_cagr = 1e-4
        max_effect = 3.0

        return Stock(name=symbol, e_cagr=e_cagr, max_effect=max_effect, psi0=initial_value,
                     segments=segment_betas, markets=geo_betas,
                     sentiments=sentiments, noise=noise)


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
