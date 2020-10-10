import logging
from copy import deepcopy
from typing import Dict, List, Callable

from .abstract import AbstractInvestor, AbstractMarket, AbstractMarketMaker, AbstractTradingStrategyFactory
from .Clock import Clock
from .Order import Order, OrderType, ExecutionType
from .AbstractMarketScenario import ScenarioError
from .TriangularOrderGenerator import TriangularOrderGenerator


class ChartInvestor(AbstractInvestor):
    """
    An Investor that trades based on historic market data and current valuations
    """

    def __init__(self,
                 market: AbstractMarket,
                 portfolio: Dict[str, float],
                 cash: float,
                 name: str,
                 strategy_factory: AbstractTradingStrategyFactory):

        self.logger = logging.getLogger(self.__class__.__name__)

        self.name = name
        self.portfolio = deepcopy(portfolio)
        self.cash = cash

        self.action_threshold = 0.01  # act if price/value ratio exceeds that
        self.cash_reserve = self.cash / 10
        self.max_volume_per_stock = self.cash / len(self.portfolio)
        self.n_orders_per_trade = 10
        self.kappa = 0.5  # larger kappa means orders more offset from the value -> better deals
        self.default_expire_after_seconds = 10

        self.market = market
        self.market_makers: Dict[str, AbstractMarketMaker] = {}
        self.actions: Dict[int, Callable] = self.define_actions()
        self.order_generator = None
        self.debug("Starting up. OSID may not reflect final host process yet.")

        self.strategy = strategy_factory.create_strategy(
            investor_qname=self.get_qname(),
            portfolio=self.portfolio,
            market_makers={symbol: mm.osid() for (symbol, mm) in self.market_makers.items()},
            market=self.market,
            max_volume_per_stock=self.cash / len(self.portfolio),
            logger=self.logger
        )

    def create_orders_list(self, symbol: str, p: float, tau: float, n: float,
                           order_type: OrderType, execution_type: ExecutionType,
                           expires_at: int, n_orders: int) -> List[Order]:

        # Lazily initialize order generator to get the correct ray-deployed qname
        if self.order_generator is None:
            self.order_generator = TriangularOrderGenerator(self.get_qname())

        return self.order_generator.create_orders_list(symbol, p, tau, n, order_type, execution_type,
                                                       expires_at, n_orders)

    def define_actions(self) -> Dict[int, Callable]:
        # something to start with
        return {1: self.act_on_price_vs_value}

    def tick(self, clock: Clock) -> str:
        self.debug('Received tick.')
        self.observe_and_act(clock)
        return 'OK'

    def get_stock_symbols(self) -> List[str]:
        return list(self.portfolio.keys())

    def register_with(self, market_maker: AbstractMarketMaker, symbol: str):
        self.debug(f"Registering for {symbol} with market maker: {market_maker.osid()}")
        self.market_makers[symbol] = market_maker

    def find_due_actions(self, clock: Clock):
        return [self.actions[f] for f in self.actions.keys() if clock.seconds % f == 0]

    def observe_and_act(self, clock: Clock):
        actions = self.find_due_actions(clock)
        for action in actions:
            self.debug(f"Performing action: {action}")
            action(clock)

    def act_on_price_vs_value(self, clock: Clock):
        pass

    def _act_on_price_vs_value(self, clock: Clock):

        prices_dict = {market_maker: market_maker.get_prices()
                       for market_maker in self.market_makers.values()}

        for symbol in self.portfolio.keys():
            self.debug(f"Looking at {symbol}")
            market_maker = self.market_makers.get(symbol)
            if not market_maker:
                self.error(f"No market maker for {symbol}")
                raise ScenarioError(f'No market maker for stock {symbol}.')

            price = prices_dict[market_maker][symbol]['last']
            self.debug(f'Price for {symbol}: {price}')
            value = self.market.get_intrinsic_value(symbol, clock.day())
            self.debug(f'Value for {symbol}: {value}')

            if abs(1 - price / value) > self.action_threshold:
                tau = 2 * abs((price - value) / price)
                order_type = OrderType.BID if price < value else OrderType.ASK

                # kappa > 0 means a buffer from the value
                center = (1 + self.kappa) * price - self.kappa * value

                execution_type = ExecutionType.LIMIT
                n = self.determine_n_shares(price)
                expiry = self.determine_expiry(clock).seconds
                orders = self.create_orders_list(symbol, center, tau, n, order_type,
                                                 execution_type, expiry, self.n_orders_per_trade)

                self.debug(f'Submitting {order_type.value} orders.')
                market_maker.submit_orders(orders, clock)
            else:
                self.debug(f"Not sumitting oder: {abs(1 - price / value)} not above {self.action_threshold}")

    def determine_n_shares(self, price) -> float:
        volume = max(0., min(self.max_volume_per_stock, self.cash - self.cash_reserve))
        return int(volume / price) if volume > price else 0

    def determine_expiry(self, clock: Clock) -> Clock:
        return Clock(initial_seconds=clock.seconds + self.default_expire_after_seconds)

    def report_tx(self, order_type: OrderType, symbol: str, volume: float, price: float, amount: float, clock: Clock):
        self.debug(f"Updating portfolio position for {symbol}")
        self.cash += amount if order_type == OrderType.ASK else -amount
        self.portfolio[symbol] += volume if order_type == OrderType.BID else -volume
        self.debug(f"{int(volume)} shares at {price}.")
        self.debug(f"cash: {self.cash} - new number of shares: {self.portfolio[symbol]}.")

    def report_expiry(self, order: Order):
        self.debug(f"Some order expired, I don't care for now.")

    def get_portfolio(self):
        portfolio = deepcopy(self.portfolio)
        portfolio['CASH'] = self.cash
        return portfolio

    def debug(self, msg: str):
        self.logger.debug(f"{str(self)}: {msg}")

    def info(self, msg: str):
        self.logger.debug(f"{str(self)}: {msg}")

    def error(self, msg: str):
        self.logger.error(f"{str(self)}:: {msg}")

    def __repr__(self):
        return f'{self.get_qname()}'

    def get_name(self):
        return f"{self.name}"

    def get_qname(self):
        return f"{self.name} {self.osid()}"

    def osid(self) -> str:
        import os
        return f'({os.getpid()}-{id(self)})'
