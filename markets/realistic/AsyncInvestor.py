from typing import List

import ray

from . import AbstractMarketMaker, Clock
from .AbstractInvestor import AbstractInvestor


@ray.remote
class RayInvestor:

    def __init__(self, delegate: AbstractInvestor):
        self.delegate: AbstractInvestor = delegate

    def tick(self, clock: Clock):
        self.delegate.tick(clock)

    def identify(self) -> str:
        ip = ray.services.get_node_ip_address()  # noqa (services not exposed)
        return f'{self.delegate.identify()}@{ip}'

    def get_stock_symbols(self):
        return self.delegate.get_stock_symbols()

    def register_with(self, market_maker: AbstractMarketMaker, symbol: str):
        self.delegate.register_with(market_maker, symbol)


class AsyncInvestor(AbstractInvestor):

    def __init__(self, delegate: AbstractInvestor):
        self.delegate = RayInvestor.remote(delegate)

    def tick(self, clock: Clock):
        self.delegate.tick.remote(clock)

    def identify(self) -> str:
        return ray.get(self.delegate.identify.remote())

    def get_stock_symbols(self) -> List[str]:
        return ray.get(self.delegate.get_stock_symbols())

    def register_with(self, market_maker: AbstractMarketMaker, symbol: str):
        self.delegate.register_with(market_maker, symbol)
