# Python helper functions for mstore
# Neil Maude
# 29-Jan-2018
# Will hold database class for accessing mstore, along with sundry helper functions
# Will have minimum dependencies
# Will *not* have dependencies on Tensorflow, Keras, Sci-Kit Learn, Numpy and similar libraries

# Required libraries
import pyodbc               # pyodbc - for SQL connectivity
import pickle               # for saving/loading objects and data
import re                   # regular expressions library, for pattern matching

# Other Arena code
import mstoresecurity                   # encryption tools for user/password
import mstoreenvironment as ENV         # Environmental variables for mstore - includes unit test params

# Module constants
MODULE_NAME = 'mstore.py'
s_SQL_DRIVER = 'DRIVER={SQL Server Native Client 11.0};'         # database driver to use

# Wider mstore constants
MSTORE_OCR_STATUS_NEW = 0               # MRContentsX record will have MT_Status == 0 when page is new
MSTORE_OCR_STATUS_SUCCESS = 1           # Success
MSTORE_OCR_STATUS_FAILED = 2            # Failed
MSTORE_OCR_STATUS_COMPLETE = 3          # This is the usual case for complete OCR - "post process" successful
                                        # Note that codes > 3 exist, but are not expected within auto-indexing
                                        # E.g. Mailroom applied, barcode indexing applied...

