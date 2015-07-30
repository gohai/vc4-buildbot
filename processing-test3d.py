#!/usr/bin/env python

# Script to test Processing on the Raspberry Pi
# Copyright (C) 2015 Gottfried Haider
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.


import os
import subprocess
import json

EXAMPLES_DIR = "/usr/local/lib/processing/modes/java/examples"

def default_input(message, defaultVal):
	if defaultVal:
		return raw_input("%s [%s]: " % (message,defaultVal)) or defaultVal
	else:
		return raw_input("%s: " % (message))

# XXX: --redo flag

with open("processing-test3d.json") as f:
	data = json.load(f)

try:
	with open("/boot/issue-vc4.json") as f:
		sys = json.load(f)
	if data.get("system") is None:
		data["system"] = sys
except IOError:
	pass

for row in data.get("tests", []):
	sketch = row.get("sketch")
	ignore = row.get("ignore", 0)
	result = row.get("result")
	if result is not None:
		print "Skipping " + sketch + " (already done)"
	if ignore is 1:
		print "Skipping " + sketch + " (ignored)"
		row["result"] = -1
	if ignore is not 1 and result is None:
		try:
			#retval = subprocess.call("echo Running " + sketch + " | tee -a processing-test3d.out && ls 2>&1 | tee -a processing-test.out", shell=True)
			retval = subprocess.call("echo Running " + sketch + " | tee -a processing-test3d.out && processing-java --sketch=\"" + EXAMPLES_DIR + "/" + sketch + "\" --run 2>&1 | tee -a processing-test.out", shell=True)
		except KeyboardInterrupt:
			retval = 0
		if retval is not 0:
			row["result"] = 0
			row["comment"] = "sketch returned " + retval
		else:
			result = int(raw_input("Result (0 not working, 1 low fps or similar, 2 usable): "))
			row["result"] = result
		row["comment"] = default_input("Comment", row.get("comment", ""))
		with open("processing-test3d.json", "w") as f:
			json.dump(data, f, indent=4, separators=(',', ': '))

print "Done (Results are stored in processing-test3d.json, output in processing-test3d.out)"
