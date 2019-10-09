import numpy as np
import uuid


class Trending:
    def __init__(self, name, sentiments):
        """
        Parameters:
        sentiments: A map {t_i: (a_i, b_i)} that defines the discontinuous piecewise
        linear sentiment function. See implementation of phi(t) to understand.
        """
        self.name = name
        self.sentiments = sentiments

    def phi(self, t):
        periods = sorted(self.sentiments.items())
        current_period = 0
        for p in periods:
            if p[0] > t:
                break
            else:
                current_period = p
        t0, (alpha, beta) = current_period
        return alpha + (t - t0) * beta


class GeoMarket(Trending):
    def __init__(self, name, sentiments):
        super(GeoMarket, self).__init__(name, sentiments)


class Segment(Trending):
    def __init__(self, name, sentiments):
        super(Segment, self).__init__(name, sentiments)


class Stock(Trending):
    def __init__(self, name, psi0, e_cagr, sentiments, max_effect,
                 noise, segments=None, markets=None, days_per_year=256):
        """
        Parameters: 
        psi0: the initial average perceived value of the stock
        e_cagr: the expacted compound annual growth rate for constant neutral sentiment
        sentiments: A map of periods - see class Trending
        max_effect: the maximum multiplier to the true value that the sentiment can achieve
        segments: map of segments as keys and their weights (adding up to 1.0)
        """
        super(Stock, self).__init__(name, sentiments)
        if segments is None:
            segments = {}
        self.days_per_year = days_per_year
        self.psi0 = psi0
        self.nu = np.log(1 + e_cagr)
        self.max_effect = max_effect
        self.noise = noise
        self.segments = segments
        self.markets = markets

    def value(self, t):
        return np.random.normal(self.psi(t), self.noise)

    def psi(self, t):
        """
        the total sentiment score from all geomarket exposures and segments
        """

        def sentiment_effect(x):
            k = self.max_effect
            delta = np.log(k - 1)
            return k / (1 + np.exp(-x + delta))

        sentiment = self.phi(t) + (
            np.sum([s[1] * s[0].phi(t) for s in self.segments.items()]) +
            np.sum([m[1] * m[0].phi(t) for m in self.markets.items()]))

        return self.psi0 * np.exp(t / self.days_per_year * self.nu) * sentiment_effect(sentiment)


class Order:
    def __init__(self, tx, other_party, ticker, amount, price):
        self.order_id = uuid.uuid4().hex
        self.tx = tx
        self.other_party = other_party
        self.ticker = ticker
        self.amount = amount
        self.price = price

    def __repr__(self):
        return (self.tx + ": " + str(self.amount) + " " + self.ticker
                + " for " + str(self.price))


class Bid(Order):
    def __init__(self, other_party, ticker, amount, price):
        super().__init__('bid', other_party, ticker, amount, price)


class Ask(Order):
    def __init__(self, other_party, ticker, amount, price):
        super().__init__('ask', other_party, ticker, amount, price)


class OrderStatus:

    DEFERED = 'DEFERED'
    EXECUTED = 'EXECUTED'
    IGNORED = 'IGNORED'

    def __init__(self, order_id, status):
        self.order_id = order_id
        self.status = status

    def is_defered(self):
        return self.status == OrderStatus.DEFERED

    def is_executed(self):
        return self.status == OrderStatus.EXECUTED

    def is_ignored(self):
        return self.status == OrderStatus.IGNORED


class OrderExecuted(OrderStatus):
    def __init__(self, order, price):
        super().__init__(order.order_id, OrderStatus.EXECUTED)
        self.tx_price = price


class OrderIgnored(OrderStatus):
    def __init__(self, order):
        super().__init__(order.order_id, OrderStatus.IGNORED)


class OrderDefered(OrderStatus):
    def __init__(self, order):
        super().__init__(order.order_id, OrderStatus.DEFERED)


