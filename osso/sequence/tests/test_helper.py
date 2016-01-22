import warnings

from django import test
from django.db import connection


class TestCase(test.TestCase):
    @property
    def is_ndbcluster(self):
        if not hasattr(self, '_is_ndbcluster'):
            try:
                # Check whether we're using ndbcluster. Because if we are,
                # we cannot use savepoints, even if we wanted to in
                # testcases.
                #   <Svedrin> I'm using Django on an NDB (mysql) cluster.
                #   since I updated to Django 1.4, I get the error: "The
                #   storage engine for the table doesn't support SAVEPOINT"
                #   <Svedrin> is there a config option or something to
                #   disable savepoints?
                # and
                #   https://bugs.launchpad.net/pbxt/+bug/720894
                cursor = connection.cursor()
                cursor.execute('SELECT @@default_storage_engine;')
                data = cursor.fetchall()
                self._is_ndbcluster = (data[0][0] == 'ndbcluster')
                del data
            except:
                self._is_ndbcluster = False
            else:
                if self._is_ndbcluster:
                    # Because we cannot use savepoints *and* mysql
                    # duplicate insert rolls back the transaction,
                    # our test case gets into a zeroed out state.
                    # At that point, there is no use in trying to
                    # continue with the test.
                    #
                    # For normal operations, where autocommit=1, we
                    # have no problems.
                    warnings.warn(
                        "watch out, we skip a few tests because ndbcluster "
                        "rolls back after an integrity error, so we "
                        "we get the worst between MyISAM and InnoDB")

        return self._is_ndbcluster