# class for mstore database actions
class MDatabase:

    s_ConnectionString = ''
    dbConn = ''
    dbConnected = False
    s_LastError = ''
    s_User = ''
    s_Password = ''

    # constructor
    def __init__(self, server, database, user_key, password_key, encrypted=True, credentials_file='', autoconnect = True):

        fExit = False

        # deal with encryption/decryption of user and password
        if encrypted:
            # decrypt first
            decrypt_success, decrypt_name, decrypt_password = mstoresecurity.get_account_details(user_key,
                                                                            password_key,
                                                                            credentials_file)
            if decrypt_success:
                self.s_User = decrypt_name
                self.s_Password = decrypt_password
            else:
                fExit = True
                self.s_LastError = 'Failed to descrypt credentials'
        else:
            self.s_User = user_key
            self.s_Password = password_key

        if not fExit:
            # build the connection string
            self.s_ConnectionString = s_SQL_DRIVER + "SERVER=" + server + ";DATABASE=" + database +";"

            if autoconnect:
                try:
                    self.dbConn = pyodbc.connect(self.s_ConnectionString + 'UID=' + self.s_User + ';PWD=' + self.s_Password)
                    self.dbConnected = True
                except:
                    # failed to connect to the database
                    self.s_LastError = "Error: failed to connect"

    # trivially return the connection, for testing purposes
    def getConnectionString(self):
        return self.s_ConnectionString

    # allow checking if the database object is connected
    def isConnected(self):
        return self.dbConnected

    # return the connection itself (pyodbc object) in case the user wants to get off and walk
    # may well want to remove this if this module is to be used outside of the Arena development team
    def getConnection(self):
        return self.dbConn

    # return the last error
    def getLastError(self):
        return self.s_LastError

    # Just stick quotes around the string, for SQL building
    def quote_string(self, sString):
        if sString.find("'") < 0:
            return "'%s'" % sString
        else:
            return "'%s'" % sString.replace("'", "#")

    # Execute arbitrary SQL on connection - default to immediate commit
    def execute(self, sSQL, commit=True):
        if self.dbConnected:
            curData = self.dbConn.cursor()
            try:
                curData.execute(sSQL)
                if commit:
                    curData.commit()            # take care - this is the same as self.dbConn.commit()
                                                # I.e. commits all pending actions on this connection object!
                return True
            except:
                return False
        else:
            return False

    # get a recordset
    def getRecordSet(self, sSQL):
        if self.dbConnected:
            curData = self.dbConn.cursor()
            curData.execute(sSQL)
            rsData = curData.fetchall()         # this gets all records into the list, performance on large result sets?
            return rsData
        else:
            self.s_LastError = 'Recordset requested, but not connected to database'
            return []

    # the following functions are used in page classification actions

    # get the page count for a document
    def get_document_page_count(self, sCabinet, nDocID):
        sSQL = 'select CB_PAGES from MICAB' + sCabinet + ' where CB_DOCID = ' + str(nDocID)
        rsPage = self.getRecordSet(sSQL)
        if len(rsPage) > 0:
            return rsPage[0].CB_PAGES
        else:
            self.s_LastError = 'Finding page count for ' + sCabinet + '/' + str(nDocID) + ' (no record)'
            return -1                   # document found

    # get the page contents, for a given document/page
    def get_page_contents(self, sCabinet, nDocID, nPage):
        # get the MRContentsXX record for this page of the requested document
        sSQL = 'select MT_Contents from MRContents' + sCabinet + ' where MT_DocId=' + str(nDocID) \
               + ' and MT_Page=' + str(nPage)
        rsPage = self.getRecordSet(sSQL)
        return rsPage[0].MT_Contents

    # get document OCR status
    def get_document_OCR_status(self, sCabinet, nDocID):
        nPages = self.get_document_page_count(sCabinet, nDocID)
        # check if all pages have OCR complete
        sSQL = 'select count(*) [Complete] from MRContents' + sCabinet + ' where MT_DocId=' + str(nDocID) \
               + ' and (MT_Status=' + str(MSTORE_OCR_STATUS_COMPLETE) \
               + ' or MT_Status=' + str(MSTORE_OCR_STATUS_SUCCESS) + ')'
        rsComplete = self.getRecordSet(sSQL)
        nRemaining = rsComplete[0].Complete
        # check for any error pages
        sSQL = 'select count(*) [Error] from MRContents' + sCabinet + ' where MT_DocId=' + str(nDocID) \
               + ' and MT_Status<>' + str(MSTORE_OCR_STATUS_COMPLETE) \
               + ' and MT_Status<>' + str(MSTORE_OCR_STATUS_SUCCESS) \
               + ' and MT_Status<>' + str(MSTORE_OCR_STATUS_NEW)
        rsError = self.getRecordSet(sSQL)
        nError = rsError[0].Error
        # return values are:
        #   0 if all pages OCR'd
        #   >1 if pages await OCR (number of pages)
        #   -1 for error pages - document will need to go down an error route
        if nError > 0:
            return -1
        else:
            return nPages - nRemaining

    # get MAF list contents
    def get_MAF_list(self, nMAFListID):
        # read in a MAF list and return the database cursor
        rsMAF = self.getRecordSet('select LS_Item1, LS_Item2, LS_Item3, LS_Item4, LS_Item5,' \
                                         'LS_Item6, LS_Item7, LS_Item8, LS_Item9, LS_Item10 ' \
                                         'from AFListItem where LS_ListID = ' + str(nMAFListID))
        return rsMAF

    # get the list of available training documents for a given document type
    # REFACTOR - this should be in the classifier module
    def get_training_doc_list(self, sCabinet, nDTID, fOrderAscending=True, max_records=0):
        sCabinetName = 'MICAB' + str(sCabinet)
        sContentsName = 'MRContents' + str(sCabinet)
        if max_records > 0:
            sSQL = 'select top ' + str(max_records) + ' '
        else:
            sSQL = 'select '
        sSQL = sSQL + 'CB_DOCID, CB_PAGES, CB_FILETYPE from ' + '(' \
               + sCabinetName + ' Left Join MIVersions on CB_DOCID = DV_DocumentId) ' \
               + 'Left Join AIExcludedDocuments on CB_DOCID = EX_DocId ' \
               + 'where ' \
               + 'IsNull(DV_Unique, -1) = -1 and ' \
               + 'IsNull(EX_DocId, -1) = -1 and ' \
               + 'CB_PAGES = (select count(*) from ' + sContentsName + ' where MT_DocId = CB_DOCID and MT_Status = 3) ' \
               + 'and CB_DTID = ' + str(nDTID)
        if fOrderAscending:
            sSQL += ' order by CB_DOCID ASC'
        else:
            sSQL += ' order by CB_DOCID DESC'
        rsDocs = self.getRecordSet(sSQL)
        return rsDocs

