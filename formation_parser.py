# Script to parse Formation forms tool output files and pass to mstore for storage

# This script to be run as a scheduled task on 1-minute intervals
# Should assume that other processes will be attempting to create files in the Formation target directory
# In practice, demo Formation files will be arriving via FTP to a shared directory structure

# Will use the mstore database library code for database connection, SQL statement execute etc

import sys                                  # System functions, such as command line arguments
import os                                   # OS functions, such as directory scanning
import shutil                               # additional file copy functions
import stat                                 # needed for CHMOD
import mstore                               # mstore database functions
import mstoreenvironment as ENV             # mstore environment parameters for this system
import json                                 # JSON file parsing library

MODULE_NAME = 'formation_parser.py'
FORMATION_BASE = ''

# connnect to the mstore database
def connect_to_mstore():
    server_name = ENV.server_name           # Our SQL-Server instance
    database_name = ENV.database_name       # Our database name
    user_secure = ENV.user_secure           # should be created to match encrypted user name
    pass_secure = ENV.pass_secure           # should be created to match encrypted password
    credentials_p = ENV.credentials_p       # Credentials file to use for authentication
    mddatabase = mstore.MDatabase(server=server_name, database=database_name, user_key=user_secure,
                        password_key=pass_secure, credentials_file=credentials_p)
    return mddatabase

# helper function - prune a directory tree
# this also removes read-only files, unlike shutil.rmtree()
def prune_directory(sDirectory, fRetainLast=False):
    for root, dirs, files in os.walk(sDirectory, topdown=False):
        for name in files:
            os.chmod(os.path.join(root, name), stat.S_IWRITE)
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    if not fRetainLast:
        os.rmdir(sDirectory)

# helper function - copy a file and optionally delete the source
def copy_file(sSourceFileWithExtension, sTargetFileWithExtension):
    if ENV.DEBUG:
        print('Attempting to copy %s to %s.' % (sSourceFileWithExtension, sTargetFileWithExtension))
    shutil.copy(sSourceFileWithExtension,sTargetFileWithExtension)
    return True

# helper function - check that a directory location exists, create if not
def check_create_dir(sDir):
    try:
        sPath = sDir
        d = os.path.dirname(sPath + '\\')
        if not os.path.exists(d):
            os.mkdir(d)
        return True
    except:
        print(sys.exc_info()[0])
        return False

# get the id value for a form type - assumed trailing numeric values
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

# read the base directory and get the form types
def get_form_types():
    form_types = []
    FORMATION_BASE = ENV.FORMATION_BASE
    for d in os.listdir(FORMATION_BASE):
        if os.path.isdir(os.path.join(FORMATION_BASE, d)):
            # found a directory here
            # before we assume that this is going to be a form type, we get the trailing numeric values
            form_type_id = get_form_type_id(d)
            if form_type_id and form_type_id.isnumeric():
                form_types += [[d,int(form_type_id),(os.path.join(FORMATION_BASE, d))]]
    return form_types

# read the list of forms in a directory
# we need a directory, with one JSON file and one PDF
def get_form_list(s_dir):
    forms_list = []

    for d in os.listdir(s_dir):
        form_path = os.path.join(s_dir, d)
        if os.path.isdir(form_path):
            # this is a directory, so we can check for JSON and PDF files being present
            #print('Found path',form_path)
            f_JSON = ''
            f_PDF = ''
            for f in os.listdir(form_path):
                if f.upper().endswith('.JSON'):
                    # found a JSON file
                    #print('Found JSON file: ',f)
                    f_JSON = f
                if f.upper().endswith('.PDF'):
                    # found a PDF file
                    #print('Found PDF file: ', f)
                    f_PDF = f
            if (f_JSON != '') and (f_PDF != ''):
                forms_list += [[form_path, f_JSON, f_PDF]]
    return forms_list

# get target location for a form
def get_form_target_location(md, nFormId):
    sweep_base = ENV.SWEEP_BASE
    s_out_dir = os.path.join(sweep_base, 'new')
    form_target_list = md.get_MAF_list(ENV.FORM_TARGET_MAF_LIST)
    # First item will be the form Id, the second the path
    for f in form_target_list:
        if f[0] == str(nFormId):
            # have found the form we're interested in
            s_out_dir = os.path.join(sweep_base, f[1])
    return s_out_dir

# get the form data field list
def get_form_field_list(md, nFormId):
    form_field_list = []
    all_field_list = md.get_MAF_list(ENV.FORM_FIELD_MAF_LIST)
    # will be of the form:
    # f[0] = Id (not useful)
    # f[1] = form type Id
    # f[2] = field tag, pipe delimited
    # f[3] = target field name
    for f in all_field_list:
        if f[1] == str(nFormId):
            # correct form
            form_field_list += [[f[2],f[3]]]
    return form_field_list

# extract fields from a JSON file
def get_values(s_JSON, field_list):
    # s_JSON = full path to JSON file to import
    # field_list = fields to extract, tuple of (tag, target field) - note that the tag may be a pipe-delimited list
    # returns a list of tuples of (value, target_field)
    values = []
    try:
        with open(s_JSON) as f:
            data = json.load(f)
        #print(s_JSON,data)
        for f in field_list:
            #print('Tag: %s' % f[0])
            h =  f[0].split('|')
            #print('Split :', h)
            d = data
            for ref in h[0:len(h) - 1]:
                d = d[ref]
                #print(d)
            val = d[h[len(h)-1]]
            values += [[val, f[1]]]
        return values
    except:
        # swallow the error and pass up an empty list of values - this will cause the form to be ignored
        # we want to carry on with other forms, even if the JSON config is wrong...
        return []

