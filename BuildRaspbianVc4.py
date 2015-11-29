#!/usr/bin/env python

# Script to build upstream Kernel, Mesa, XServer and friends on Raspberry Pi
# Copyright (C) 2015 Gottfried Haider
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.


import os
import subprocess
import re
import json

LINUX_GIT_REPO_2708 = "https://github.com/raspberrypi/linux.git"
LINUX_GIT_BRANCH_2708 = "rpi-4.2.y"
LINUX_GIT_REPO_2709 = "https://github.com/raspberrypi/linux.git"
LINUX_GIT_BRANCH_2709 = "rpi-4.2.y"
MESA_GIT_REPO = "git://anongit.freedesktop.org/mesa/mesa"
MESA_GIT_BRANCH = "master"
PROCESSING_GIT_REPO = "https://github.com/processing/processing.git"
PROCESSING_GIT_BRANCH = "master"
PROCESSING_VERSION = "3.0.1"
XSERVER_GIT_REPO = "git://anongit.freedesktop.org/xorg/xserver"
XSERVER_GIT_BRANCH = "master"
DATA_DIR = os.path.dirname(os.path.realpath(__file__))
MAKE_OPTS = "-j3 -l3"
CLEANUP = 1

issue = {}

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

def updateHostApt():
	subprocess.check_call("apt-get -y update", shell=True)

def updateFirmware():
	# mask_gpu_interrupt0 gets obsoleted by a post-Jesse firmware update
	subprocess.check_call("rpi-update", shell=True)

def updateConfigTxt():
	txt = file_get_contents("/boot/config.txt")
	added_comment = 0
	match = re.findall(r'^# added for vc4 driver$', txt, re.MULTILINE)
	if 0 < len(match):
		added_comment = 1
	# set mask_gpu_interrupt0=0x400
	# this is not necessary anymore with newer firmwares
	#match = re.findall(r'^mask_gpu_interrupt0=(.*)$', txt, re.MULTILINE)
	#if 0 < len(match):
	#	txt = re.sub(r'(^)mask_gpu_interrupt0=(.*)($)', r'\1mask_gpu_interrupt0=0x400\3', txt, 0, re.MULTILINE)
	#else:
	#	txt = txt.strip() + "\n\n" + "# added for vc4 driver\n" + "mask_gpu_interrupt0=0x400\n"
	#	added_comment = 1
	# set avoid_warnings=2 to remove warning overlay
	match = re.findall(r'^avoid_warnings=(.*)$', txt, re.MULTILINE)
	if 0 < len(match):
		txt = re.sub(r'(^)avoid_warnings=(.*)($)', r'\1avoid_warnings=2\3', txt, 0, re.MULTILINE)
	else:
		if not added_comment:
			txt = txt.strip() + "\n\n" + "# added for vc4 driver\n"
			added_comment = 1
		txt = txt + "avoid_warnings=2\n"
	# set disable_overscan=1 to workaround a bug in vc4 where the
	# mouse cursor does not take the margins around the image into
	# account
	#match = re.findall(r'^disable_overscan=(.*)$', txt, re.MULTILINE)
	#if 0 < len(match):
	#	txt = re.sub(r'(^)disable_overscan=(.*)($)', r'\1disable_overscan=1\3', txt, 0, re.MULTILINE)
	#else:
	#	if not added_comment:
	#		txt = txt.strip() + "\n\n" + "# added for vc4 driver\n"
	#		added_comment = 1
	#	txt = txt + "disable_overscan=1\n"
	# add vc4 overlay
	match = re.findall(r'^dtoverlay=vc4-kms-v3d$', txt, re.MULTILINE)
	if 0 == len(match):
		if not added_comment:
			txt = txt.strip() + "\n\n" + "# added for vc4 driver\n"
			added_comment = 1
		txt = txt + "dtoverlay=vc4-kms-v3d\n"
	file_put_contents("/boot/config.txt", txt)