class MAutoIndex:

    md_database = None      # Will hold an mstore database connection object

    def __init__(self, mDatabase):
        self.set_database(mDatabase)

    # set and get the database object
    def set_database(self, mDatabase):
        if isinstance(mDatabase, MDatabase):
            if mDatabase.isConnected():
                self.md_database = mDatabase
            else:
                raise ValueError('set_database requires MDatabase to be connected')
        else:
            raise ValueError('set_database requires a MDatabase object')
    def get_database(self):
        return self.md_database

    # write an event to the AILog table
    def write_log_event(self, nJobID, sDescription, sSource='', sCabinetID='', nDocID=0):
        # note that the source, cabinet and docId are optional values

        sTmpSQL = 'insert into AILog (' \
                    + 'AL_JobID, AL_Source, AL_Description, AL_CabinetID, AL_DocID' \
                    + ') values (' \
                    + str(nJobID) + ', ' \
                    + self.md_database.quote_string(sSource) + ', ' \
                    + self.md_database.quote_string(sDescription) + ', ' \
                    + self.md_database.quote_string(sCabinetID) + ', ' \
                    + str(nDocID) \
                    + ')'
        self.md_database.execute(sTmpSQL)

    # check for a record in AIJobs for this JobId and create one if not there
    def check_create_job_record(self, nJobID):

        sTmpSQL = 'select count(*) RecCount from AIJobs where AJ_JobId = ' + str(nJobID)
        rs = self.md_database.getRecordSet(sTmpSQL)
        if rs[0].RecCount <= 0:
            # No record in AIJobs - create one..
            sTmpSQL = 'insert into AIJobs (AJ_JobID) Values (' + str(nJobID) + ')'
            result = self.md_database.execute(sTmpSQL)
            if not result:
                self.write_log_event(nJobID,'Failed to create AIJobs record','check_create_job_record')
                raise('Could not create AIJobs record')
            else:
                self.write_log_event(nJobID, 'Created AIJobs record for new document','check_create_job_record')

    # Set the OCR status for a job, in the case of complete or an error
    def set_job_OCR_status(self, nJobID, sCabinetID, nDocID):
        # get the status
        nStatus = self.md_database.get_document_OCR_status(sCabinetID, nDocID)
        # write the status to the database, if there is an update
        sTmpSQL = ''
        if nStatus == 0:
            # All pages are complete, no errors
            sTmpSQL = 'update AIJobs set AJ_OCRComplete = 1 where AJ_JobID = ' + str(nJobID)
            self.write_log_event(nJobID, 'OCR complete for all pages', 'set_job_OCR_status', sCabinetID, nDocID)
        else:
            if nStatus < 0:
                # permanent error case, set the error field
                sTmpSQL = 'update AIJobs set AJ_OCRComplete = 0, AJ_OCRError = 1 where AJ_JobID = ' + str(nJobID)
                self.write_log_event(nJobID, 'Permanent error in OCR process', 'set_job_OCR_status', sCabinetID, nDocID)
        if sTmpSQL != '':
            result = self.md_database.execute(sTmpSQL)
            if not result:
                raise ('Could not update AIJobs record')

    # internal helper function - get the rules for a fixed text classifier, from a MAF list
    def get_fixed_text_classifier_rules(self, nMAFListID):
        # read in the list, parse the values into a list of tuples
        # note that we are doing this by grabbing an in-memory copy of a MAF list
        # should be fine with regard to size, but possible that really huge systems could get slow...

        # The MAF list is expected to be formed as:
        #   LS_Item1 - just a unique ID to meet the MAF list database constraint
        #   LS_Item2 - the DTID for this rule
        #   LS_Item3 - the Regular Expression for searching

        rules = []
        rsMAF = self.md_database.get_MAF_list(nMAFListID)
        for r in rsMAF:
            rules += [(r.LS_Item2, r.LS_Item3)]
        return rules

    # function to run a fixed text classification, returns the DTID for the doc (if uniquely matched)
    def fixed_text_classifier(self, nJobID, sCabinetID, nDocID, nRulesList=0):
        # takes in the job/cabinet/docid
        # takes an optional rules list parameter - this is the ID of a MAF list to use for the rules
        # if no rules list is provided, will use the default from the environment parameters
        # we would only use an alternative to implement multiple fixed text classifiers in the future
        # returns:
        #   in the case of a unique match, the DTID value
        #   in the case of no match, 0
        #   in the case of a multiple match, -1

        # Note that the page content is converted to UPPER CASE for processing, but the RegEx values are not
        # Therefore fixed text values in the RegEx should be set up as upper text in the parameters / MAF list

        nTargetDTID = 0
        fUnique     = True
        nDocPages   = 0

        # load the rules - will be a list of tuples of (DTID, RegEx)
        # [(1, 'Purchase Invoice'), (2, 'Some other document type marker text)]
        if nRulesList == 0:
            nMAFList = ENV.MAF_ListID_FixedTextClassifier
        else:
            nMAFList = nRulesList
        rules = self.get_fixed_text_classifier_rules(nMAFList)

        # load the page count for this document
        nDocPages = self.md_database.get_document_page_count(sCabinetID, nDocID)

        # loop over pages
        for nPage in range(1,nDocPages+1):
            # load the page text
            page = self.md_database.get_page_contents(sCabinetID, nDocID, nPage)
            # clean out any unicode chars in the page text
            page = re.sub(r'[^\x00-\x7f]', r'', page)

            # CAUTION - reversed the decision to work only in upper case...
            # we are going to work only in upper case
            #page = page.upper()

            # loop over rules
            for r in rules:
                regex = r[1]
                matches = re.findall(regex, page)
                # update DTID if we have a match, update the unique flag if multiple DTID matches
                if matches:
                    # have at least one match to this expression
                    if (nTargetDTID == 0) or (r[0] == nTargetDTID):
                        # either first match or same DTID
                        nTargetDTID = r[0]
                    elif (nTargetDTID != 0) and (r[0] != nTargetDTID):
                        # match, but not the same DTID as previous matches
                        fUnique = False

        # have now tested all rules over all pages - can return the DTID, if any...
        if fUnique:
            # either a unique match or no match
            if nTargetDTID != 0:
                self.write_log_event(nJobID, 'Fixed text classifier match = ' + str(nTargetDTID), 'fixed_text_classifier',
                                     sCabinetID, nDocID)
            else:
                self.write_log_event(nJobID, 'No match in fixed text classifier', 'fixed_text_classifier',
                                     sCabinetID, nDocID)
            return nTargetDTID
        else:
            #non-unique match to rules
            self.write_log_event(nJobID, 'Multiple document type matches in fixed text classifier',
                                 'fixed_text_classifier', sCabinetID, nDocID)
            return -1

    # update the classification status
    def update_job_classification(self, nJobID, nTargetID, fFound):
        sTmpSQL = ''
        if fFound == False:
            sTmpSQL = 'update AIJobs set AJ_ClassFound = 0, AJ_TargetDTID = 0 where AJ_JobID = ' + str(nJobID)
        else:
            sTmpSQL = 'update AIJobs set AJ_ClassFound = 1, AJ_TargetDTID = ' + str(nTargetID) \
                        + ' where AJ_JobID = ' + str(nJobID)
        self.md_database.execute(sTmpSQL)

    # Run the fixed text classification process
    # This is the externally callable function, for use in workflow scripts
    def run_fixed_text_classifier(self, nJobID, sCabinetID, nDocID, nRulesList=0):
        self.write_log_event(nJobID, 'Running fixed text classifier', 'run_fixed_text_classifier', sCabinetID, nDocID)
        nTargetDTID = self.fixed_text_classifier(nJobID, sCabinetID, nDocID, nRulesList)
        if int(nTargetDTID) >= 1:
            # successful classification
            self.update_job_classification(nJobID,nTargetDTID, True)
        else:
            # did not classify at this stage
            self.update_job_classification(nJobID, 0, False)

    # Get the target DTID for a job where the document has been identified already
    def get_targetDTID_for_classified_doc(self, nJobID):
        # read from AIJobs
        sTmpSQL = 'select AJ_TargetDTID, AJ_ClassFound from AIJobs where AJ_JobID = ' + str(nJobID)
        rsDTID = self.md_database.getRecordSet(sTmpSQL)
        if len(rsDTID) > 0:
            # we have a record
            if rsDTID[0].AJ_ClassFound == 1:
                return rsDTID[0].AJ_TargetDTID
            else:
                # class not found
                self.write_log_event(nJobID, 'Attempt to read class for unclassified job', 'get_targetDTID_for_classified_doc')
                return -1
        else:
            # empty recordset
            self.write_log_event(nJobID, 'Attempt to read target DTID for job with no AIJobs record!', 'get_targetDTID_for_classified_doc')
            return -1

    # internal helper function - get the rules for reference lookup, from a MAF list
    def get_ref_lookup_rules(self, nMAFListID):
        # read in the list, parse the values into a list of tuples
        # note that we are doing this by grabbing an in-memory copy of a MAF list
        # should be fine with regard to size, but possible that really huge systems could get slow...

        # The MAF list is expected to be formed as:
        #   LS_Item1 - a unique ID to meet the MAF list database constraint
        #   LS_Item2 - the DTID for this rule
        #   LS_Item3 - the Regular Expression for searching
        #   LS_Item4 - the validation table name
        #   LS_Item5 - the master column in the validation table
        #   LS_Item6-10 - the cross reference fields in the validation table

        rules = []
        rsMAF = self.md_database.get_MAF_list(nMAFListID)
        for r in rsMAF:
            # create a list of lookup fields - this is useful for later, as deals with NULLs
            lookup_fields = []
            for i in range(5,10):
                if len(str(r[i]).strip()) > 0:
                    # have a usable lookup field
                    lookup_fields += [str(r[i]).strip()]
            rules += [(r.LS_Item1, r.LS_Item2, r.LS_Item3, r.LS_Item4, r.LS_Item5, lookup_fields)]
        return rules

    # internal helper function - get the values for cross-checking of a candidate reference value
    def get_cross_ref_values(self, sLookupTable, sLookupColumn, sLookupValue, lCrossRefCols):
        #print(lCrossRefCols)
        cr_values = []
        for c in lCrossRefCols:
            sTmpSQL = 'select top 1 ' + c + ' as cr_value from ' + sLookupTable
            sTmpSQL += ' where ' + sLookupColumn + ' = ' + self.md_database.quote_string(sLookupValue)
            rsCR = self.md_database.getRecordSet(sTmpSQL)
            # Check if empty or None (NULL)
            if (len(str(rsCR[0].cr_value)) > 0) and (rsCR[0].cr_value != None):
                cr_values += [rsCR[0].cr_value]
        return cr_values

    # update the reference capture status
    def update_reference_status(self, nJobID, sRefValue, fFound):
        sTmpSQL = ''
        if fFound == False:
            sTmpSQL = 'update AIJobs set AJ_KeyRefFound = 0 where AJ_JobID = ' + str(nJobID)
        else:
            sTmpSQL = 'update AIJobs set AJ_KeyRefFound = 1, AJ_KeyRefValue = '
            sTmpSQL += self.md_database.quote_string(sRefValue)
            sTmpSQL += ' where AJ_JobID = ' + str(nJobID)
        self.md_database.execute(sTmpSQL)

    # Run the reference extract process, with validation
    # This is the externally callable function, for us in workflow scripts
    def run_reference_extract(self, nJobID, sCabinetID, nDocID, nRefRulesList=0):
        # This function will loop over all of the possible rules for the particular document
        # If the data is captured and validated, the captured references table will be updated
        # Finally, the AIJobs table will be updated to signal that reference extract was successful or not

        # Get the target DTID
        nTargetDTID = self.get_targetDTID_for_classified_doc(nJobID)
        if int(nTargetDTID) > 0:

            # Load in the reference rules for this DTID

            # load the rules - will be a list of tuples of:
            #    (RuleID, DTID, RegEx, Validation Table, Master Field Name,
            #       [Cross Ref Field1, 2, 3, 4, 5])
            # Not all 5 cross ref fields may be used
            # The RuleID is included for logging purposes

            if nRefRulesList == 0:
                nMAFList = ENV.MAF_ListID_ReferenceExtractDefinitions
            else:
                nMAFList = nRefRulesList
            ref_rules = self.get_ref_lookup_rules(nMAFList)

            # list to retain validated matches
            # Will be a list of tuples:
            #   [(RuleId, Ref Value, Cross-Ref Value, Page Found)]
            validated_matches = []

            # Loop over the reference rules
            for rule in ref_rules:

                # Loop over the document pages
                nDocPages = self.md_database.get_document_page_count(sCabinetID, nDocID)

                for nPage in range(1, nDocPages + 1):
                    # load the page text
                    page = self.md_database.get_page_contents(sCabinetID, nDocID, nPage)
                    # clean out any unicode chars in the page text
                    page = re.sub(r'[^\x00-\x7f]', r'', page)

                    # Find regex matches - may be multiples
                    regex = rule[2]                         # 3rd value in rule tuple is the actual regex
                    matches = re.findall(regex, page)

                    #print(matches)

                    # Loop over matches
                    if len(matches) > 0:

                        for match in matches:

                            #print(match)

                            # Load in the potential cross-reference values for this match
                            cross_check_values = self.get_cross_ref_values(rule[3], rule[4], match, rule[5])

                            #print(cross_check_values)

                            # Loop over the document pages
                            for nCheckPage in range(1, nDocPages + 1):

                                # load the page
                                check_page = self.md_database.get_page_contents(sCabinetID, nDocID, nCheckPage)

                                for cv in cross_check_values:

                                    #print (cv)

                                    # do we have this value in the text?
                                    check_matches = re.findall(cv, check_page)

                                    #print('Check matches: ', check_matches)

                                    # Record if validated
                                    if len(check_matches) > 0:

                                        validated_matches += [(rule[0], match, cv, nPage)]

            #print(validated_matches)

            # check if we have duplicated matches for the same reference value only
            # it is OK to match the same reference multiple times
            # it is not OK to match to multiple references, as we won't know how to index the document
            sFirstMatch = ''
            fUniqueMatch = False
            for m in validated_matches:
                if sFirstMatch == '':
                    sFirstMatch = m[1]
                    fUniqueMatch = True
                else:
                    if m[1] != sFirstMatch:
                        fUniqueMatch = False

            #print(fUniqueMatch, len(validated_matches))

            if len(validated_matches) > 0:
                # we have some matched items
                if fUniqueMatch:
                    # unique match found
                    sMessage = 'Unique reference match found for rule #' + str(validated_matches[0][0])
                    sMessage += ', value = ' + self.md_database.quote_string(validated_matches[0][1])
                    sMessage += ', with ' + str(len(validated_matches)) + ' total matches'
                    self.write_log_event(nJobID, sMessage, 'run_reference_extract', sCabinetID, nDocID)
                    # update database to indicate new status
                    self.update_reference_status(nJobID, validated_matches[0][1], True)
                else:
                    # not a unique match
                    sMessage = 'Multiple reference matches found'
                    sMessage += ', ' + str(len(validated_matches)) + ' total matches, for rules: '
                    for v in validated_matches:
                        sMessage += str(v[0]) + ' '
                    self.write_log_event(nJobID, sMessage, 'run_reference_extract', sCabinetID, nDocID)
                    # update database to indicate new status
                    self.update_reference_status(nJobID, '', False)
            else:
                # no matches
                self.write_log_event(nJobID, 'No reference matches found for target DTID = ' + str(nTargetDTID),
                                     'run_reference_extract', sCabinetID, nDocID)
                # update the database to reflect the new status for this document
                self.update_reference_status(nJobID, '', False)

        else:
            # failed to get target DTID
            self.write_log_event(nJobID, 'Cannot process references - job not classified','run_reference_extract')
            # just update the status - this will avoid jobs being locked in workflow
            self.update_reference_status(nJobID, '', False)

