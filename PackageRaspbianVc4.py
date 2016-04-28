#!/usr/bin/env python

# Script to package and distribute Raspberry Pi disk images
# Copyright (C) 2015 Gottfried Haider
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.


import os
import subprocess
import re
import time

# assume BuildRaspbianVc4.py is in the same dir as this one 
CUSTOM_KERNEL = 1
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PREFIX = time.strftime("%Y%m%d-%H%M-vc4")
UPLOAD = 0
UPLOAD_HOST = "sukzessiv.net"
UPLOAD_USER = "vc4-buildbot"
UPLOAD_KEY = os.path.dirname(os.path.realpath(__file__)) + "/sukzessiv-net.pem"
UPLOAD_PATH = "~/upload/"
RASPBIAN_IMG_ENLARGE_BY_MB = 500
# this can be determined from fdisk *.img
RASPBIAN_IMG_BYTES_PER_SECTOR = 512
RASPBIAN_IMG_START_SECTOR_VFAT = 8192
RASPBIAN_IMG_START_SECTOR_EXT4 = 131072

# helper functions
def file_get_contents(fn):
		with open(fn) as f:
			return f.read()

def file_put_contents(fn, s):
		with open(fn, 'w') as f:
			f.write(s)

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
	subprocess.call("rm -f /tmp/*-vc4*", shell=True)

def BuildRaspbianVc4():
	ret = subprocess.call(SCRIPT_DIR + "/BuildRaspbianVc4.py >/tmp/" + PREFIX + ".log 2>&1", shell=True)
	if not ret:
		subprocess.call("mv /tmp/" + PREFIX + ".log /tmp/" + PREFIX + "-success.log", shell=True)
		subprocess.call("bzip2 -9 /tmp/" + PREFIX + "-success.log", shell=True)
		subprocess.call("cp /boot/issue-vc4.json /tmp/" + PREFIX + "-issue.json", shell=True)
	else:
		subprocess.call("mv /tmp/" + PREFIX + ".log /tmp/" + PREFIX + "-failure.log", shell=True)
		subprocess.call("bzip2 -9 /tmp/" + PREFIX + "-failure.log", shell=True)
	return ret

def TarRaspbianVc4():
	# XXX: optionally include src
	# XXX: better to temp. move original dir?
	if CUSTOM_KERNEL:
		subprocess.call("tar cfp /tmp/" + PREFIX + "-overlay.tar /boot/bcm2708-rpi-b.dtb /boot/bcm2708-rpi-b-plus.dtb /boot/bcm2708-rpi-cm.dtb /boot/bcm2709-rpi-2-b.dtb /boot/bcm2710-rpi-3-b.dtb /boot/config.txt /boot/issue-vc4.json /boot/kernel.img /boot/kernel.img-config /boot/kernel7.img /boot/kernel7.img-config /boot/overlays /etc/ld.so.conf.d/01-libc.conf /etc/profile.d/graphics-debug.sh /etc/rc.local /etc/security/limits.d/coredump.conf /home/pi/processing-test3d.* /lib/modules/*-2708* /lib/modules/*-2709* /usr/local --exclude=\"/usr/local/bin/indiecity\" --exclude=\"/usr/local/games\" --exclude=\"/usr/local/lib/python*\" --exclude=\"/usr/local/lib/site_ruby\" --exclude=\"/usr/local/src\" --exclude=\"/usr/local/sbin\" --exclude=\"/usr/local/share/ca-certificates\" --exclude=\"/usr/local/share/fonts\" --exclude=\"/usr/local/share/sgml\" --exclude=\"/usr/local/share/xml\" >/dev/null", shell=True)
	else:
		subprocess.call("tar cfp /tmp/" + PREFIX + "-overlay.tar /boot/config.txt /boot/issue-vc4.json /etc/ld.so.conf.d/01-libc.conf /etc/profile.d/graphics-debug.sh /etc/rc.local /etc/security/limits.d/coredump.conf /home/pi/processing-test3d.* /usr/local --exclude=\"/usr/local/bin/indiecity\" --exclude=\"/usr/local/games\" --exclude=\"/usr/local/lib/python*\" --exclude=\"/usr/local/lib/site_ruby\" --exclude=\"/usr/local/src\" --exclude=\"/usr/local/sbin\" --exclude=\"/usr/local/share/ca-certificates\" --exclude=\"/usr/local/share/fonts\" --exclude=\"/usr/local/share/sgml\" --exclude=\"/usr/local/share/xml\" >/dev/null", shell=True)
	subprocess.call("bzip2 -9 /tmp/" + PREFIX + "-overlay.tar", shell=True)
	return "/tmp/" + PREFIX + "-overlay.tar.bz2"

def TarProcessing():
	os.chdir("/usr/local/lib")
	subprocess.call("tar cfp /tmp/" + PREFIX + "-processing.tar processing-3.*", shell=True)
	subprocess.call("bzip2 -9 /tmp/" + PREFIX + "-processing.tar", shell=True)
	return "/tmp/" + PREFIX + "-processing.tar.bz2"