def updateLdConfig():
	# this makes /usr/local/lib come before /{usr/,}lib/arm-linux-gnueabihf
	if not os.path.exists("/etc/ld.so.conf.d/01-libc.conf"):
		subprocess.check_call("mv /etc/ld.so.conf.d/libc.conf /etc/ld.so.conf.d/01-libc.conf", shell=True)
	subprocess.check_call("ldconfig")

def enableCoredumps():
	file_put_contents("/etc/security/limits.d/coredump.conf", "*\tsoft\tcore\tunlimited")

def enableDebugEnvVars():
	# MESA_DEBUG macro needs this library for texture compression
	subprocess.check_call("apt-get -y install libtxc-dxtn-s2tc0", shell=True)
	out = "export LIBGL_DEBUG=1\n"
	out += "export MESA_DEBUG=1\n"
	out += "export EGL_LOG_LEVEL=debug\n"
	out += "export GLAMOR_DEBUG=1\n"
	file_put_contents("/etc/profile.d/graphics-debug.sh", out)

def updateUdevGpioRule():
	# this is needed for recent kernels
	# proposed fix in https://github.com/raspberrypi/linux/issues/791 didn't work for me
	udev = file_get_contents("/etc/udev/rules.d/99-com.rules")
	udev = re.sub('/sys/devices/virtual/gpio\'', '/sys/devices/virtual/gpio; chown -RH root:gpio /sys/class/gpio/* && chmod -R 770 /sys/class/gpio/*\'', udev)
	file_put_contents("/etc/udev/rules.d/99-com.rules", udev)

def updateRcLocalForLeds():
	# LEDs can only be controlled by the root user by default
	# couldn't get a udev rule for this to work
	rclocal = file_get_contents("/etc/rc.local")
	match = re.findall(r'^chmod -R a\+rw /sys/class/leds/\*$', rclocal, re.MULTILINE)
	if 0 == len(match):
		rclocal = re.sub('exit 0\n', '# allow regular users to control the leds\nchmod -R a+rw /sys/class/leds/*\n\nexit 0\n', rclocal)
		file_put_contents("/etc/rc.local", rclocal)

def getGitInfo():
	info = {}
	info['commit'] = subprocess.check_output("git rev-parse HEAD", shell=True).rstrip()
	info['branch'] = subprocess.check_output("git rev-parse --abbrev-ref HEAD", shell=True).rstrip()
	info['url'] = subprocess.check_output("git config --get remote.origin.url", shell=True).rstrip()
	return info

def buildXorgMacros():
	subprocess.check_call("apt-get -y install autoconf", shell=True)
	if not os.path.exists("/usr/local/src/xorg-macros"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/util/macros /usr/local/src/xorg-macros", shell=True)
	os.chdir("/usr/local/src/xorg-macros")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)
	# move .pc file to standard path
	subprocess.check_call("mkdir -p /usr/local/lib/pkgconfig", shell=True)
	subprocess.check_call("mv /usr/local/share/pkgconfig/xorg-macros.pc /usr/local/lib/pkgconfig", shell=True)
	issue['xorg-macros'] = getGitInfo()

def buildXcbProto():
	if not os.path.exists("/usr/local/src/xcb-proto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xcb/proto /usr/local/src/xcb-proto", shell=True)
	os.chdir("/usr/local/src/xcb-proto")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	issue['xcb-proto'] = getGitInfo()

def buildLibXcb():
	# needed to prevent xcb_poll_for_special_event linker error when installing mesa
	subprocess.check_call("apt-get -y install libtool libpthread-stubs0-dev libxau-dev", shell=True)
	if not os.path.exists("/usr/local/src/libxcb"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xcb/libxcb /usr/local/src/libxcb", shell=True)
	os.chdir("/usr/local/src/libxcb")
	subprocess.call("git pull", shell=True)
	# xorg-macros.m4 got installed outside of the regular search path of aclocal
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)
	issue['libxcb'] = getGitInfo()

