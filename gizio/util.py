import numpy as np


def np_equal(a, b):
    return (np.array(a) == np.array(b)).all()
