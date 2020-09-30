import uuid
from copy import deepcopy
from typing import Dict, List, Callable

from .SynchronousMarketScenario import ScenarioError
from .AbstractMarketMaker import AbstractMarketMaker
from .Clock import Clock
from .AbstractMarket import AbstractMarket
from .TriangularOrderGenerator import TriangularOrderGenerator
from .Order import OrderType, ExecutionType
from .AbstractInvestor import AbstractInvestor


class ChartInvestor(AbstractInvestor):

    def __init__(self,
                 market: AbstractMarket,
                 portfolio: Dict[str, float],
                 cash: float,
                 name: str = None,
                 unique_id: uuid.UUID = uuid.uuid4()):

        self.name = name
        self.unique_id = unique_id

        self.portfolio = deepcopy(portfolio)
        self.cash = cash

        self.action_threshold = 0.01  # act if price/value ratio exceeds that
        self.cash_reserve = self.cash / 10
        self.max_volume_per_stock = self.cash / len(self.portfolio)
        self.n_orders_per_trade = 10

        self.market = market
        self.market_makers: Dict[str, AbstractMarketMaker] = {}
        self.actions: Dict[int, Callable] = self.define_actions()
        self.order_generator = TriangularOrderGenerator(self.unique_id)

    def define_actions(self) -> Dict[int, Callable]:
        # something to start with
        return {1: self.act_on_price_vs_value}

    def __repr__(self):
        return self.name if self.name else str(self.unique_id)

    def tick(self, clock: Clock) -> str:
        self.observe_and_act(clock)
        return 'OK'

    def identify(self) -> str:
        return self.name if self.name else self.unique_id

    def get_stock_symbols(self) -> List[str]:
        return list(self.portfolio.keys())

    def register_with(self, market_maker: AbstractMarketMaker, symbol: str):
        self.market_makers[symbol] = market_maker

    def find_due_actions(self, clock: Clock):
        return [self.actions[f] for f in self.actions.keys() if clock.seconds % f == 0]

    def observe_and_act(self, clock: Clock):
        for action in self.find_due_actions(clock):
            action(clock)

    def act_on_price_vs_value(self, clock: Clock):

        prices_dict = {market_maker: market_maker.get_prices()
                       for market_maker in self.market_makers.values()}

        for symbol in self.portfolio.keys():
            market_maker = self.market_makers.get(symbol)
            if not market_maker:
                raise ScenarioError(f'No market maker for stock {symbol}.')

            price = prices_dict[market_maker][symbol]['last']
            value = self.market.get_intrinsic_value(symbol, clock.day())

            if abs(1 - price / value) > self.action_threshold:
                center = (price + value) / 2
                tau = abs((price - value) / price)
                order_type = OrderType.BID if price < value else OrderType.ASK
                execution_type = ExecutionType.LIMIT
                n = self.determine_n_shares(price)
                expiry = self.determine_expiry()
                orders = self.order_generator.create_orders_list(symbol, center, tau, n, order_type,
                                                                 execution_type, expiry, self.n_orders_per_trade)

                market_maker.submit_orders(orders)

    def determine_n_shares(self, price) -> float:
        volume = max(0., min(self.max_volume_per_stock, self.cash - self.cash_reserve))
        return int(volume / price) if volume > price else 0

    @staticmethod
    def determine_expiry() -> int:
        return 10