def buildGlProto():
	if not os.path.exists("/usr/local/src/glproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/glproto /usr/local/src/glproto", shell=True)
	os.chdir("/usr/local/src/glproto")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)
	issue['glproto'] = getGitInfo()

def buildLibDrm():
	subprocess.check_call("apt-get -y install libudev-dev", shell=True)
	if not os.path.exists("/usr/local/src/libdrm"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/mesa/drm /usr/local/src/libdrm", shell=True)
	os.chdir("/usr/local/src/libdrm")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local --disable-amdgpu --disable-freedreno --disable-vmwgfx --disable-radeon --disable-nouveau", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)
	issue['libdrm'] = getGitInfo()

def buildDri2Proto():
	if not os.path.exists("/usr/local/src/dri2proto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/dri2proto /usr/local/src/dri2proto", shell=True)
	os.chdir("/usr/local/src/dri2proto")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)
	issue['dri2proto'] = getGitInfo()

def buildDri3Proto():
	# unavailable in raspbian
	if not os.path.exists("/usr/local/src/dri3proto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/dri3proto /usr/local/src/dri3proto", shell=True)
	os.chdir("/usr/local/src/dri3proto")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)
	issue['dri3proto'] = getGitInfo()

def buildPresentProto():
	# unavailable in raspbian
	if not os.path.exists("/usr/local/src/presentproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/presentproto /usr/local/src/presentproto", shell=True)
	os.chdir("/usr/local/src/presentproto")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)
	issue['presentproto'] = getGitInfo()

def buildLibXShmFence():
	# unavailable in raspbian
	if not os.path.exists("/usr/local/src/libxshmfence"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/lib/libxshmfence /usr/local/src/libxshmfence", shell=True)
	os.chdir("/usr/local/src/libxshmfence")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)
	issue['libxshmfence'] = getGitInfo()

def buildMesa():
	# XXX: compile libvdpau from sources (needs to be >= 1.1 but the packaged one is 0.4.1, re-add --enable-vdpau)
	subprocess.check_call("apt-get -y install bison flex python-mako libx11-dev libx11-xcb-dev libxext-dev libxdamage-dev libxfixes-dev libudev-dev libexpat-dev gettext libomxil-bellagio-dev", shell=True)
	if not os.path.exists("/usr/local/src/mesa"):
		subprocess.check_call("git clone " + MESA_GIT_REPO + " /usr/local/src/mesa", shell=True)
	os.chdir("/usr/local/src/mesa")
	subprocess.check_call("git remote set-url origin " + MESA_GIT_REPO, shell=True)
	subprocess.call("git fetch", shell=True)
	subprocess.check_call("git checkout -f -B " + MESA_GIT_BRANCH + " origin/" + MESA_GIT_BRANCH, shell=True)
	# workaround https://bugs.freedesktop.org/show_bug.cgi?id=80848
	if not os.path.exists("/usr/lib/arm-linux-gnueabihf/tmp-libxcb"):
		subprocess.call("mkdir /usr/lib/arm-linux-gnueabihf/tmp-libxcb", shell=True)
		subprocess.check_call("mv /usr/lib/arm-linux-gnueabihf/libxcb* /usr/lib/arm-linux-gnueabihf/tmp-libxcb", shell=True)
	subprocess.check_call("ldconfig", shell=True)
	# XXX: unsure if swrast is needed
	# --enable-glx-tls matches Raspbian's config
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local --with-gallium-drivers=vc4 --enable-gles1 --enable-gles2 --with-egl-platforms=x11,drm --with-dri-drivers=swrast --enable-dri3 --enable-glx-tls --enable-omx", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	# undo workaround
	subprocess.check_call("mv /usr/lib/arm-linux-gnueabihf/tmp-libxcb/* /usr/lib/arm-linux-gnueabihf", shell=True)
	subprocess.check_call("rmdir /usr/lib/arm-linux-gnueabihf/tmp-libxcb", shell=True)
	subprocess.check_call("ldconfig", shell=True)
	issue['mesa'] = getGitInfo()

