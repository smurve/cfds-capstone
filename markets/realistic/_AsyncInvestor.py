import logging
from typing import List

import ray

from . import AbstractMarketMaker, Clock
from .AbstractInvestor import AbstractInvestor
from .remotes import AsyncMarketMaker


@ray.remote
class RayInvestor:

    def __init__(self, delegate: AbstractInvestor):
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.FileHandler("/etc/logs/actor.log", mode="a+"))
        self.logger.setLevel('INFO')
        self.delegate: AbstractInvestor = delegate
        self.logger.debug(f"This is {delegate.get_name()}: starting up.")

    def tick(self, clock: Clock):
        self.logger.debug(f"This is {self.delegate.get_name()}: recieved clock tick signal.")
        self.delegate.tick(clock)

    def identify(self) -> str:
        ip = ray.services.get_node_ip_address()  # noqa (services not exposed)
        return f'{self.delegate.identify()}@{ip}'

    def get_stock_symbols(self):
        return self.delegate.get_stock_symbols()

    def register_with(self, market_maker: AbstractMarketMaker, symbol: str):
        return self.delegate.register_with(AsyncMarketMaker(market_maker), symbol)

    def report_tx(self, order_type, symbol: str, volume: float, price: float, amount: float):
        self.delegate.report_tx(order_type, symbol, volume, price, amount)

    def get_portfolio(self):
        return self.delegate.get_portfolio()

    def get_name(self):
        return self.delegate.get_name()

    def osid(self):
        return self.delegate.osid()


class AsyncInvestor(AbstractInvestor):

    def __init__(self, investor):
        if isinstance(investor, AbstractInvestor):
            self.actor_ref = RayInvestor.remote(investor)
        else:
            self.actor_ref = investor
        self.logger = logging.getLogger(__name__)

    def tick(self, clock: Clock):
        self.logger.debug(f'{self.get_name()} here. Ticking remote delegate.')
        self.actor_ref.tick.remote(clock)

    def identify(self) -> str:
        return ray.get(self.actor_ref.identify.remote())

    def get_stock_symbols(self) -> List[str]:
        return ray.get(self.actor_ref.get_stock_symbols.remote())

    def register_with(self, market_maker: AsyncMarketMaker, symbol: str):
        return ray.get(self.actor_ref.register_with.remote(market_maker.actor_ref, symbol))

    def report_tx(self, order_type, symbol: str, volume: float, price: float, amount: float):
        self.logger.debug(f'{self.get_name()} here. Reporting transaction to remote.')
        self.actor_ref.report_tx.remote(order_type, symbol, volume, price, amount)

    def get_portfolio(self):
        return ray.get(self.actor_ref.get_portfolio.remote())

    def get_name(self):
        return ray.get(self.actor_ref.get_name.remote())

    def osid(self):
        return ray.get(self.actor_ref.osid.remote())
