import sqlparse.sql
import sqlparse.tokens


CONDITIONS = {'sz': '-size {}{}c',
              'perm': '-perm {}'}
COMPARISON = {'<': '-',
              '=': '',
              '>': '+'}
ATTRS = {'name': '%p',
         'sz': '%s',
         'perm': '%M'}


def _t_select(stmt):
    """
    Translator for SELECT stmt.
    :param stmt: parsed sql statement.
    :return: shell command as a string.
    """
    select_c = stmt.token_next_match(0, sqlparse.tokens.Keyword.DML, 'SELECT')
    select_c_idx = stmt.token_index(select_c)

    attrs = stmt.token_next(select_c_idx)

    if attrs.match(sqlparse.tokens.Wildcard, None):
        action = '-ls'
    else:
        action = "-printf '" + '\\t'.join([ATTRS[a] for a in attrs.value.split(',')]) + "\\n'"

    from_c = stmt.token_next_match(0, sqlparse.tokens.Keyword, 'FROM')
    from_c_idx = stmt.token_index(from_c)
    path = stmt.token_next(from_c_idx).value

    where_c = stmt.token_next_by_instance(0, sqlparse.sql.Where)
    cond = _get_where_cond(where_c) if where_c else []

    tests = ' '.join([oper + ' ' + CONDITIONS[key.lower()].format(COMPARISON[comp], value) for oper, key, comp, value in cond])

    shell_cmd = "find {} {} {}".format(path, tests, action)

    return shell_cmd


def _get_where_cond(where_token):
    """
    Extract the conditions from inside a WHERE token.
    :param where_token: WHERE token.
    :return: list of tuples (operator, left_value, comparison, right_value).
    """
    cond = []
    idx = 0
    compare = where_token.token_next(idx)
    cond.append(('', compare.left.value, compare.tokens[1].value, compare.right.value))

    idx = where_token.token_index(compare)
    op = where_token.token_next(idx)
    while op is not None and op.match(sqlparse.tokens.Keyword, ['AND', 'OR']):
        idx = where_token.token_index(op)
        compare = where_token.token_next(idx)
        cond.append(('-'+op.value.lower(), compare.left.value, compare.tokens[1].value, compare.right.value))

        idx = where_token.token_index(compare)
        op = where_token.token_next(idx)

    return cond


TRANSLATORS = {'SELECT': _t_select}


def translate(stmt):
    """
    Translates an sql statement to a shell command.
    :param stmt: parsed sql statement.
    :return: shell command as a string.
    """
    translator = TRANSLATORS.get(stmt.get_type())

    return translator(stmt)
