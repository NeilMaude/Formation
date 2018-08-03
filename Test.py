# Test code here

from xml.etree import ElementTree

e = ElementTree.parse('D:\\git\\Python\\Formation\\ftp\\DVLA - HGV Daily Check-11600\Form-99800\DVLA - HGV Daily Check.xml').getroot()

for child in e:
    print(child.tag, child.attrib)

import json

with open('D:\\git\\Python\\Formation\\Samples\\DVLA - HGV Daily Check.json') as f:
    data = json.load(f)

for d in data:
    print(d)

for f in data['form_fields']:
    print(f)

