"""
Describe
========

Functions that are used to gather information about some data

  **DataFrame Accessor**: ``clarite_describe``

  **CLI Command**: ``describe``

  .. autosummary::
     :toctree: modules/describe

     correlations
     freq_table
     percent_na

"""

# Describe - functions that are used to gather information about some data

import numpy as np
import pandas as pd


def correlations(data, threshold: float = 0.75):
    """
    Return variables with pearson correlation above the threshold

    Parameters
    ----------
    data: pd.DataFrame
        The DataFrame to be described
    threshold: float, between 0 and 1
        Return a dataframe listing pairs of variables whose absolute value of correlation is above this threshold

    Returns
    -------
    result: pd.DataFrame
        DataFrame listing pairs of correlated variables and their correlation value

    Examples
    --------
    >>> import clarite
    >>> correlations = clarite.describe.correlations(df, threshold=0.9)
    >>> correlations.head()
                        var1      var2  correlation
    36704  supplement_count  DSDCOUNT     1.000000
    32807          DR1TM181  DR1TMFAT     0.997900
    33509          DR1TP182  DR1TPFAT     0.996172
    39575          DRD370FQ  DRD370UQ     0.987974
    35290          DR1TS160  DR1TSFAT     0.984733
    """
    # Get correlaton matrix
    correlation = data.corr()
    # Keep only the upper triangle to avoid listing both a-b and b-a correlations
    correlation = correlation.where(
        np.triu(np.ones(correlation.shape), k=1).astype(np.bool)
    )
    # Stack and rename into the desired format
    correlation = (
        correlation.stack()
        .rename("correlation")
        .rename_axis(["var1", "var2"])
        .reset_index()
    )
    # Remove those with correlation below threshold
    correlation = correlation.loc[correlation["correlation"].abs() >= threshold, ]
    # Sort by absolute value and return
    return correlation.reindex(
        correlation["correlation"].abs().sort_values(ascending=False).index
    )


def freq_table(data):
    """
    Return the count of each unique value for all categorical variables.  Non-categorical typed variables
    will return a single row with a value of '<Non-Categorical Values>' and the number of non-NA values.

    Parameters
    ----------
    data: pd.DataFrame
        The DataFrame to be described

    Returns
    -------
    result: pd.DataFrame
        DataFrame listing variable, value, and count for each categorical variable

    Examples
    --------
    >>> import clarite
    >>> clarite.describe.freq_table(df).head(n=10)
        variable value  count
    0                 SDDSRVYR                         2   4872
    1                 SDDSRVYR                         1   4191
    2                   female                         1   4724
    3                   female                         0   4339
    4  how_many_years_in_house                         5   2961
    5  how_many_years_in_house                         3   1713
    6  how_many_years_in_house                         2   1502
    7  how_many_years_in_house                         1   1451
    8  how_many_years_in_house                         4   1419
    9                  LBXPFDO  <Non-Categorical Values>   1032
    """
    # Define a function to be applied to each categorical variable
    def formatted_value_counts(var_name: str, df: pd.DataFrame):
        if str(df[var_name].dtype) == "category":
            df = (
                df[var_name]
                .value_counts()
                .reset_index()
                .rename({"index": "value", var_name: "count"}, axis="columns")
            )
            df["variable"] = var_name
            return df[["variable", "value", "count"]]  # reorder columns
        else:
            return pd.DataFrame.from_dict(
                {
                    "variable": [var_name],
                    "value": ["<Non-Categorical Values>"],
                    "count": [df[var_name].count()],
                }
            )

    return pd.concat(
        [formatted_value_counts(var_name, data) for var_name in list(data)]
    ).reset_index(drop=True)


def percent_na(data):
    """
    Return the percent of observations that are NA for each variable

    Parameters
    ----------
    data: pd.DataFrame
        The DataFrame to be described

    Returns
    -------
    result: pd.Series
        Series listing percent NA for each variable

    Examples
    --------
    >>> import clarite
    >>> clarite.describe.percent_na(df)
    SDDSRVYR                 0.000000
    female                   0.000000
    LBXHBC                   0.049321
    LBXHBS                   0.049873
    """
    return 1 - (data.count() / data.apply(len))
