# Testing the os.walk stuff for polling Formation file creation

import os

START_DIR = 'D:\Git\Python\Formation\FTP'

print('\nCurrent directory:', os.getcwd(), '\n')

print('All directories in the tree from:', START_DIR)
for root, dirs, files in os.walk(START_DIR, topdown=True):
    for name in dirs:
        print(os.path.join(root, name))

print('\nAll directories just in the top level:')
for d in os.listdir(START_DIR):
    if os.path.isdir(os.path.join(START_DIR,d)):
        print(os.path.join(START_DIR,d))

print('\nList forms created, by type:')
for d in os.listdir(START_DIR):
    #d will be the form type
    if os.path.isdir(os.path.join(START_DIR, d)):
        for f in os.listdir(os.path.join(START_DIR,d)):
            form_base = os.path.join(START_DIR, d)
            form_base = os.path.join(form_base, f)
            if os.path.isdir(form_base):
                print('Form type: %s, form instance: %s' % (d,f))
                print('Form base path:', form_base)

print('\nForm files by form instance:')
for d in os.listdir(START_DIR):
    if os.path.isdir(os.path.join(START_DIR, d)):
        #d will be the form type
        for i in os.listdir(os.path.join(START_DIR,d)):
            form_base = os.path.join(START_DIR,d)
            form_base = os.path.join(form_base,i)
            if os.path.isdir(form_base):
                for f in os.listdir(form_base):
                    print(f)

print('\nFind XML, JSON and PDF files by form instance:')
for d in os.listdir(START_DIR):
    if os.path.isdir(os.path.join(START_DIR, d)):
        #d will be the form type
        for i in os.listdir(os.path.join(START_DIR,d)):
            form_base = os.path.join(START_DIR,d)
            form_base = os.path.join(form_base,i)
            if os.path.isdir(form_base):
                for f in os.listdir(form_base):
                    if f.upper().endswith('.XML'):
                        print('Found XML file:',f)
                    if f.upper().endswith('.JSON'):
                        print('Found JSON file:', f)
                    if f.upper().endswith('.PDF'):
                        print('Found PDF file:', f)