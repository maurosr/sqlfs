import sqlparse
import subprocess
import sys

from translators import translate


if __name__ == '__main__':
    sql_queries = sys.argv[1]

    print '\nParsing\t\t"{}"'.format(sql_queries)

    stmts = []
    try:
        stmts = sqlparse.parse(sql_queries)
    except Exception as e:
        print 'Error while parsing sql queries "{}": {}'.format(sql_queries, e)
        exit()

    for stmt in stmts:
        print '\nTranslating\t"{}"'.format(stmt)

        shell_cmd = ''
        shell_cmd = translate(stmt)

        print 'Executing\t"{}"\n'.format(shell_cmd)

        ret = subprocess.call(shell_cmd, shell=True)

        if ret != 0:
            print 'Error while executing cmd "{}".'.format(shell_cmd)
            exit()
