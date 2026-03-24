import pandas as pd
import numpy as np

def compute_ewma(returns:pd.Series, span: int = 30) -> pd.Series:
    """
    Compute EWMA volatility from a return series.

    Parameters are:

    returns: pd.Series -> Daily log returns

    span: int -> Decay parameter in days (default 30)

    Return is:
    pd.Series -> Annualised EWMA volatility
    """
    variance = returns.ewm(span=span).var()
    return (variance ** 0.5) * (252 ** 0.5)