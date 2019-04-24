from typing import Optional, List

import pandas as pd

from .utilities import _validate_skip_only


@pd.api.extensions.register_dataframe_accessor("colfilter")
class ColFilterAccessor(object):
    def __init__(self, pandas_obj):
        self._validate(pandas_obj)
        self._obj = pandas_obj

    @staticmethod
    def _validate(obj):
        # TODO: Perform any required validation
        if False:
            raise AttributeError("")

    def percent_zero(self, max_proportion: float = 0.9, skip: Optional[List[str]] = None, only: Optional[List[str]] = None):
        """Remove columns which have >= <max_proportion> values of zero (excluding NA)"""
        df = self._obj
        columns = _validate_skip_only(list(df), skip, only)
        num_before = len(df.columns)

        percent_value = df.apply(lambda col: sum(col == 0) / col.count())
        kept = (percent_value < max_proportion) | ~df.columns.isin(columns)
        num_removed = num_before - sum(kept)

        print(f"Removed {num_removed:,} of {num_before:,} variables ({num_removed/num_before:.2%}) "
              f"which were equal to zero in at least {max_proportion:.2%} of non-NA observations.")
        return df.loc[:, kept]