def buildXTrans():
	# xserver: Requested 'xtrans >= 1.3.5' but version of XTrans is 1.2.7
	if not os.path.exists("/usr/local/src/libxtrans"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/lib/libxtrans /usr/local/src/libxtrans", shell=True)
	os.chdir("/usr/local/src/libxtrans")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	# move .pc file to standard path
	subprocess.check_call("mv /usr/local/share/pkgconfig/xtrans.pc /usr/local/lib/pkgconfig", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	issue['xtrans'] = getGitInfo()

def buildXProto():
	# xserver: Requested 'xproto >= 7.0.26' but version of Xproto is 7.0.23
	if not os.path.exists("/usr/local/src/xproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/xproto /usr/local/src/xproto", shell=True)
	os.chdir("/usr/local/src/xproto")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	issue['xproto'] = getGitInfo()

def buildXExtProto():
	# xserver: Requested 'xextproto >= 7.2.99.901' but version of XExtProto is 7.2.1
	if not os.path.exists("/usr/local/src/xextproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/xextproto /usr/local/src/xextproto", shell=True)
	os.chdir("/usr/local/src/xextproto")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	issue['xextproto'] = getGitInfo()

def buildInputProto():
	# xserver: Requested 'inputproto >= 2.3' but version of InputProto is 2.2
	if not os.path.exists("/usr/local/src/inputproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/inputproto /usr/local/src/inputproto", shell=True)
	os.chdir("/usr/local/src/inputproto")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	issue['inputproto'] = getGitInfo()

def buildRandrProto():
	# xserver: Requested 'randrproto >= 1.4.0' but version of RandrProto is 1.3.2
	if not os.path.exists("/usr/local/src/randrproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/randrproto /usr/local/src/randrproto", shell=True)
	os.chdir("/usr/local/src/randrproto")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)
	issue['randrproto'] = getGitInfo()

def buildFontsProto():
	# xserver: Requested 'fontsproto >= 2.1.3' but version of FontsProto is 2.1.2
	if not os.path.exists("/usr/local/src/fontsproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/fontsproto /usr/local/src/fontsproto", shell=True)
	os.chdir("/usr/local/src/fontsproto")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	issue['fontsproto'] = getGitInfo()

def buildLibEpoxy():
	# xserver: needed for glamor, unavailable in raspbian
	if not os.path.exists("/usr/local/src/libepoxy"):
		subprocess.check_call("git clone https://github.com/anholt/libepoxy.git /usr/local/src/libepoxy", shell=True)
	os.chdir("/usr/local/src/libepoxy")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)
	issue['libepoxy'] = getGitInfo()

