from __future__ import annotations
import logging
import ray
from typing import List, Dict

from .Clock import Clock
from .abstract import AbstractInvestor, AbstractMarketMaker
from .Order import Order


@ray.remote
class RayInvestor:

    def __init__(self, delegate: AbstractInvestor):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.delegate: AbstractInvestor = delegate
        self.logger.debug(f"This is {delegate.get_name()}: starting up.")

    def tick(self, clock: Clock):
        self.logger.debug(f"This is {self.delegate.get_name()}: recieved clock tick signal.")
        self.delegate.tick(clock)

    def get_stock_symbols(self):
        return self.delegate.get_stock_symbols()

    def register_with(self, market_maker: AbstractMarketMaker, symbol: str):
        self.logger.debug(f"{self.delegate.get_qname()}: recieved clock tick signal.")
        return self.delegate.register_with(AsyncMarketMaker(market_maker), symbol)

    def report_tx(self, order_type, symbol: str, volume: float, price: float, amount: float):
        self.delegate.report_tx(order_type, symbol, volume, price, amount)

    def get_portfolio(self):
        return self.delegate.get_portfolio()

    def get_name(self) -> str:
        return self.delegate.get_name()

    def osid(self) -> str:
        return self.delegate.osid()

    def get_qname(self) -> str:
        return self.delegate.get_qname()


class AsyncInvestor(AbstractInvestor):

    def __init__(self, investor):
        if isinstance(investor, AbstractInvestor):
            self.actor_ref = RayInvestor.remote(investor)
        else:
            self.actor_ref = investor
        self.logger = logging.getLogger(self.__class__.__name__)

    def tick(self, clock: Clock):
        self.logger.debug(f'{self.get_name()} here. Ticking remote delegate.')
        self.actor_ref.tick.remote(clock)

    def get_stock_symbols(self) -> List[str]:
        return ray.get(self.actor_ref.get_stock_symbols.remote())

    def register_with(self, market_maker: AsyncMarketMaker, symbol: str):
        return ray.get(self.actor_ref.register_with.remote(market_maker.actor_ref, symbol))

    def report_tx(self, order_type, symbol: str, volume: float, price: float, amount: float):
        self.logger.debug(f'{self.get_qname()} here. Reporting transaction to remote.')
        self.actor_ref.report_tx.remote(order_type, symbol, volume, price, amount)

    def get_portfolio(self):
        return ray.get(self.actor_ref.get_portfolio.remote())

    def get_name(self):
        return ray.get(self.actor_ref.get_name.remote())

    def osid(self):
        return ray.get(self.actor_ref.osid.remote())

    def get_qname(self) -> str:
        return ray.get(self.actor_ref.get_qname.remote())


class AsyncMarketMaker(AbstractMarketMaker):

    def __init__(self, delegate):
        if isinstance(delegate, AbstractMarketMaker):
            self.actor_ref = RayMarketMaker.remote(delegate)
        else:
            self.actor_ref = delegate
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_participant(self, investor):
        if isinstance(investor, AsyncInvestor):
            self.actor_ref.register_participant.remote(investor.actor_ref)
        else:
            self.actor_ref.register_participant.remote(investor)

    def submit_orders(self, orders: List[Order]):
        self.actor_ref.submit_orders.remote(orders)

    def get_prices(self) -> Dict[str, Dict[str, float]]:
        return ray.get(self.actor_ref.get_prices.remote())

    def trades_in(self, stock: str) -> bool:
        return ray.get(self.actor_ref.trades_in.remote(stock))

    def osid(self) -> str:
        return ray.get(self.actor_ref.osid.remote())


@ray.remote
class RayMarketMaker:

    def __init__(self, delegate: AbstractMarketMaker):
        self.delegate = delegate
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_participant(self, investor):
        self.delegate.register_participant(AsyncInvestor(investor))

    def submit_orders(self, orders: List[Order]):
        try:
            self.delegate.submit_orders(orders)
        except Exception as rte:
            self.logger.error(f'{type(rte)}: {str(rte)}')

    def get_prices(self) -> Dict[str, Dict[str, float]]:
        return self.delegate.get_prices()

    def trades_in(self, stock: str) -> bool:
        return self.delegate.trades_in(stock)

    def osid(self) -> str:
        return self.delegate.osid()
