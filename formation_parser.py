# Script to parse Formation forms tool output files and pass to mstore for storage

# This script to be run as a scheduled task on 1-minute intervals
# Should assume that other processes will be attempting to create files in the Formation target directory
# In practice, demo Formation files will be arriving via FTP to a shared directory structure

# Will use the mstore database library code for database connection, SQL statement execute etc

import sys                                  # System functions, such as command line arguments
import os                                   # OS functions, such as directory scanning
import mstore                               # mstore database functions
import mstoreenvironment as ENV             # mstore environment parameters for this system

MODULE_NAME = 'formation_parser.py'
FORMATION_BASE = ''

def connect_to_mstore():
    server_name = ENV.server_name           # Our SQL-Server instance
    database_name = ENV.database_name       # Our database name
    user_secure = ENV.user_secure           # should be created to match encrypted user name
    pass_secure = ENV.pass_secure           # should be created to match encrypted password
    credentials_p = ENV.credentials_p       # Credentials file to use for authentication
    mddatabase = mstore.MDatabase(server=server_name, database=database_name, user_key=user_secure,
                        password_key=pass_secure, credentials_file=credentials_p)
    return mddatabase

def get_form_type_id(s_form):
    form_id = ''
    form_input = s_form
    while len(form_input) > 0:
        if form_input[len(form_input)-1:len(form_input)].isnumeric():
            form_id = form_input[len(form_input)-1:len(form_input)] + form_id
            form_input = form_input[0:len(form_input)-1]
        else:
            form_input = ''
    return form_id

def get_form_types():
    # read the base directory and get the form types
    form_types = []
    FORMATION_BASE = ENV.FORMATION_BASE
    for d in os.listdir(FORMATION_BASE):
        if os.path.isdir(os.path.join(FORMATION_BASE, d)):
            # found a directory here
            # before we assume that this is going to be a form type, we get the trailing numeric values
            form_type_id = get_form_type_id(d)
            if form_type_id and form_type_id.isnumeric():
                form_types += [[d,form_type_id,(os.path.join(FORMATION_BASE, d))]]
    return form_types

def run_process():
    # run the parsing process
    md = connect_to_mstore()

    # read in the list of form types from the Formation base location
    form_types = get_form_types()


def unit_tests():
    # run the unit test process
    n_pass = 0
    n_fail = 0
    print("\nRunning unit tests for " + MODULE_NAME)

    print("\n" + str(n_pass + n_fail+1) + ": Connect to test server/database - with encrypted credentials")
    try:
        MD = connect_to_mstore()
        print("Created database object with connection string: " + MD.getConnectionString())
        print('Encrypted credentials...')
        print('Test passed')
        n_pass += 1
    except:
        print('Connect to test server failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Get form type ID from string")
    try:
        form_id = get_form_type_id('bobbins-12345')
        if form_id.isnumeric() and int(form_id) == 12345:
            print('Test passed')
            n_pass += 1
        else:
            print('Returned invalid value: ', form_id)
            n_fail += 1
    except:
        print('Get form type Id failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Get form types")
    try:
        form_types = get_form_types()
        print('Read %d form types:' % len(form_types))
        for f in form_types:
            print('Form type %s , id %s, at location: %s' % (f[0],f[1],f[2]))
        print('Test passed')
        n_pass += 1
    except:
        print('Get form types failed...')
        n_fail += 1

    print('\nTotal tests :', n_pass + n_fail)
    print('  %d tests passed' % n_pass)
    print('  %d tests failed' % n_fail)
    print('  %.2f%% success rate\n' % (100.0 * (n_pass / (n_pass + n_fail))))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'TEST':
            print('Running in test mode...')
            # run unit tests
            unit_tests()
    else:
        # run the live program
        run_process()