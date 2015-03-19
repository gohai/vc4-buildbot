#!/usr/bin/env python

import os
import subprocess
import time

# assume BuildRaspbianVc4.py is in the same dir as this one 
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PREFIX = time.strftime("%Y%m%d-%H%M-vc4")
UPLOAD_HOST = "sukzessiv.net"
UPLOAD_USER = "vc4-buildbot"
UPLOAD_KEY = os.path.dirname(os.path.realpath(__file__)) + "/sukzessiv-net.pem"
UPLOAD_PATH = "~/upload/"

def checkRoot():
	if os.geteuid() != 0:
		exit("You need to have root privileges to run this script")

def killHangingBuilds():
	subprocess.call("pkill -f \"BuildRaspbianVc4\"", shell=True)

def UploadTempFiles():
	# XXX: disable host check? or http://serverfault.com/questions/132970/can-i-automatically-add-a-new-host-to-known-hosts
	# XXX: add *.pem to .gitignore
	ret = subprocess.call("scp -Bpq -i " + UPLOAD_KEY + " /tmp/*-vc4* " + UPLOAD_USER + "@" + UPLOAD_HOST + ":" + UPLOAD_PATH, shell=True)
	return ret

def DeleteTempFiles():
	subprocess.call("rm /tmp/*-vc4*", shell=True)

def BuildRaspbianVc4():
	# preserve original kernel on build machine
	# XXX: flag
	# XXX: still leaves a window for things to go wrong
	subprocess.check_call("cp /boot/kernel.img /boot/kernel.img.orig", shell=True)
	subprocess.check_call("cp /boot/kernel7.img /boot/kernel7.img.orig", shell=True)
	ret = subprocess.call(SCRIPT_DIR + "/BuildRaspbianVc4.py >/tmp/" + PREFIX + ".log 2>&1", shell=True)
	if not ret:
		subprocess.call("mv /tmp/" + PREFIX + ".log /tmp/" + PREFIX + "-success.log", shell=True)
		subprocess.call("bzip2 -9 /tmp/" + PREFIX + "-success.log", shell=True)
	else:
		subprocess.call("mv /tmp/" + PREFIX + ".log /tmp/" + PREFIX + "-failure.log", shell=True)
		subprocess.call("bzip2 -9 /tmp/" + PREFIX + "-failure.log", shell=True)
	subprocess.check_call("mv /boot/kernel.img.orig /boot/kernel.img", shell=True)
	subprocess.check_call("mv /boot/kernel7.img.orig /boot/kernel7.img", shell=True)
	return ret

def TarRaspbianVc4():
	# XXX: optionally include src
	# XXX: better to temp. move original dir?
	subprocess.check_call("tar cfp /tmp/" + PREFIX + ".tar /boot/config.txt /boot/kernel.img /boot/kernel.img-config /boot/kernel7.img /boot/kernel7.img-config /etc/ld.so.conf.d/01-libc.conf /lib/modules/*-raspbian-* /usr/local --exclude=\"/usr/local/bin/indiecity\" --exclude=\"/usr/local/games\" --exclude=\"/usr/local/lib/python*\" --exclude=\"/usr/local/lib/site_ruby\" --exclude=\"/usr/local/src\" --exclude=\"/usr/local/sbin\" --exclude=\"/usr/local/share/applications\" --exclude=\"/usr/local/share/ca-certificates\" --exclude=\"/usr/local/share/fonts\" --exclude=\"/usr/local/share/sgml\" --exclude=\"/usr/local/share/xml\" >/dev/null", shell=True)
	subprocess.check_call("bzip2 -9 /tmp/" + PREFIX + ".tar", shell=True)


# XXX: pull latest vc4-buildbot script
# XXX: umask?
checkRoot()
killHangingBuilds()
UploadTempFiles()
DeleteTempFiles()
ret = BuildRaspbianVc4()
if not ret:
	# success
	TarRaspbianVc4()
ret = UploadTempFiles()
if not ret:
	DeleteTempFiles()
# else:
#	there might be a temporary connectivity issue
#	in this case we'll try again next time this script is run
