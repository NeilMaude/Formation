# Test that pyODBC is available and working
# Neil Maude, 27 June 2018

import pyodbc
import sys

MODULE_NAME = 'test_db.py'
SQL_DRIVER = 'DRIVER={SQL Server Native Client 11.0};'         # database driver to use

def run_check(server, database, user, password):

    s_ConnectionString = SQL_DRIVER + "SERVER=" + server + ";DATABASE=" + database + ";"

    try:
        dbConn = pyodbc.connect(s_ConnectionString + 'UID=' + user + ';PWD=' + password)
        print("Connected OK, test passed...")
    except:
        # failed to connect to the database
        print("Error: failed to connect")
        print("\nUsing connection string:\n", s_ConnectionString)

    return

if __name__ == "__main__":
  if len(sys.argv) < 4:
    print('Usage: python ' + MODULE_NAME + ' Server Database User Password')
    sys.exit(1)
  run_check(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