def ResizeRaspbianImage(fn, mbToAdd):
	subprocess.check_call("dd if=/dev/zero bs=1M count=" + str(mbToAdd) + " >>" + fn, shell=True)
	subprocess.check_call("fdisk " + fn + " <<EOF\nd\n2\nn\np\n2\n" + str(RASPBIAN_IMG_START_SECTOR_EXT4) + "\n\nw\nEOF", shell=True)
	subprocess.check_call("dd if=" + fn + " bs=" + str(RASPBIAN_IMG_BYTES_PER_SECTOR) + " count=" + str(RASPBIAN_IMG_START_SECTOR_EXT4) + " of=/tmp/part1", shell=True)
	subprocess.check_call("dd if=" + fn + " bs=" + str(RASPBIAN_IMG_BYTES_PER_SECTOR) + " skip=" + str(RASPBIAN_IMG_START_SECTOR_EXT4) + " of=/tmp/part2", shell=True)
	subprocess.check_call("e2fsck -f /tmp/part2", shell=True)
	subprocess.check_call("resize2fs /tmp/part2", shell=True)
	subprocess.check_call("cat /tmp/part1 /tmp/part2 > " + fn, shell=True)
	subprocess.check_call("rm -f /tmp/part1 /tmp/part2", shell=True)

def BuildRaspbianImage(overlay):
	subprocess.check_call("apt-get -y install zip", shell=True)
	os.chdir("/tmp")
	# make sure we have the latest version
	subprocess.call("wget -N http://downloads.raspberrypi.org/raspbian_latest", shell=True)
	subprocess.check_call("rm -Rf /tmp/raspbian-vc4", shell=True)
	subprocess.check_call("mkdir /tmp/raspbian-vc4", shell=True)
	os.chdir("/tmp/raspbian-vc4")
	subprocess.check_call("unzip ../raspbian_latest", shell=True)
	# this should yield one .img file inside /tmp/raspbian-vc4
	files = os.listdir("/tmp/raspbian-vc4")
	for fn in files:
		if fn.endswith(".img"):
			# make room for files we're adding to the image
			ResizeRaspbianImage("/tmp/raspbian-vc4/" + fn, RASPBIAN_IMG_ENLARGE_BY_MB)
			break
	subprocess.check_call("mkdir /tmp/raspbian-vc4/live", shell=True)
	subprocess.check_call("mount -o offset=" + str(RASPBIAN_IMG_START_SECTOR_EXT4 * RASPBIAN_IMG_BYTES_PER_SECTOR) + " -t ext4 *.img live", shell=True)
	subprocess.check_call("mount -o offset=" + str(RASPBIAN_IMG_START_SECTOR_VFAT * RASPBIAN_IMG_BYTES_PER_SECTOR) + " -t vfat *.img live/boot", shell=True)
	os.chdir("/tmp/raspbian-vc4/live")
	# update firmware
	subprocess.check_call("SKIP_BACKUP=1 SKIP_WARNING=1 chroot /tmp/raspbian-vc4/live rpi-update", shell=True)
	# change the default X server for startx
	xserverrc = file_get_contents("/tmp/raspbian-vc4/live/etc/X11/xinit/xserverrc")
	xserverrc = re.sub('/usr/bin/X', '/usr/local/bin/Xorg', xserverrc)
	file_put_contents("/tmp/raspbian-vc4/live/etc/X11/xinit/xserverrc", xserverrc)
	# change the default X server running after startup
	lightdmconf = file_get_contents("/tmp/raspbian-vc4/live/etc/lightdm/lightdm.conf")
	lightdmconf = re.sub("#xserver-command=X", "xserver-command=/usr/local/bin/Xorg", lightdmconf)
	file_put_contents("/tmp/raspbian-vc4/live/etc/lightdm/lightdm.conf", lightdmconf)
	if CUSTOM_KERNEL:
		# remove obsolete DT overlay files
		subprocess.check_call("rm -Rf /boot/overlays/*.dtb", shell=True)
		# remove obsolete kernel modules
		subprocess.check_call("rm -Rf /tmp/raspbian-vc4/live/lib/modules/*", shell=True)
	subprocess.check_call("tar vfxp " + overlay, shell=True)
	# install libglew1.7 needed for mesa-demos (seems to be installed by default in Jessie)
	#subprocess.check_call("chroot /tmp/raspbian-vc4/live apt-get -y install libglew1.7", shell=True)
	# install gstreamer0.10 plugins for processing-video
	# XXX: gstreamer0.10-ffmpeg is no longer available in Jessie
	#subprocess.check_call("chroot /tmp/raspbian-vc4/live apt-get -y install gstreamer0.10-plugins-good gstreamer0.10-plugins-bad gstreamer0.10-plugins-ugly", shell=True)
	# install libtxc-dxtn-s2tc0 to silence Mesa warnings
	subprocess.check_call("chroot /tmp/raspbian-vc4/live apt-get -y install libtxc-dxtn-s2tc0", shell=True)
	# install libvdpau for gst-plugins-bad (seems to be installed by default in Jessie)
	# XXX: http://mirrordirector.raspbian.org/raspbian/pool/main/libv/libvdpau/libvdpau1_0.4.1-7_armhf.deb currently gives 404
	# XXX: vdpau-driver, vdpauinfo
	#subprocess.check_call("chroot /tmp/raspbian-vc4/live apt-get -y install libvdpau1", shell=True)
	# move the binary graphics driver to disable jogl's auto-detection
	# XXX: guessing raspi-config leaves this intact as well
	#subprocess.check_call("mv /tmp/raspbian-vc4/live/opt/vc /tmp/raspbian-vc4/live/opt/vc.bak", shell=True)
	# rebuild ld.so.cache
	subprocess.check_call("ldconfig -r /tmp/raspbian-vc4/live", shell=True)
	os.chdir("/tmp/raspbian-vc4")
	subprocess.check_call("umount live/boot", shell=True)
	subprocess.check_call("umount live", shell=True)
	subprocess.check_call("zip -9 ../" + PREFIX +"-image.zip *.img", shell=True)
	os.chdir("/tmp")
	subprocess.check_call("rm -Rf /tmp/raspbian-vc4", shell=True)
	# we keep raspbian_latest around for future invocations (although it looks like /tmp gets cleaned?)
	return "/tmp/" + PREFIX + "-image.zip"