# write fields to SQL database, return the unique file name to use
def write_fields(md, values, s_original_path, s_form_ref='unknown', s_form_id='unknown'):
    # md will be an mstore database object
    # values will be a list of tuples (value, field)
    #print('Hello!')
    sSQL = 'insert into ' + ENV.FORMATION_DATA_TABLE
    sFields = 'originalpath, formtype, formref'
    sValues = md.quote_string(s_original_path)
    sValues += ',' + md.quote_string(s_form_ref)
    sValues += ',' + md.quote_string(s_form_id)
    #print(sSQL)
    for fv in values:
        sFields += ',' + fv[1]
        sValues += ',' + md.quote_string(fv[0])
    sSQL += '(' + sFields + ') values (' + sValues + ')'
    try:
        md.execute(sSQL)
        sSQL = 'select max(ID) [NewID] from ' + ENV.FORMATION_DATA_TABLE
        #print(sSQL)
        rs = md.getRecordSet(sSQL)
        #print(rs[0])
        new_id = rs[0].NewID
        return new_id
    except:
        return -1

def run_process():
    # run the parsing process
    md = connect_to_mstore()

    if not check_create_dir(ENV.SWEEP_BASE): return            # check that this directory exists, end otherwise

    # read in the list of form types from the Formation base location
    form_types = get_form_types()

    # for each form type
    for f_type in form_types:

        # f_type is tuple of (full name, Id, path to forms)

        # load in the mstore configuration, if any - done once, so we have it for all forms of this type
        nFormId = f_type[1]
        s_output_location = get_form_target_location(md, nFormId)
        field_list = get_form_field_list(md, nFormId)

        # get the list of forms - must be complete with JSON data and a PDF
        form_list = get_form_list(f_type[2])

        # for each form
        for form in form_list:

            # first thing is to check that the output directory is OK for this form type
            if check_create_dir(s_output_location):

                # form is tuple of (folder, JSON file, PDF file) - files don't have a path appended
                s_JSON_file = os.path.join(form[0],form[1])
                s_PDF_file = os.path.join(form[0],form[2])
                #print(s_JSON_file,s_PDF_file)

                # load the JSON and get the values
                values = get_values(s_JSON_file,field_list)

                # if there are no values, still process this file - likely a new form
                # write the JSON data to mstore and get a unique Id - this will be the unique file Id
                new_id = write_fields(md, values, s_PDF_file, str(nFormId), get_form_type_id(form[0]))

                s_output_PDF = str(new_id) + '.pdf'
                s_output_PDF = os.path.join(s_output_location, s_output_PDF)

                # copy the PDF to the Sweep location for this form type
                if copy_file(s_PDF_file, s_output_PDF):
                    # clean out the files for this form - remove the files, remove the directory
                    if ENV.DEBUG == False:
                        prune_directory(form[0])
                    else:
                        print('\n** In DEBUG mode, no files removed! **')
                        print('Be careful of filling up your disk drives!')


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

    print("\n" + str(n_pass + n_fail+1) + ": Get form output location")
    try:
        form_id = 12763
        form_out = get_form_target_location(MD, form_id)
        print('Directory set as %s for %d' % (form_out,form_id))
        n_pass += 1
    except:
        print('Get form output location failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Get fields for the form")
    try:
        form_id = 12763
        field_list = get_form_field_list(MD, form_id)
        print('Fields found for %d:' % form_id)
        for f in field_list:
            print('Tag %s, target %s' % (f[0],f[1]))
        n_pass += 1
    except:
        print('Get form output location failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Get forms for a form type")
    try:
        form_type_dir = 'D:\Git\Python\Formation\FTP\BMW approved used car check-12763'
        forms = get_form_list(form_type_dir)
        print('Forms found for %s: (%d)' % (form_type_dir, len(forms)))
        for f in forms:
            print('Form in: %s, JSON file: %s, PDF file: %s' % (f[0] ,f[1], f[2]))
        n_pass += 1
    except:
        print('Get forms for type failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Get values for a form")
    try:
        form_JSON = 'D:\Git\Python\Formation\FTP\BMW approved used car check-12763\Form-99889\BMW approved used car check.json'
        field_list = [['8','CB_CREF1'],['31|31[Issue_2_Fault_description]','CB_DREF7']]
        values = get_values(form_JSON, field_list)
        print('Values found for %s: (%d)' % (form_JSON, len(values)))
        for f in values:
            print('Value: %s, for field: %s' % (f[0] ,f[1]))
        n_pass += 1
    except:
        print('Get value from form failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Write values for a form")
    try:
        value_list = [['AB12CDE','CB_CREF1'],['Some fault name','CB_DREF7']]
        s_original_path = 'D:\Some-Test-Path'
        #print(value_list)
        new_id = write_fields(MD, value_list, s_original_path)
        print('Values written and Id returned: %d' % new_id)
        n_pass += 1
    except:
        print('Write values failed...')
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