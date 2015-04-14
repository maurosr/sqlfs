import sqlparse.sql
import sqlparse.tokens


CONDITIONS = {'sz': '-size {}{}c',  # in bytes
              'perm': '-perm {}{}',
              'name': '-name {}{}',
              'u': '-user {}{}',
              'g': '-group {}{}',
              'modified': '-mtime {}{}'  # in days
              }
COMPARISON = {'<': '-',
              '=': '',
              '>': '+'}
ATTRS = {'sz': '%s',
         'perm': '%M',
         'name': '%p',
         'u': '%u',
         'g': '%g',
         'modified': '%Tc',
         'sum': '$S'
         }

PRECMD = {'sum': "S=$( (find {} -maxdepth 1 -printf s+=%s\\\\n; echo s) | bc)"}


def _get_conditions(stmt):
    where_c = stmt.token_next_by_instance(0, sqlparse.sql.Where)
    cond = _get_where_cond(where_c) if where_c else []
    return ' '.join([oper + ' ' + CONDITIONS[key.lower()].format(COMPARISON[comp], value)
                     for oper, key, comp, value in cond])


def _get_options(stmt):
    recursive = stmt.token_next_match(0, sqlparse.tokens.Keyword, 'RECURSIVE')

    options = ''
    if not recursive:
        options += ' -maxdepth 1'

    return options


def _get_path(stmt, keyword="FROM"):
    from_c = stmt.token_next_match(0, sqlparse.tokens.Keyword, keyword)
    from_c_idx = stmt.token_index(from_c)
    return stmt.token_next(from_c_idx).value


def _t_select(stmt):
    """
    Translator for SELECT stmt.
    :param stmt: parsed sql statement.
    :return: shell command as a string.
    """
    select_c = stmt.token_next_match(0, sqlparse.tokens.Keyword.DML, 'SELECT')
    select_c_idx = stmt.token_index(select_c)

    path = _get_path(stmt)

    attrs = stmt.token_next(select_c_idx)

    pre_cmd = ''
    if attrs.match(sqlparse.tokens.Wildcard, None):
        action = '-ls'
    else:
        # allow spaces between attributes
        attrs = [a.strip().split('(')[0].lower() for a in attrs.value.split(',')]

        if 'sum' in attrs:
            pre_cmd = PRECMD['sum'].format(path) + '; '

        action = "-printf " + '\\\\t'.join([ATTRS[a] for a in attrs]) + "\\\\n"

    options = _get_options(stmt)
    tests = _get_conditions(stmt)

    shell_cmd = pre_cmd + "find {} {} {} {}".format(path, options, tests, action)

    return shell_cmd


def _t_delete(stmt):
    """
    Translator for DELETE stmt.
    :param stmt: parsed sql statement.
    :return: shell command as a string.
    """
    action = '-delete'

    path = _get_path(stmt)
    options = _get_options(stmt)
    tests = _get_conditions(stmt)

    shell_cmd = "find {} {} {} {}".format(path, options, tests, action)
    return shell_cmd


def _t_insert(stmt):
    """
    Translator for INSERT stmt.
    :param stmt: parsed sql statement.
    :return: shell command as a string.
    """
    path2 = _get_path(stmt, "INTO")
    action = "-exec cp '{}' " + path2 + " \;"

    path1 = _get_path(stmt)
    options = _get_options(stmt)
    tests = _get_conditions(stmt)

    shell_cmd = "find {} {} {} {}".format(path1, options, tests, action)
    return shell_cmd


def _get_where_cond(where_token):
    """
    Extract the conditions from inside a WHERE token.
    :param where_token: WHERE token.
    :return: list of tuples (operator, left_value, comparison, right_value).
    """
    cond = []
    idx = 0

    op = None
    while idx == 0 or (op is not None and op.match(sqlparse.tokens.Keyword, ['AND', 'OR'])):
        compare = where_token.token_next(idx)

        # allow spaces between operators
        token_compare = [t for t in compare.tokens[1:-1] if t.value.strip() != ""]
        cond.append(('', compare.left.value, token_compare[0].value, compare.right.value))

        # find new compare
        idx = where_token.token_index(compare)
        op = where_token.token_next(idx)
        idx = where_token.token_index(op)

    return cond


TRANSLATORS = {'SELECT': _t_select,
               'DELETE': _t_delete,
               'INSERT': _t_insert}


def translate(stmt):
    """
    Translates an sql statement to a shell command.
    :param stmt: parsed sql statement.
    :return: shell command as a string.
    """
    translator = TRANSLATORS.get(stmt.get_type())

    return translator(stmt)