class Market:
    def __init__(self, bid_ask, stocks=None):
        self.t = 0
        self.is_open = False
        self.orders = {
            'ask': {},
            'bid': {}
        }
        self.prices = {}
        
        self.spread = bid_ask
        self.history = {}
        self.daily = {}
        
        self.stocks = {}

        if stocks:
            for stock in stocks:
                self.stocks[stock.name] = stock
                self.orders['ask'][stock.name] = {} 
                self.orders['bid'][stock.name] = {} 
                # The market starts with an estimate
                p = round(stock.value(0), 3)
                self.prices[stock.name] = p
                self.daily[stock.name] = []
                self.history[stock.name] = []
                self.history[stock.name].append([p, p, p, p])
        
    def open(self):
        if self.is_open:
            print("Already open.")
            return
        self.is_open = True
        self.t += 1
        for _ in self.prices:
            self.daily = {ticker: [] for ticker in self.prices}
            
    def close(self):
        if not self.is_open:
            print("Already closed.")
            return
        self.is_open = False
        for ticker in self.daily:
            if self.daily[ticker]:
                # use the close of the last history entry
                p = self.history[ticker][-1][1]
                self.history[ticker].append([p, p, p, p])
            else:
                p_open = self.daily[ticker][0]
                p_close = self.daily[ticker][-1]
                p_high = np.max(self.daily[ticker])
                p_low = np.min(self.daily[ticker])
                self.history[ticker].append([p_open, p_close, p_high, p_low])
        return self.daily.copy()

    def tx_price(self, ticker, tx):
        delta = self.spread if tx == 'bid' else -self.spread
        return round(self.prices[ticker] + delta, 3)

    def execute(self, order, defer=True, reprocessing=False):
                    
        if not self.is_open:
            print("Market is closed.")
            return

        # bid-ask spread
        tx_price = self.tx_price(order.ticker, order.tx)
        
        # If we have an immediate match
        if (order.price >= tx_price and order.tx == 'bid') or (order.price <= tx_price and order.tx == 'ask'):
            if order.tx == 'bid':
                order.other_party.buy(order.ticker, order.amount, tx_price)
            else:
                order.other_party.sell(order.ticker, order.amount, tx_price)

            # Compute new price - only for original orders, not for deferred ones
            if not reprocessing:
                self.prices[order.ticker] = tx_price
                self.daily[order.ticker].append(tx_price)
                
            _ = self.maybe_process_defered('ask' if order.tx == 'bid' else 'bid', order.ticker)

            return OrderExecuted(order, tx_price)
        
        else:
            if defer:
                self.orders[order.tx][order.ticker][order.order_id] = order
                return OrderDefered(order)
                    
        return OrderIgnored(order)

    def remove_order(self, order):
        tx, ticker, order_id = order.tx, order.ticker, order.order_id
        del(self.orders[tx][ticker][order_id])

    def maybe_process_defered(self, tx, ticker):
        order_ids = list(self.orders[tx][ticker].keys())
        last_status = None
        for order_id in order_ids:
            order = self.orders[tx][ticker][order_id]
            status = self.execute(order, defer=True, reprocessing=True)
            last_status = status
            if status.is_executed():
                self.remove_order(order)
        return last_status

    def price_for(self, ticker):
        return self.tx_price(ticker, 'bid'), self.tx_price(ticker, 'ask')

    def value_for(self, ticker):
        return self.stocks[ticker].value(self.t)
    
    def history_for(self, ticker):
        return list(self.history[ticker])
    

class Investor:
    def __init__(self, name, cash, portfolio):
        self.cash = cash
        self.name = name
        self.portfolio = portfolio

    def sell(self, symbol, n, p):
        self.cash = round(self.cash + n * p, 3)
        pos = self.portfolio[symbol]
        self.portfolio[symbol] = pos - n

    def buy(self, symbol, n, p):
        self.cash = round(self.cash - n * p, 3)
        pos = self.portfolio[symbol]
        self.portfolio[symbol] = pos + n

    def __repr__(self):
        return self.name + " (cash: " + str(self.cash) + ", " + str(self.portfolio) + ")"

    
class MomentumInvestor(Investor):
    """
    A momentum investor who has some reasoning wrt true value
    """
    def __init__(self, name, wealth, portfolio, w_value=0.5, w_momentum=0.5, trend_span=20):
        self.w_value = w_value
        self.w_momentum = w_momentum
        self.trend_span = trend_span
        self.history = []
        super().__init__(name, wealth, portfolio)
        
    def act(self, market):
        for ticker in market.prices:
            self.act_on(market, ticker)
        
    def act_on(self, market, ticker):
        _, ask = market.price_for(ticker)
        h = market.history_for(ticker)
        h = h[-self.trend_span:]
        bid_price, ask_price = market.price_for(ticker)
        if len(h) > 0:
            # comparing opening prices
            n_tx = 10
            momentum = np.log(h[-1][0] / h[0][0])
            value_diff = np.log(market.value_for(ticker) / bid_price)
            incentive = value_diff * self.w_value + momentum * self.w_momentum
            incentive = np.random.normal(incentive, .2)
            self.history.append([value_diff, momentum, incentive])
            if incentive > 0:
                if self.cash > n_tx * bid_price + 1000.0:
                    market.execute(Bid(self, ticker, n_tx, bid_price))
            else:
                if self.portfolio[ticker] >= n_tx:
                    market.execute(Ask(self, ticker, n_tx, ask_price))
