import numpy as np


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

    def __repr__(self):
        return self.name


class Segment(Trending):
    def __init__(self, name, sentiments):
        super(Segment, self).__init__(name, sentiments)

    def __repr__(self):
        return self.name


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

    def __repr__(self):
        return self.name

    def value(self, t):
        return np.random.normal(self.psi(t), self.noise)

    def psi(self, t):
        """
        The intrinsic value of this stock
        """

        def sentiment_effect(x):
            k = self.max_effect
            delta = np.log(k - 1)
            return k / (1 + np.exp(-x + delta))

        sentiment = self.phi(t) + (
            np.sum([s[1] * s[0].phi(t) for s in self.segments.items()]) +
            np.sum([m[1] * m[0].phi(t) for m in self.markets.items()]))

        return self.psi0 * np.exp(t / self.days_per_year * self.nu) * sentiment_effect(sentiment)
