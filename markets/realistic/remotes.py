from __future__ import annotations

import abc
import logging
from typing import List, Dict, Tuple

import ray
from ray.actor import ActorHandle

from .Clock import Clock
from .Order import Order
from .abstract import AbstractInvestor, AbstractMarketMaker, AbstractStatistician, AbstractParticipant


class AsyncParticipant(abc.ABC):

    def __init__(self, actor_ref):
        self.actor_ref = actor_ref
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_participant(self, other_participant, **kwargs):
        if isinstance(other_participant, AsyncParticipant):
            self.logger.debug(f'{self.osid()}: registering actor_ref of {other_participant.osid()}')
            self.actor_ref.register_participant.remote(other_participant.actor_ref, **kwargs)
        elif isinstance(other_participant, ActorHandle):
            self.logger.debug(f'{self.osid()}: registering {other_participant.osid()}')
            self.actor_ref.register_participant.remote(other_participant, **kwargs)
        else:
            self.logger.error(f'{self.osid()}')

    def osid(self):
        return ray.get(self.actor_ref.osid.remote())


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

    def register_participant(self, other_participant: ActorHandle, **kwargs):
        try:
            role = ray.get(other_participant.get_role.remote())
            if role == 'MarketMaker':
                self.logger.info(f"{self.get_qname()}: "
                                  f"Registering MarketMaker {ray.get(other_participant.osid.remote())}.")
                return self.delegate.register_participant(AsyncMarketMaker(other_participant), **kwargs)
            elif role == 'Statistician':
                self.logger.info(f"{self.get_qname()}: "
                                 f"Registering Statistician {ray.get(other_participant.osid.remote())}.")
                return self.delegate.register_participant(AsyncStatistician(other_participant), **kwargs)

        except Exception as e:
            self.logger.error(f'{self.get_qname()}: Failed to register participant.')
            self.logger.error(f'OSID was {ray.get(other_participant.osid.remote())}')
            raise e

    def report_tx(self, order_type, symbol: str, volume: float, price: float, amount: float, clock: Clock):
        self.delegate.report_tx(order_type, symbol, volume, price, amount, clock)

    def report_expiry(self, order: Order):
        self.delegate.report_expiry(order)

    def get_portfolio(self):
        return self.delegate.get_portfolio()

    def get_name(self) -> str:
        return self.delegate.get_name()

    def osid(self) -> str:
        return self.delegate.osid()

    def get_qname(self) -> str:
        return self.delegate.get_qname()

    def get_role(self) -> str:
        return self.delegate.get_role()


class AsyncInvestor(AsyncParticipant, AbstractInvestor):

    def __init__(self, delegate):
        if isinstance(delegate, AbstractInvestor):
            super().__init__(RayInvestor.remote(delegate))
        else:
            super().__init__(delegate)
        self.logger = logging.getLogger(self.__class__.__name__)

    def tick(self, clock: Clock):
        self.logger.debug(f'{self.get_name()} here. Ticking remote delegate.')
        self.actor_ref.tick.remote(clock)

    def get_stock_symbols(self) -> List[str]:
        return ray.get(self.actor_ref.get_stock_symbols.remote())

    def report_tx(self, order_type, symbol: str, volume: float, price: float, amount: float, clock: Clock):
        self.logger.debug(f'{self.get_qname()} here. Reporting transaction to remote.')
        self.actor_ref.report_tx.remote(order_type, symbol, volume, price, amount, clock)

    def report_expiry(self, order: Order):
        self.actor_ref.report_expiry.remote(order)

    def get_portfolio(self):
        return ray.get(self.actor_ref.get_portfolio.remote())

    def get_name(self):
        return ray.get(self.actor_ref.get_name.remote())

    def get_qname(self) -> str:
        return ray.get(self.actor_ref.get_qname.remote())


@ray.remote
class RayMarketMaker:

    def __init__(self, delegate: AbstractMarketMaker):
        self.delegate = delegate
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_participant(self, investor, **kwargs):
        self.delegate.register_participant(AsyncInvestor(investor), **kwargs)

    def submit_orders(self, orders: List[Order], clock: Clock):
        try:
            self.delegate.submit_orders(orders, clock)
        except Exception as rte:
            self.logger.error(f'{type(rte)}: {str(rte)}')

    def get_prices(self) -> Dict[str, Dict[str, float]]:
        return self.delegate.get_prices()

    def get_order_book(self) -> Dict[str, Dict[float, Tuple[str, float]]]:
        return self.delegate.get_order_book()

    def trades_in(self, stock: str) -> bool:
        return self.delegate.trades_in(stock)

    def osid(self) -> str:
        return self.delegate.osid()

    def get_role(self) -> str:
        return self.delegate.get_role()


class AsyncMarketMaker(AsyncParticipant, AbstractMarketMaker):

    def __init__(self, delegate):
        if isinstance(delegate, AbstractMarketMaker):
            super().__init__(RayMarketMaker.remote(delegate))
        else:
            super().__init__(delegate)

    def submit_orders(self, orders: List[Order], clock: Clock):
        self.actor_ref.submit_orders.remote(orders, clock)

    def get_prices(self) -> Dict[str, Dict[str, float]]:
        return ray.get(self.actor_ref.get_prices.remote())

    def get_order_book(self) -> Dict[float, Tuple[str, float]]:
        return ray.get(self.actor_ref.get_order_book.remote())

    def trades_in(self, stock: str) -> bool:
        return ray.get(self.actor_ref.trades_in.remote(stock))


@ray.remote
class RayStatistician:
    def __init__(self, delegate: AbstractStatistician):
        self.delegate = delegate
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_chart_data(self, **queryargs):
        return self.delegate.get_chart_data(**queryargs)

    def report_transaction(self, symbol: str, volume: float, price: float, clock: Clock):
        self.delegate.report_transaction(symbol, volume, price, clock)

    def register_participant(self, other_participant: AbstractParticipant, **kwargs):
        self.delegate.register_participant(other_participant, **kwargs)

    def get_role(self) -> str:
        return self.delegate.get_role()


class AsyncStatistician(AsyncParticipant, AbstractStatistician):
    def __init__(self, delegate):
        if isinstance(delegate, AsyncStatistician):
            super().__init__(RayStatistician.remote(delegate))
        else:
            super().__init__(delegate)

    def get_chart_data(self, **queryargs):
        return ray.get(self.actor_ref.get_chart_data.remote(**queryargs))

    def report_transaction(self, symbol: str, volume: float, price: float, clock: Clock):
        self.actor_ref.report_transaction.remote(symbol, volume, price, clock)
