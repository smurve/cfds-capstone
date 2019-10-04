import numpy as np


# average along the axis using sections of a given length
def avg_over_axis(orig, axis, section):
    """
    calculates the piece-wise averages along an axis. Essentially an average pooling
    along a single axis.

    Example: avg_over_axis([[1,2,3,4,5,6], [3,4,5,6,7,8]], 0, 2) == [2,3,4,5,6,7]
    :param orig: an numpy array
    :param axis: axis to average along
    :param section: number of values to average amongst. Must divide orig.shape[axis]
    :return: a numpy array with 'axis' reduced to by averaging every 'section' values.
    """
    shape = np.shape(orig)
    dim_a = shape[axis]
    expanded = np.expand_dims(orig, axis+1)
    new_shape = list(expanded.shape)
    new_shape[axis] = dim_a//section
    new_shape[axis+1] = section

    reshaped = np.reshape(orig, new_shape)
    rolled = np.rollaxis(reshaped, axis+1, 0)
    avg = 0
    for r in rolled:
        avg += r / section
    return avg
