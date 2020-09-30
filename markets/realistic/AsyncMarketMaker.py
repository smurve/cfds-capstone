from typing import List, Dict
from uuid import UUID
import ray

from .AbstractMarketMaker import AbstractMarketMaker
from .Order import Order


@ray.remote
class RayMarketMaker:

    def __init__(self, delegate: AbstractMarketMaker):
        self.delegate = delegate

    def register_participant(self, uuid: UUID, portfolio: dict):
        self.delegate.register_participant(uuid, portfolio)

    def submit_orders(self, orders: List[Order]):
        self.delegate.submit_orders(orders)

    def get_prices(self) -> Dict[str, Dict[str, float]]:
        return self.delegate.get_prices()

    def trades_in(self, stock: str) -> bool:
        return self.delegate.trades_in(stock)


class AsyncMarketMaker(AbstractMarketMaker):

    def __init__(self, delegate: AbstractMarketMaker):
        self.delegate = RayMarketMaker.remote(delegate)

    def register_participant(self, uuid: UUID, portfolio: dict):
        self.delegate.register_participant.remote(uuid, portfolio)

    def submit_orders(self, orders: List[Order]):
        self.delegate.submit_orders.remote(orders)

    def get_prices(self) -> Dict[str, Dict[str, float]]:
        return ray.get(self.delegate.get_prices.remote())

    def trades_in(self, stock: str) -> bool:
        return ray.get(self.delegate.trades_in.remote())