def buildXServer():
	subprocess.check_call("apt-get -y install libpixman-1-dev libssl-dev x11proto-xcmisc-dev x11proto-bigreqs-dev x11proto-render-dev x11proto-video-dev x11proto-composite-dev x11proto-record-dev x11proto-scrnsaver-dev x11proto-resource-dev x11proto-xf86dri-dev x11proto-xinerama-dev libxkbfile-dev libxfont-dev libpciaccess-dev libxcb-keysyms1-dev", shell=True)
	# without libxcb-keysyms1-dev compiling fails with "Keyboard.c:21:29: fatal error: xcb/xcb_keysyms.h: No such file or directory compilation terminated.
	if not os.path.exists("/usr/local/src/xserver"):
		subprocess.check_call("git clone " + XSERVER_GIT_REPO + " /usr/local/src/xserver", shell=True)
	os.chdir("/usr/local/src/xserver")
	subprocess.check_call("git remote set-url origin " + XSERVER_GIT_REPO, shell=True)
	subprocess.call("git fetch", shell=True)
	subprocess.check_call("git checkout -f -B " + XSERVER_GIT_BRANCH + " origin/" + XSERVER_GIT_BRANCH, shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local --enable-glamor --enable-dri2 --enable-dri3 --enable-present", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	# copy xorg.conf
	subprocess.call("mkdir /usr/local/etc/X11", shell=True)
	subprocess.check_call("cp "+DATA_DIR+"/xorg.conf /usr/local/etc/X11", shell=True)
	# workaround "XKB: Couldn't open rules file /usr/local/share/X11/xkb/rules/$"
	subprocess.call("ln -s /usr/share/X11/xkb/rules /usr/local/share/X11/xkb/rules", shell=True)
	# workaround "XKB: Failed to compile keymap"
	subprocess.call("ln -s /usr/bin/xkbcomp /usr/local/bin/xkbcomp", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	issue['xserver'] = getGitInfo()

def buildMesaDemos():
	# this needs libglew1.7 to run
	subprocess.check_call("apt-get -y install libglew-dev", shell=True)
	if not os.path.exists("/usr/local/src/mesa-demos"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/mesa/demos /usr/local/src/mesa-demos", shell=True)
	os.chdir("/usr/local/src/mesa-demos")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)
	issue['mesa-demos'] = getGitInfo()

def buildLibEvdev():
	# >= 0.4 needed for xf86-input-evdev
	if not os.path.exists("/usr/local/src/libevdev"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/libevdev /usr/local/src/libevdev", shell=True)
	os.chdir("/usr/local/src/libevdev")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)
	issue['libevdev'] = getGitInfo()

def buildInputEvdev():
	# ABI major version on raspbian is 16 (vs. currently 22), so build evdev module
	subprocess.check_call("apt-get -y install libmtdev-dev", shell=True)
	if not os.path.exists("/usr/local/src/xf86-input-evdev"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/driver/xf86-input-evdev /usr/local/src/xf86-input-evdev", shell=True)
	os.chdir("/usr/local/src/xf86-input-evdev")
	subprocess.call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	issue['xf86-input-evdev'] = getGitInfo()

def buildLinux():
	# install dependencies
	# (menuconfig additionally needs ncurses-dev)
	subprocess.check_call("apt-get -y install bc", shell=True)
	if not os.path.exists("/usr/local/src/raspberrypi-tools"):
		subprocess.check_call("git clone https://github.com/raspberrypi/tools /usr/local/src/raspberrypi-tools", shell=True)
	os.chdir("/usr/local/src/raspberrypi-tools")
	subprocess.call("git pull", shell=True)
	# get up-to-date git tree
	if not os.path.exists("/usr/local/src/linux"):
		subprocess.check_call("git clone " + LINUX_GIT_REPO_2708 + " /usr/local/src/linux ", shell=True)
	issue['raspberrypi-tools'] = getGitInfo()
	os.chdir("/usr/local/src/linux")
	# compile a downstream kernel for 2708
	subprocess.check_call("git remote set-url origin " + LINUX_GIT_REPO_2708, shell=True)
	subprocess.call("git fetch", shell=True)
	subprocess.check_call("git checkout -f -B " + LINUX_GIT_BRANCH_2708 + " origin/" + LINUX_GIT_BRANCH_2708, shell=True)
	subprocess.check_call("make mrproper", shell=True)
	#subprocess.check_call("cp " + DATA_DIR + "/config-2708 .config", shell=True)
	subprocess.check_call("make bcmrpi_defconfig", shell=True)
	# change localversion
	subprocess.check_call("sed -i 's/CONFIG_LOCALVERSION=\"\"/CONFIG_LOCALVERSION=\"-2708\"/' .config", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	# remove old kernel versions
	subprocess.check_call("rm -rf /lib/modules/*-2708*", shell=True)
	subprocess.check_call("make modules_install", shell=True)
	subprocess.check_call("cp arch/arm/boot/dts/bcm2708-rpi-b.dtb /boot/bcm2708-rpi-b.dtb", shell=True)
	subprocess.check_call("cp arch/arm/boot/dts/bcm2708-rpi-b-plus.dtb /boot/bcm2708-rpi-b-plus.dtb", shell=True)
	subprocess.check_call("cp arch/arm/boot/dts/bcm2708-rpi-cm.dtb /boot/bcm2708-rpi-cm.dtb", shell=True)
	# this signals to the bootloader that device tree is supported
	subprocess.check_call("/usr/local/src/raspberrypi-tools/mkimage/mkknlimg --dtok arch/arm/boot/zImage arch/arm/boot/zImage", shell=True)
	subprocess.check_call("cp arch/arm/boot/zImage /boot/kernel.img", shell=True)
	subprocess.check_call("cp .config /boot/kernel.img-config", shell=True)
	issue['linux-2708'] = getGitInfo()
	# compile a downstream kernel for 2709
	subprocess.check_call("git remote set-url origin " + LINUX_GIT_REPO_2709, shell=True)
	subprocess.call("git fetch", shell=True)
	subprocess.check_call("git checkout -f -B " + LINUX_GIT_BRANCH_2709 + " origin/" + LINUX_GIT_BRANCH_2709, shell=True)
	subprocess.check_call("make mrproper", shell=True)
	#subprocess.check_call("cp " + DATA_DIR + "/config-2709 .config", shell=True)
	subprocess.check_call("make bcm2709_defconfig", shell=True)
	# change localversion
	subprocess.check_call("sed -i 's/CONFIG_LOCALVERSION=\"-v7\"/CONFIG_LOCALVERSION=\"-2709\"/' .config", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("rm -rf /lib/modules/*-2709*", shell=True)
	subprocess.check_call("make modules_install", shell=True)
	subprocess.check_call("cp arch/arm/boot/dts/bcm2709-rpi-2-b.dtb /boot/bcm2709-rpi-2-b.dtb", shell=True)
	# overlays are automatically generated with DT-enabled configs
	subprocess.check_call("rm -rf /boot/overlays/*.dtb", shell=True)
	subprocess.check_call("cp arch/arm/boot/dts/overlays/*.dtb /boot/overlays", shell=True)
	subprocess.check_call("/usr/local/src/raspberrypi-tools/mkimage/mkknlimg --dtok arch/arm/boot/zImage arch/arm/boot/zImage", shell=True)
	subprocess.check_call("cp arch/arm/boot/zImage /boot/kernel7.img", shell=True)
	subprocess.check_call("cp .config /boot/kernel7.img-config", shell=True)
	subprocess.check_call("cp arch/arm/boot/dts/overlays/vc4-kms-v3d-overlay.dtb /boot/overlays/", shell=True)
	if CLEANUP:
		subprocess.check_call("make mrproper", shell=True)
	issue['linux-2709'] = getGitInfo()

def buildGstreamer():
	# Raspbian seem to have a modified (?) gstreamer-1.0 that hooks into OpenMAX IL
	# let's see how the latest version of gstreamer performs
	# this should have support for vdpau and omx, not: vaapi
	# gst-plugins-bad checks for bcm_init on the host system
	# vdpau needs libvdpau1 installed on the host system to work (vdpauinfo still complains about a missing libvdpau_vc4.so)
	# unsure if omx needs libomxil-bellagio0 libomxil-bellagio0-components-* on host system (omx does not show up in gst-inspect-1.0 either way)
	subprocess.check_call("apt-get -y install libglib2.0-dev libvdpau-dev", shell=True)
	for pkg in ["gstreamer", "gst-plugins-base", "gst-plugins-good", "gst-plugins-bad", "gst-plugins-ugly", "gst-libav"]:
		if not os.path.exists("/usr/local/src/" + pkg):
			# 1.4 is the current stable branch
			subprocess.check_call("git clone --recursive --branch 1.4 git://anongit.freedesktop.org/gstreamer/" + pkg + " /usr/local/src/" + pkg, shell=True)
		os.chdir("/usr/local/src/" + pkg)
		# XXX: what about subprojects
		subprocess.call("git pull", shell=True)
		# we're missing gtk-doc-tools, so skip building the docs
		subprocess.check_call("./autogen.sh --prefix=/usr/local --disable-gtk-doc", shell=True)
		subprocess.check_call("make " + MAKE_OPTS, shell=True)
		subprocess.check_call("make install", shell=True)
		if CLEANUP:
			subprocess.check_call("make clean", shell=True)
		subprocess.check_call("ldconfig", shell=True)
	if not os.path.exists("/usr/local/src/gst-omx"):
		subprocess.check_call("git clone --recursive git://anongit.freedesktop.org/gstreamer/gst-omx /usr/local/src/gst-omx", shell=True)
	os.chdir("/usr/local/src/gst-omx")
	# XXX: what about subprojects
	subprocess.call("git pull", shell=True)
	# work around a compilation error
	# to build a VC IV specific backend: --with-omx-target=rpi
	# XXX: OMX_VideoExt.h... no, OMX_VIDEO_CodingVP8 is declared... no, OMX_VIDEO_CodingTheora is declared... no
	subprocess.check_call("CFLAGS=\"-DOMX_VERSION_MAJOR=1 -DOMX_VERSION_MINOR=1 -DOMX_VERSION_REVISION=2 -DOMX_VERSION_STEP=0\" ./autogen.sh --prefix=/usr/local --disable-gtk-doc --with-omx-target=generic", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)

def buildExtraProcessing():
	subprocess.check_call("apt-get -y install ant", shell=True)
	# Processing expects this directory to exist as as well
	if not os.path.exists("/usr/local/src/processing-docs"):
		subprocess.check_call("git clone https://github.com/processing/processing-docs.git /usr/local/src/processing-docs", shell=True)
	os.chdir("/usr/local/src/processing-docs")
	subprocess.call("git pull", shell=True)
	if not os.path.exists("/usr/local/src/processing"):
		subprocess.check_call("git clone " + PROCESSING_GIT_REPO + " /usr/local/src/processing", shell=True)
	os.chdir("/usr/local/src/processing")
	subprocess.check_call("git remote set-url origin " + PROCESSING_GIT_REPO, shell=True)
	subprocess.call("git fetch", shell=True)
	subprocess.check_call("git checkout -f -B " + PROCESSING_GIT_BRANCH + " origin/" + PROCESSING_GIT_BRANCH, shell=True)
	os.chdir("/usr/local/src/processing/build")
	# we could build Processing with a more recent Java version
	subprocess.check_call("ant linux-build", shell=True)
	# this also removes previous versions
	subprocess.check_call("rm -rf /usr/local/lib/processing*", shell=True)
	subprocess.check_call("mv linux/work /usr/local/lib/processing-" + PROCESSING_VERSION, shell=True)
	subprocess.check_call("chown root:root -R /usr/local/lib/processing-" + PROCESSING_VERSION, shell=True)
	subprocess.check_call("ln -sf processing-" + PROCESSING_VERSION + " /usr/local/lib/processing", shell=True)
	subprocess.check_call("ln -sf /usr/local/lib/processing/processing /usr/local/bin/processing", shell=True)
	subprocess.check_call("ln -sf /usr/local/lib/processing/processing-java /usr/local/bin/processing-java", shell=True)
	subprocess.check_call("mkdir -p /usr/local/share/applications", shell=True)
	subprocess.check_call("cp -f linux/processing.desktop /usr/local/share/applications", shell=True)
	# update .desktop file
	desktop = file_get_contents("/usr/local/share/applications/processing.desktop")
	desktop = re.sub('@version@', PROCESSING_VERSION, desktop)
	desktop = re.sub('/opt/processing', '/usr/local/lib/processing', desktop)
	file_put_contents("/usr/local/share/applications/processing.desktop", desktop)
	# inject nightly OpenJFX build (FX2D not working on Raspbian as of 3.0a9, stock or mesa)
	# this also copies a gstreamer-lite.so btw
	#subprocess.check_call("wget -q http://108.61.191.178/openjfx-8-sdk-overlay-linux-armv6hf.zip", shell=True)
	#subprocess.check_call("mkdir openjfx", shell=True)
	#os.chdir("/usr/local/src/processing/build/openjfx")
	#subprocess.check_call("unzip ../openjfx-8-sdk-overlay-linux-armv6hf.zip", shell=True)
	#subprocess.check_call("cp -rf jre/* /usr/local/lib/processing/java", shell=True)
	#os.chdir("/usr/local/src/processing/build")
	#subprocess.check_call("rm -rf openjfx*", shell=True)
	# copy the simplevideo library
	#subprocess.check_call("wget -q http://github.com/gohai/processing-simplevideo/archive/master.zip", shell=True)
	#subprocess.check_call("unzip master.zip", shell=True)
	#subprocess.check_call("mv processing-simplevideo-master /usr/local/lib/processing/modes/java/libraries/simplevideo", shell=True)
	#subprocess.check_call("rm -f master.zip", shell=True)
	# copy the test script
	subprocess.check_call("cp -f " + DATA_DIR + "/processing-test3d.* /home/pi", shell=True)
	subprocess.check_call("chown pi:pi /home/pi/processing-test3d.*", shell=True)
	if CLEANUP:
		subprocess.check_call("ant clean", shell=True)
	# this is currently not working for some reason
	issue['processing'] = getGitInfo()

def buildExtraProcessingVideo():
	if not os.path.exists("/usr/local/src/processing-video"):
		subprocess.check_call("git clone https://github.com/processing/processing-video.git /usr/local/src/processing-video", shell=True)
	os.chdir("/usr/local/src/processing-video")
	subprocess.call("git fetch", shell=True)
	subprocess.check_call("git checkout -f -B master origin/master", shell=True)
	subprocess.check_call("printf \"core.classpath.location=/usr/local/lib/processing/core/library\\ncompiler.classpath.location=/usr/local/lib/processing/java/mode\" > build.properties", shell=True)
	subprocess.check_call("ant build", shell=True)
	subprocess.check_call("mkdir -p /usr/local/lib/processing/modes/java/libraries/video", shell=True)
	subprocess.check_call("cp -fr examples library library.properties /usr/local/lib/processing/modes/java/libraries/video", shell=True)
	if CLEANUP:
		subprocess.check_call("ant clean", shell=True)
	issue['processing-video'] = getGitInfo()

def buildIssueJson():
	os.chdir(os.path.dirname(os.path.realpath(__file__)))
	issue['vc4-buildbot'] = getGitInfo()
	s = json.dumps(issue, sort_keys=True, indent=4, separators=(',', ': '))
	file_put_contents("/boot/issue-vc4.json", s)


checkRoot()
updateHostApt()
updateFirmware()
updateConfigTxt()
updateLdConfig()
enableCoredumps()
# not needed anymore?
#updateUdevGpioRule()
updateRcLocalForLeds()
enableDebugEnvVars()
# build Processing first since chances are that I screwed up somewhere
# XXX: workaround HTTP error
#buildExtraProcessing()
#buildExtraProcessingVideo()
# mesa and friends
buildXorgMacros()
buildXcbProto()
buildLibXcb()
buildGlProto()
buildLibDrm()
buildDri2Proto()
buildDri3Proto()
buildPresentProto()
buildLibXShmFence()
buildMesa()
# xserver and friends
buildXTrans()
buildXProto()
buildXExtProto()
buildInputProto()
buildRandrProto()
buildFontsProto()
buildLibEpoxy()
buildXServer()
# glxgears and friends
buildMesaDemos()
# xserver modules
buildLibEvdev()
buildInputEvdev()
buildGstreamer()
# build kernel last to minimize window where we would boot an
# untested kernel on power outage etc
buildLinux()

buildIssueJson()
