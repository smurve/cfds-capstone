from typing import List, Callable, Dict

from .abstract import AbstractMarket
from .Stock import Stock

INTRINSIC_VALUE = 'INTRINSIC_VALUE'


def unbiased_float(any_float: float):
    return any_float


class BiasedMarketView(AbstractMarket):

    def __init__(self, market: AbstractMarket, biases: Dict[str, Callable] = None):
        self.market = market
        self.biases = {
            INTRINSIC_VALUE: biases.get(INTRINSIC_VALUE) if biases else unbiased_float
        }

    def get_stocks(self) -> List[Stock]:
        return self.market.get_stocks()

    def get_intrinsic_value(self, symbol: str, day: int) -> float:
        return self.biases[INTRINSIC_VALUE](self.market.get_intrinsic_value(symbol, day))