def unit_test():
    # Run unit tests for this module
    # Will require an mstore system to test against, which will require some standard setup (user, password etc)
    # So this will not run in an arbitrary environment

    # The following environment must be correctly configured in advance for tests to run

    user_plain = ENV.user_plain
    pass_plain = ENV.pass_plain
    user_secure = ENV.user_secure           # should be created to match encrypted user name
    pass_secure = ENV.pass_secure           # should be created to match encrypted password
    credentials_p = ENV.credentials_p       # must exist - 'main' part is to avoid over-write by security unit tests
    server_name = ENV.server_name           # test SQL-Server instance
    database_name = ENV.database_name       # test database

    # (End of specific params...)

    n_pass = 0
    n_fail = 0
    print("\nRunning unit tests for " + MODULE_NAME)
    print("\n" + str(n_pass + n_fail+1) + ": Connect to test server/database - unencrypted credentials")
    print('\nServer: ', server_name)
    print('Database: ', database_name)

    try:
        MD = MDatabase(server = server_name, database = database_name, user_key=user_plain,
                       password_key=pass_plain, encrypted=False)
        print("Created database object with connection string: " + MD.getConnectionString())
        print('Unencrypted credentials...')
        print('Test passed')
        n_pass += 1
    except:
        print('Connect to test server failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Connect to test server/database - with encrypted credentials")
    try:
        MD = MDatabase(server=server_name, database=database_name, user_key=user_secure, password_key=pass_secure,
                       credentials_file=credentials_p)
        print("Created database object with connection string: " + MD.getConnectionString())
        print('Encrypted credentials...')
        print('Test passed')
        n_pass += 1
    except:
        print('Connect to test server failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Test quote_string function")
    try:
        sInput = 'This is a test string'
        print('Input: ', sInput)
        quoted = MD.quote_string(sInput)
        print('Quoted: ', quoted)
        sInput = "Test string with 'quote' included"
        print('Input: ', sInput)
        quoted = MD.quote_string(sInput)
        print('Quoted: ', quoted)
        print('Complete testing of quote_string')
        print('Test passed')
        n_pass += 1
    except:
        print('Test of quote_string failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Create MAutoIndex object and set database")
    try:
        AI = MAutoIndex(MD)
        print('Created MAutoIndex object using database from encrypted credentials')
        print('Test passed')
        n_pass += 1
    except:
        print('Create of MAutoIndex object failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Read some records")
    sTmpSQL = 'select count(*) RecCount from MICABDEF'
    try:
        rs = MD.getRecordSet(sTmpSQL)
        print('Read ' + str(rs[0].RecCount) + ' records...')
        print('Test passed')
        n_pass += 1
    except:
        print('Failed to read records... ', sTmpSQL)
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Write an AILog entry")
    try:
        AI.write_log_event(-1, 'Test log record', 'Unit test process', 'A', -2)
        print('Wrote test log record')
        print('Test passed')
        n_pass += 1
    except:
        print('Write out of AILog test record failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Check/create of AIJob record")
    try:
        AI.check_create_job_record(-1)
        print('Completed check/create of AIJob record for JobID -1')
        print('Test passed')
        n_pass += 1
    except:
        print('Check/create of AIJob record failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail+1) + ": Count document pages")
    # Will need some meaningful cabinet/docId combination within the test system
    sCabinet = '1'
    nDocID = 100000013
    try:
        nPages = MD.get_document_page_count(sCabinet, nDocID)
        print('Completed page count for document ID: ' + str(nDocID) + ' in cabinet: ' + str(sCabinet))
        print('Page count = ' + str(nPages))
        print('Test passed')
        n_pass += 1
    except:
        print('Count pages failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Update OCR status - success case")
    # Will need some meaningful cabinet/docId/jobId combination within the test system
    sCabinet = '1'
    nDocID = 100000020
    nJobID = 5
    try:
        nPages = AI.set_job_OCR_status(nJobID, sCabinet, nDocID)
        print('Completed status update for JobID: ' + str(nJobID))
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Update OCR status failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Update OCR status - error case")
    # Will need some meaningful cabinet/docId/jobId combination within the test system
    # It is expected that this case will be a failure example (MT_Status == 2)
    # This test checks that the process runs, but does not validate the outcome
    sCabinet = '1'
    nDocID = 100000019
    nJobID = 4
    try:
        nPages = AI.set_job_OCR_status(nJobID, sCabinet, nDocID)
        print('Completed status update for JobID: ' + str(nJobID))
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Update OCR status failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Read MAF list")
    # Will need a meaningful list ID
    nMAFListID = 1
    try:
        rsMAF = MD.get_MAF_list(nMAFListID)
        print('Read MAF list for ID: ' + str(nMAFListID) + ', count = ' + str(len(rsMAF)))
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Read MAF list failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Read fixed text classifier rules list")
    # Will need a meaningful list ID
    nMAFListID = 1
    try:
        rules = AI.get_fixed_text_classifier_rules(nMAFListID)
        print('Fixed text classifier rules list for ID: ' + str(nMAFListID) + ', count = ' + str(len(rules)))
        print('Rules (up to 10) : ', rules[0:10])
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Read text classifier rules list failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Process fixed text classifier")
    # Will need some meaningful cabinet/docId/jobId combination within the test system
    # It is expected that this case will be a failure example (MT_Status == 2)
    # This test checks that the process runs, but does not validate the outcome
    sCabinet = '1'
    nDocID = 100000019
    nJobID = 4
    try:
        result = AI.fixed_text_classifier(nJobID, sCabinet, nDocID)
        print('Completed processing for docID: ' + str(nDocID))
        print('Target DTID: ' + str(result))
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Process fixed text classifier failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Test update of classifier status")
    # Will need some meaningful cabinet/docId/jobId combination within the test system
    # It is expected that this case will be a failure example (MT_Status == 2)
    # This test checks that the process runs, but does not validate the outcome
    sCabinet = '1'
    nDocID = 100000019
    nJobID = 4
    try:
        AI.update_job_classification(nJobID,999,True)
        print('Completed fixed text classification for JobID: ' + str(nJobID))
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Process fixed text classifier failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Run fixed text classifier with update")
    # Will need some meaningful cabinet/docId/jobId combination within the test system
    # It is expected that this case will be a failure example (MT_Status == 2)
    # This test checks that the process runs, but does not validate the outcome
    sCabinet = '1'
    nDocID = 100000019
    nJobID = 4
    try:
        print('Running fixed text classification for JobID: ' + str(nJobID))
        AI.run_fixed_text_classifier(nJobID, sCabinet, nDocID)
        print('Completed fixed text classification for JobID: ' + str(nJobID))
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Process fixed text classifier failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Check target DTID for classified doc")
    # Will need some meaningful cabinet/docId/jobId combination within the test system
    # It is expected that this case will be a failure example (MT_Status == 2)
    # This test checks that the process runs, but does not validate the outcome
    sCabinet = '1'
    nDocID = 100000019
    nJobID = 4
    try:
        print('Getting target DTID for JobID: ' + str(nJobID))
        nTargetDTID = AI.get_targetDTID_for_classified_doc(nJobID)
        print('Read target for JobID: ' + str(nTargetDTID))
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Check target DTID test failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Test loading of reference extract rules")
    nMAFListID = 2
    try:
        rules = AI.get_ref_lookup_rules(nMAFListID)
        print('Reference extract rules list for ID: ' + str(nMAFListID) + ', count = ' + str(len(rules)))
        print('Rules (up to 10) : ', rules[0:10])
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Read text classifier rules list failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Test loading of cross reference values")
    sLookupTable = 'AIzDemoLookup'
    sLookupColumn = 'DemoKeyField'
    sLookupValue = 'Enterprise'
    lCrossRefCols = ['DemoLookup1', 'DemoLookup2', 'DemoLookup3', 'DemoLookup4', 'DemoLookup5']
    try:
        cr_values = AI.get_cross_ref_values(sLookupTable, sLookupColumn, sLookupValue, lCrossRefCols)
        print(
            'Cross reference values for ' + str(sLookupColumn) + ', in table ' + str(sLookupTable) + ', count = ' + str(
                len(cr_values)))
        print('Values (up to 5) : ', cr_values[0:5])
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Loading cross reference values failed...')
        n_fail += 1

    print("\n" + str(n_pass + n_fail + 1) + ": Run reference extract for classified doc")
    # Will need some meaningful cabinet/docId/jobId combination within the test system
    # It is expected that this case will be a failure example (MT_Status == 2)
    # This test checks that the process runs, but does not validate the outcome
    sCabinet = '1'
    nDocID = 100000020
    nJobID = 5
    try:
        print('Running reference extract for JobID: ' + str(nJobID))
        AI.run_reference_extract(nJobID, sCabinet, nDocID)
        print('Test passed')
        n_pass += 1
    except:
        print()
        print('Reference extract test failed...')
        n_fail += 1

    print("\nCompleted unit tests for " + MODULE_NAME)
    print(str(n_pass + n_fail) + " total tests")
    print(str(n_pass) + " tests passed")
    print(str(n_fail) + " tests failed\n")

    return n_pass, n_fail