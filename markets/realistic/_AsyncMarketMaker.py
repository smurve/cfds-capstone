import logging
from typing import List, Dict

import ray

from .AbstractMarketMaker import AbstractMarketMaker
from .Order import Order
from .RayMarketMaker import RayMarketMaker


class AsyncMarketMaker(AbstractMarketMaker):

    def __init__(self, delegate):
        if isinstance(delegate, AbstractMarketMaker):
            self.actor_ref = RayMarketMaker.remote(delegate)
        else:
            self.actor_ref = delegate
        self.logger = logging.getLogger(__name__)

    def register_participant(self, investor):
        if type(investor) == 'AbstractInvestor':
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
