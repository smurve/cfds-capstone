import logging
from copy import deepcopy
from typing import Dict, List, Callable, Optional

from .abstract import (AbstractInvestor, AbstractMarket, AbstractMarketMaker,
                       AbstractTradingStrategyFactory, AbstractTradingStrategy)
from .Clock import Clock
from .Order import Order, OrderType, ExecutionType
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
                 strategy_factory: AbstractTradingStrategyFactory = None):

        self.logger = logging.getLogger(self.__class__.__name__)

        self.name = name
        self.portfolio = deepcopy(portfolio)
        self.cash = cash

        self.cash_reserve = self.cash / 10

        self.market = market
        self.market_makers: Dict[str, AbstractMarketMaker] = {}
        self.actions: Dict[int, Callable] = self.define_actions()
        self.info(f"Starting up. Qualified Name {self.get_qname()} may not reflect process id on destination host yet.")

        self.strategy_factory = strategy_factory
        self.strategy: Optional[AbstractTradingStrategy] = None

    def get_strategy(self) -> AbstractTradingStrategy:
        """
        Strategy creation needs to wait until the first tick, for this class may potentially be deployed after
        the constructor call. This is what Ray does.
        :return: A lazily initialized instance of the strategy
        """
        assert self.strategy_factory is not None, "Strategy factory must be supplied in constructor."
        if self.strategy is None:
            self.strategy = self.strategy_factory.create_strategy(
                investor_qname=self.get_qname(),
                portfolio=self.portfolio,
                market=self.market,
                max_volume_per_stock=self.cash / len(self.portfolio),
                logger=self.logger
            )
        return self.strategy

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

    def register_participant(self, market_maker: AbstractMarketMaker, symbol: str):
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

        prices_dict = {symbol: self.market_makers[symbol].get_prices()[symbol]
                       for symbol in self.portfolio}

        orders = self.get_strategy().suggest_orders(prices_dict=prices_dict,
                                                    cash=self.cash,
                                                    cash_reserve=self.cash_reserve,
                                                    clock=clock)

        for symbol in self.portfolio.keys():
            self.market_makers[symbol].submit_orders(orders[symbol], clock)

    def report_tx(self, order_type: OrderType, symbol: str, volume: float,
                  price: float, amount: float, clock: Clock):
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
        self.logger.info(f"{str(self)}: {msg}")

    def error(self, msg: str):
        self.logger.error(f"{str(self)}:: {msg}")

    def __repr__(self):
        return f'{self.get_qname()}'

    def get_name(self):
        return f"{self.name}"

    def get_qname(self):
        return f"{self.name} {self.osid()}"
