# File to hold the standard mstore user/password keys and other environmental variables
# Obviously, these aren't the values used in production!
# You will need to change these to match your development environment setup

# Debugging parameters
DEBUG = True                               # General debug flag

# Database security - should move user/password to command line parameters in production
user_secure = 'Y$gDcKScl@&+RAW9!EDq1enZu'   # should be created to match encrypted user name
pass_secure = 'qHZN34nrLRZeo@GU9Bg#yFwhb'   # should be created to match encrypted password
credentials_p = 'credentials.p'             # must exist

server_name = '169.254.5.23\SQLEXPRESS'     # SQL-Server instance
database_name = 'MSTOREAF_mstoreDemo'       # database

#Formation specific parameters
FORMATION_BASE = 'D:\Git\Python\Formation\FTP'      # Base location for incoming files
SWEEP_BASE = 'D:\Temp\Formation-Sweep'              # Output location for Sweep files

FORM_TARGET_MAF_LIST = 3                            # MAF list with Formation output targets
FORM_FIELD_MAF_LIST = 4                             # MAF list with Formation required fields

FORMATION_DATA_TABLE = 'zFormationData'             # Data table to load - expected to exist already


