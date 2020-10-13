from ..MarketMaker import MarketMaker
from ..Statistician import Statistician
from ..USITMarket import USITMarket
from ..Ensemble import Ensemble
from ..BiasedMarketView import BiasedMarketView, INTRINSIC_VALUE
from ..ChartInvestor import ChartInvestor
from ..strategy import PriceValueStrategyFactory

#
#     The market and the market makers
#
_us_it_market_ = USITMarket(
    {'TSMC': 186.73,
     'AAPL': 201.22,
     'NKLA': 222.14,
     'TSLA': 462.40},
    noise=0.0)

initial_prices = {stock.name: round(stock.psi(0), 2) for stock in _us_it_market_.get_stocks()}
_market_maker_ = MarketMaker(initial_prices)

#
#     The investors
#
_warren_ = ChartInvestor(market=BiasedMarketView(market=_us_it_market_,
                                                 biases={
                                                     INTRINSIC_VALUE: lambda v: 0.96 * v}
                                                 ),
                         name='Warren Buffet',
                         portfolio={'TSMC': 5000},
                         cash=200_000,
                         strategy_factory=PriceValueStrategyFactory(
                             action_threshold=0.01
                         ))


_michael_ = ChartInvestor(market=BiasedMarketView(market=_us_it_market_,
                                                  biases={
                                                      INTRINSIC_VALUE: lambda v: 1.04 * v}
                                                  ),
                          name='Warren Buffet',
                          portfolio={'TSMC': 5000},
                          cash=200_000,
                          strategy_factory=PriceValueStrategyFactory(
                              action_threshold=0.01
                          ))

_raphi_ = Statistician()

#
#     The ensemble
#
ensemble = Ensemble(
    markets=[_us_it_market_],
    market_makers={_market_maker_: _raphi_},
    investors=[_warren_, _michael_]
)
