import pandas as pd
import numpy as np
import uuid
import unicodedata
import re

def clean_str(x):
    x = x.strip()
    x = re.sub(' +', ' ', x)
    return x


def strip_accents(s):
    """
    remove accents from a string.
    Parameters
    ----------
    s :str
    string

    Returns
    -------

    """
    s = s.replace('\xb0C', 'degC')
    s = s.replace('\xb5', 'u')
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def intervals_to_category(s, cat_dict):
    """
    transform numerical serie to categorical str enum comparing numerical values with intervals defining the categories.
    Parameters
    ----------
    s : pd.Series
    cat_dict :dict
    a dictionary that have as keys enum categories and as values a tuple of an interval of numerical values.

    Returns
    -------

    """
    s_cat = s.copy()
    for k, v in cat_dict.items():
        s_cat[s.between(*v)] = k
    return s_cat


def _prep_agg_pond(table, pond, bool_filter_col, pond_col, bool_filter_not):
    """

    Parameters
    ----------
    table : pd.DataFrame
    by : str or list
    pandas.DataFrame.Groupby argument
    pond : str,list
    column or columns containing numeric values
    bool_filter_col : str
    column containing a boolean array to filter data
    bool_filter_not : bool
    if true take the negative of the boolean array instead
    pond_col:str
    name of the pond column.

    Returns
    -------
    table : pd.DataFrame
    transformed table

    """
    if bool_filter_col is not None:
        if bool_filter_not:
            table = table.loc[~table[bool_filter_col].astype(bool), :]
        else:
            table = table.loc[table[bool_filter_col].astype(bool), :]
    if isinstance(pond, str):
        table[pond_col] = table[pond]
    elif isinstance(pond, (list, tuple)):
        table[pond_col] = 1
        for col in pond:
            table[pond_col] = table[pond_col] * table[col]
    else:
        raise BaseException('pond must be str,list or tuple not {}'.format(type(pond)))
    return table


def agg_pond_avg(table, value_col, pond, by, bool_filter_col=None, bool_filter_not=False):
    """
    function to make an average ponderate serie from a table column
    Parameters
    ----------
    table : pd.DataFrame

    value_col : str
    column containing numeric values
    pond : str,list
    column or columns containing numeric values
    by : str or list
    pandas.DataFrame.Groupby argument
    bool_filter_col : str
    column containing a boolean array to filter data
    bool_filter_not : bool
    if true take the negative of the boolean array instead

    Returns
    -------
    grp : pd.Series
    serie of ponderate avg of value_col

    """
    pond_col = str(uuid.uuid4())
    table = _prep_agg_pond(table, pond, bool_filter_col, pond_col, bool_filter_not)
    pond_value_col_temp = str(uuid.uuid4())
    table[pond_value_col_temp] = table[pond_col] * table[value_col]
    null = table[pond_value_col_temp].isnull()
    null = null | table[pond_col].isnull()
    table.loc[null, [pond_col, pond_value_col_temp]] = np.nan
    grp = table.groupby(by)[[pond_col, pond_value_col_temp]].sum()
    grp[grp[pond_col] <= 0] = np.nan
    s_grp = grp[pond_value_col_temp] / grp[pond_col]
    del table[pond_col]
    del table[pond_value_col_temp]

    return s_grp


def agg_pond_top_freq(table, enum_col, pond, by, bool_filter_col=None, bool_filter_not=False):
    """
    function to make an topfreq ponderate serie from a table column

    Parameters
    ----------
    table : pd.DataFrame

    enum_col : str
    column containing enumerator values
    pond : str,list
    column or columns containing numeric values
    by : str or list
    pandas.DataFrame.Groupby argument
    bool_filter_col : str
    column containing a boolean array to filter data
    bool_filter_not : bool
    if true take the negative of the boolean array instead

    Returns
    -------
    grp : pd.Series
    serie of ponderated topfreq of enum_col

    """

    pond_col = 'pond9999999'
    table = _prep_agg_pond(table, pond, bool_filter_col, pond_col, bool_filter_not)
    grp = table.groupby([by, enum_col])[pond_col].sum()
    is_0 = grp[pond_col] == 0
    grp.loc[is_0, enum_col] = np.nan
    s = grp.reset_index().sort_values([by, pond_col], ascending=False).drop_duplicates(subset=by).set_index(by)[
        enum_col]

    return s


def affect_lib_by_matching_score(txt, lib_dict):
    """
    function that rank matching score for associating a string
    to an enum depending on the matching with different keywords associated to that enum. The matching score is the sum
    of the occurences of all keywords. if a keyword is missing it decrease the score by 1.

    Parameters
    ----------
    txt :str
    text to be matched
    lib_dict :dict
    key : enum , value is a list of keyword or tuple of keywords.
    if there is tuple of keyword it match any of the keywords inside the tuple

    Returns
    -------

    """

    def compare_(txt, comp):
        if isinstance(comp, tuple):
            count = np.max([txt.count(x) for x in comp])
        else:
            count = txt.count(comp)

        if count > 0:
            return count
        else:
            return -1

    comp_score_dict = dict()
    for k, v in lib_dict.items():
        comp_score_dict[k] = np.sum([compare_(txt, el) for el in v])

    comp = pd.Series(comp_score_dict).sort_values(ascending=False)
    if comp.max() > 0:
        comp = comp.loc[comp == comp.max()]

        affectation = comp.sort_index().index[0]  # sorting index in case of conflicts
        return affectation
    else:
        return 'non affecte'


def concat_string_cols(table, cols, join_string=None, is_unique=False, is_sorted=False):
    """

    Parameters
    ----------
    table :pd.DataFrame
    cols : list
    list of columns to concatenate
    join_string : str,None
    string to be used as separator for join method when concatenate
    is_unique : bool
    if True will remove duplicated strings to concatenate
    is_sorted : bool
    if True will sort string before concatenate

    Returns
    -------

    """
    if join_string is None:
        join_string = ''

    list_concat = list()

    for col in cols:
        list_concat.append(list(table[col].astype('string').replace('nan', pd.NA).values))

    list_concat = zip(*list_concat)
    t = list(list_concat)

    if is_unique is True and is_sorted is True:
        concat = [join_string.join(sorted(list(set([st for st in el if not pd.isna(st)])))) for el in t]
    elif is_unique is True:
        concat = [join_string.join(list(set([st for st in el if not pd.isna(st)]))) for el in t]
    elif is_sorted is True:
        concat = [join_string.join(sorted([st for st in el if not pd.isna(st)])) for el in t]
    else:
        concat = [join_string.join([st for st in el if not pd.isna(st)]) for el in t]

    s_concat = pd.Series(concat, index=table.index)

    s_concat = s_concat.replace('', pd.NA)

    return s_concat


def merge_without_duplicate_columns(table, other_table, on, merge_kwargs=None):
    if merge_kwargs is None:
        merge_kwargs = {}
    if isinstance(on, (str, int, float)):
        on = [on]
    cols = table.columns
    other_cols = other_table.columns
    other_cols = [col for col in other_cols if col not in cols]  # preserve order
    other_cols = list(other_cols)
    other_cols.extend(list(on))
    table = table.merge(other_table[other_cols], on=on, **merge_kwargs)
    return table


def round_float_cols(table, round=3):
    float_cols = table.dtypes.astype(str).str.contains('float')
    table.loc[:, float_cols] = table.loc[:, float_cols].round(round)
    return table


def unique_ordered(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]
