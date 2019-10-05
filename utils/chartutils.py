import matplotlib.pyplot as plt


def plot_many(rows, cols, width, height, data=None, titles=None, xlim=None):
    fig, plots = plt.subplots(rows, cols)
    fig.set_figheight(height)
    fig.set_figwidth(width)

    if data is not None:
        for p, d in zip(plots, data):
            for c in d:
                p.plot(*c)
    if titles is not None:
        for p, c in zip(plots, titles):
            p.set_title(c)
    if xlim is not None:
        for p in plots:
            p.set_xlim(xlim)
    return plots
