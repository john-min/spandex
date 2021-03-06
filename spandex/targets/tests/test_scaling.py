import numpy as np
import pandas as pd
import pandas.util.testing as pdt
import pytest

from spandex.targets import scaling as scl


@pytest.fixture(scope='module')
def col():
    return pd.Series([1, 2, 3, 4, 5])


@pytest.fixture(scope='module')
def target_col():
    return 'target_col'


@pytest.fixture(scope='module')
def df(target_col):
    #    a  b  a  b  a  b  a  b  a   b
    l = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    return pd.DataFrame(
        {target_col: l,
         'geo_id': ['a', 'b'] * 5,
         'filter_col': [x + 100 for x in l]})


@pytest.mark.parametrize('metric', ['mean', 'median'])
def test_scale_col_to_target_mean_median(col, metric):
    target = 600
    expected = pd.Series([200, 400, 600, 800, 1000])

    result = scl.scale_col_to_target(col, target, metric=metric)

    assert getattr(result, metric)() == target
    pdt.assert_series_equal(result, expected, check_dtype=False)


def test_scale_col_to_target_sum(col):
    target = 16
    expected = col * target / col.sum()

    result = scl.scale_col_to_target(col, target, metric='sum')

    assert result.sum() == target
    pdt.assert_series_equal(result, expected)


def test_scale_col_to_target_clip(col):
    target = 600
    clip_low = 450
    clip_high = 999
    expected = pd.Series([450, 450, 600, 800, 999])

    result = scl.scale_col_to_target(
        col, target, metric='mean', clip_low=clip_low, clip_high=clip_high)

    pdt.assert_series_equal(result, expected, check_dtype=False)


def test_scale_col_to_target_round(col):
    target = 16

    result = scl.scale_col_to_target(
        col, target, metric='sum', int_result=True)

    pdt.assert_series_equal(result, col)


def test_scale_to_targets(df, target_col):
    targets = [100, 1000]
    filters = [['geo_id == "a"', 'filter_col < 106'], 'geo_id == "b"']
    metric = 'sum'

    result = scl.scale_to_targets(df, target_col, targets, metric, filters)

    pdt.assert_index_equal(result.columns, df.columns)
    pdt.assert_series_equal(
        result[target_col],
        pd.Series(
            [11.11111111, 66.66666667, 33.33333333, 133.33333333, 55.55555556,
             200, 7, 266.66666667, 9, 333.33333333]),
        check_dtype=False)


def test_scale_to_targets_no_segments(df, target_col):
    target = [1000]
    metric = 'mean'

    result = scl.scale_to_targets(df, target_col, target, metric=metric)

    pdt.assert_index_equal(result.columns, df.columns)
    pdt.assert_series_equal(
        result[target_col],
        pd.Series(
            [181.81818182, 363.63636364, 545.45454545, 727.27272727,
             909.09090909, 1090.90909091, 1272.72727273, 1454.54545455,
             1636.36363636, 1818.18181818]),
        check_dtype=False)


def test_scale_to_targets_clip_int(df, target_col):
    target = [1000]
    metric = 'mean'
    clip_low = 400
    clip_high = 999.99
    int_result = True

    result = scl.scale_to_targets(
        df, target_col, target, metric, clip_low=clip_low, clip_high=clip_high,
        int_result=int_result)

    pdt.assert_index_equal(result.columns, df.columns)
    pdt.assert_series_equal(
        result[target_col],
        pd.Series([400, 400, 545, 727, 909, 1000, 1000, 1000, 1000, 1000]))


def test_scale_to_targets_from_table(df, target_col):
    targets = pd.DataFrame(
        {'column_name': [target_col, target_col],
         'target_value': [100, 1000],
         'target_metric': ['sum', 'sum'],
         'filters': ['geo_id == "a",filter_col < 106', 'geo_id == "b"'],
         'clip_low': [np.nan, np.nan],
         'clip_high': [np.nan, np.nan],
         'int_result': [np.nan, np.nan]})

    result = scl.scale_to_targets_from_table(df, targets)

    pdt.assert_index_equal(result.columns, df.columns)
    pdt.assert_series_equal(
        result[target_col],
        pd.Series(
            [11.11111111, 66.66666667, 33.33333333, 133.33333333, 55.55555556,
             200, 7, 266.66666667, 9, 333.33333333]),
        check_dtype=False)


def test_scale_to_targets_from_table_clip_int(df, target_col):
    targets = pd.DataFrame(
        {'column_name': [target_col],
         'target_value': [1000],
         'target_metric': ['mean'],
         'filters': [np.nan],
         'clip_low': [400],
         'clip_high': [999.99],
         'int_result': [True]})

    result = scl.scale_to_targets_from_table(df, targets)

    pdt.assert_index_equal(result.columns, df.columns)
    pdt.assert_series_equal(
        result[target_col],
        pd.Series([400, 400, 545, 727, 909, 1000, 1000, 1000, 1000, 1000]))


def test_targets_row_to_params():
    column = 'income'
    target = 100000
    metric = 'mean'
    filters = 'geo_id == "a",filter_col < 106'
    clip_low = 400
    clip_high = 999.9
    int_result = True

    row = pd.Series(
        [column, target, metric, filters, clip_low, clip_high, int_result],
        index=[
            'column_name', 'target_value', 'target_metric', 'filters',
            'clip_low', 'clip_high', 'int_result'])

    r = scl._targets_row_to_params(row)

    assert r.column == column
    assert r.target == target
    assert r.metric == metric
    assert r.filters == ['geo_id == "a"', 'filter_col < 106']
    assert r.clip_low == clip_low
    assert r.clip_high == clip_high
    assert r.int_result == int_result


def test_targets_row_to_params_defaults():
    column = 'income'
    target = 100000
    metric = 'mean'
    filters = np.nan
    clip_low = np.nan
    clip_high = np.nan
    int_result = np.nan

    row = pd.Series(
        [column, target, metric, filters, clip_low, clip_high, int_result],
        index=[
            'column_name', 'target_value', 'target_metric', 'filters',
            'clip_low', 'clip_high', 'int_result'])

    r = scl._targets_row_to_params(row)

    assert r.column == column
    assert r.target == target
    assert r.metric == metric
    assert r.filters is None
    assert r.clip_low is None
    assert r.clip_high is None
    assert r.int_result is False
