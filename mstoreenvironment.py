# File to hold the standard mstore user/password keys and other environmental variables
# Obviously, these aren't the values used in production!
# You will need to change these to match your development environment setup

# Debugging parameters
DEBUG = False                               # General debug flag

# Database security - should move user/password to command line parameters in production
user_secure = 'Y$gDcKScl@&+RAW9!EDq1enZu'   # should be created to match encrypted user name
pass_secure = 'qHZN34nrLRZeo@GU9Bg#yFwhb'   # should be created to match encrypted password
credentials_p = 'credentials.p'             # must exist

server_name = '169.254.5.23\SQLEXPRESS'     # SQL-Server instance
database_name = 'MSTOREAF_mstoreDemo'       # database

#Formation specific parameters
FORMATION_BASE = 'D:\Git\Python\Formation\FTP'      # Base location for incoming files





