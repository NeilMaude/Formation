# Test code here

from xml.etree import ElementTree

e = ElementTree.parse('D:\\git\\Python\\Formation\\ftp\\DVLA - HGV Daily Check-11600\Form-99800\DVLA - HGV Daily Check.xml').getroot()

for child in e:
    print(child.tag, child.attrib)

import json

with open('D:\Git\Python\Formation\FTP\BMW approved used car check-12763\Form-99889\BMW approved used car check.json') as f:
    data = json.load(f)

for d in data:
    print(d)

print('\nSpecific field extract')
print(data['8'])

