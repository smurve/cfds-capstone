import logging
from typing import List, Dict

import ray

from .AbstractMarketMaker import AbstractMarketMaker
from .AsyncInvestor import AsyncInvestor
# from .AbstractInvestor import AbstractInvestor
from .Order import Order


@ray.remote
class RayMarketMaker:

    def __init__(self, delegate: AbstractMarketMaker):
        self.delegate = delegate
        self.logger = logging.getLogger(__name__)

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