# XXX: pull latest vc4-buildbot script
# XXX: umask?
# XXX: prepopulate ssh host keys in known_hosts
checkRoot()
killHangingBuilds()
if UPLOAD:
	UploadTempFiles()
	DeleteTempFiles()
# preserve original kernel and device tree on build machine

if CUSTOM_KERNEL:
	if not os.path.exists("/boot/kernel.img.orig"):
		subprocess.call("cp /boot/kernel.img /boot/kernel.img.orig", shell=True)
	if not os.path.exists("/boot/bcm2708-rpi-b.dtb.orig"):
		subprocess.call("cp /boot/bcm2708-rpi-b.dtb /boot/bcm2708-rpi-b.dtb.orig", shell=True)
	if not os.path.exists("/boot/bcm2708-rpi-b-plus.dtb.orig"):
		subprocess.call("cp /boot/bcm2708-rpi-b-plus.dtb /boot/bcm2708-rpi-b-plus.dtb.orig", shell=True)
	if not os.path.exists("/boot/bcm2708-rpi-cm.dtb.orig"):
		subprocess.call("cp /boot/bcm2708-rpi-cm.dtb /boot/bcm2708-rpi-cm.dtb.orig", shell=True)
	if not os.path.exists("/boot/kernel7.img.orig"):
		subprocess.call("cp /boot/kernel7.img /boot/kernel7.img.orig", shell=True)
	if not os.path.exists("/boot/bcm2709-rpi-2-b.dtb.orig"):
		subprocess.call("cp /boot/bcm2709-rpi-2-b.dtb /boot/bcm2709-rpi-2-b.dtb.orig", shell=True)
	if not os.path.exists("/boot/bcm2710-rpi-3-b.dtb.orig"):
		subprocess.call("cp /boot/bcm2710-rpi-3-b.dtb /boot/bcm2710-rpi-3-b.dtb.orig", shell=True)
	if not os.path.exists("/boot/overlays.orig"):
		subprocess.call("cp -r /boot/overlays /boot/overlays.orig", shell=True)
ret = BuildRaspbianVc4()
if not ret:
	# success
	tar = TarRaspbianVc4()
	TarProcessing()
if CUSTOM_KERNEL:
	# restore original kernel
	subprocess.call("mv /boot/kernel.img.orig /boot/kernel.img", shell=True)
	subprocess.call("mv /boot/bcm2708-rpi-b.dtb.orig /boot/bcm2708-rpi-b.dtb", shell=True)
	subprocess.call("mv /boot/bcm2708-rpi-b-plus.dtb.orig /boot/bcm2708-rpi-b-plus.dtb", shell=True)
	subprocess.call("mv /boot/bcm2708-rpi-cm.dtb.orig /boot/bcm2708-rpi-cm.dtb", shell=True)
	subprocess.call("mv /boot/kernel7.img.orig /boot/kernel7.img", shell=True)
	subprocess.call("mv /boot/bcm2709-rpi-2-b.dtb.orig /boot/bcm2709-rpi-2-b.dtb", shell=True)
	subprocess.call("mv /boot/bcm2710-rpi-3-b.dtb.orig /boot/bcm2710-rpi-3-b.dtb", shell=True)
	subprocess.call("rm -rf /boot/overlays", shell=True)
	subprocess.call("mv /boot/overlays.orig /boot/overlays", shell=True)
if not ret:
	BuildRaspbianImage(tar)
if UPLOAD:
	ret = UploadTempFiles()
	if not ret:
		DeleteTempFiles()
#else:
#	there might be a temporary connectivity issue
#	in this case we'll try again next time this script is run

# XXX: limit login to scp?
# XXX: delete old builds on the server
# XXX: ~/.ssh mode 700?
