#!/usr/bin/env python

import os
import subprocess
import re

# XXX: handle changed git repo URLs
LINUX_GIT_REPO = "https://github.com/anholt/linux.git"
LINUX_GIT_BRANCH = "vc4-kms-v3d"
MESA_GIT_REPO = "git://anongit.freedesktop.org/mesa/mesa"
MESA_GIT_BRANCH = "master"
DATA_DIR = os.path.dirname(os.path.realpath(__file__))
MAKE_OPTS = "-j3"
CLEANUP = 1

def checkRoot():
	if os.geteuid() != 0:
		exit("You need to have root privileges to run this script")

# helper functions used in updateConfigTxt
def file_get_contents(fn):
		with open(fn) as f:
			return f.read()

def file_put_contents(fn, s):
		with open(fn, 'w') as f:
			f.write(s)

def updateConfigTxt():
	txt = file_get_contents("/boot/config.txt")
	added_comment = 0
	# set mask_gpu_interrupt0=0x400
	match = re.findall(r'^mask_gpu_interrupt0=(.*)$', txt, re.MULTILINE)
	if 0 < len(match):
		txt = re.sub(r'(^)mask_gpu_interrupt0=(.*)($)', r'\1mask_gpu_interrupt0=0x400\3', txt, 0, re.MULTILINE)
	else:
		txt = txt.strip() + "\n\n" + "# added for vc4 driver\n" + "mask_gpu_interrupt0=0x400\n"
		added_comment = 1
	# set avoid_warnings=1 to remove warning overlay
	match = re.findall(r'^avoid_warnings=(.*)$', txt, re.MULTILINE)
	if 0 < len(match):
		txt = re.sub(r'(^)avoid_warnings=(.*)($)', r'\1avoid_warnings=1\3', txt, 0, re.MULTILINE)
	else:
		if not added_comment:
			txt = txt.strip() + "\n\n" + "# added for vc4 driver\n"
		txt = txt + "avoid_warnings=1\n"
	file_put_contents("/boot/config.txt", txt)

def updateLdConfig():
	# this makes /usr/local/lib come before /{usr/,}lib/arm-linux-gnueabihf
	if not os.path.exists("/etc/ld.so.conf.d/01-libc.conf"):
		subprocess.check_call("mv /etc/ld.so.conf.d/libc.conf /etc/ld.so.conf.d/01-libc.conf", shell=True)
	subprocess.check_call("ldconfig")

def buildXorgMacros():
	subprocess.check_call("apt-get -y install autoconf", shell=True)
	if not os.path.exists("/usr/local/src/xorg-macros"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/util/macros /usr/local/src/xorg-macros", shell=True)
	os.chdir("/usr/local/src/xorg-macros")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)

def buildXcbProto():
	if not os.path.exists("/usr/local/src/xcb-proto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xcb/proto /usr/local/src/xcb-proto", shell=True)
	os.chdir("/usr/local/src/xcb-proto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)

def buildLibXcb():
	# needed to prevent xcb_poll_for_special_event linker error when installing mesa
	subprocess.check_call("apt-get -y install libtool libpthread-stubs0-dev libxau-dev", shell=True)
	if not os.path.exists("/usr/local/src/libxcb"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xcb/libxcb /usr/local/src/libxcb", shell=True)
	os.chdir("/usr/local/src/libxcb")
	subprocess.check_call("git pull", shell=True)
	# xorg-macros.m4 got installed outside of the regular search path of aclocal
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)

def buildGlProto():
	if not os.path.exists("/usr/local/src/glproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/glproto /usr/local/src/glproto", shell=True)
	os.chdir("/usr/local/src/glproto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)

def buildLibDrm():
	if not os.path.exists("/usr/local/src/libdrm"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/mesa/drm /usr/local/src/libdrm", shell=True)
	os.chdir("/usr/local/src/libdrm")
	subprocess.check_call("git pull", shell=True)
	# XXX: this also builds libraries for nouveau, radeon etc, which aren't needed
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)

def buildDri2Proto():
	if not os.path.exists("/usr/local/src/dri2proto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/dri2proto /usr/local/src/dri2proto", shell=True)
	os.chdir("/usr/local/src/dri2proto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)

def buildDri3Proto():
	# unavailable in raspbian
	if not os.path.exists("/usr/local/src/dri3proto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/dri3proto /usr/local/src/dri3proto", shell=True)
	os.chdir("/usr/local/src/dri3proto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)

def buildPresentProto():
	# unavailable in raspbian
	if not os.path.exists("/usr/local/src/presentproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/presentproto /usr/local/src/presentproto", shell=True)
	os.chdir("/usr/local/src/presentproto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)

def buildLibXShmFence():
	# unavailable in raspbian
	if not os.path.exists("/usr/local/src/libxshmfence"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/lib/libxshmfence /usr/local/src/libxshmfence", shell=True)
	os.chdir("/usr/local/src/libxshmfence")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)

def buildMesa():
	subprocess.check_call("apt-get -y install bison flex python-mako libx11-dev libx11-xcb-dev libxext-dev libxdamage-dev libxfixes-dev libudev-dev libexpat-dev gettext", shell=True)
	if not os.path.exists("/usr/local/src/mesa"):
		subprocess.check_call("git clone " + MESA_GIT_REPO + " /usr/local/src/mesa", shell=True)
	os.chdir("/usr/local/src/mesa")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("git checkout -f " + MESA_GIT_BRANCH, shell=True)
	# workaround https://bugs.freedesktop.org/show_bug.cgi?id=80848
	subprocess.call("mkdir /usr/lib/arm-linux-gnueabihf/tmp-libxcb", shell=True)
	subprocess.check_call("mv /usr/lib/arm-linux-gnueabihf/libxcb* /usr/lib/arm-linux-gnueabihf/tmp-libxcb", shell=True)
	subprocess.check_call("ldconfig", shell=True)
	# XXX: unsure if swrast is needed
	# XXX: this complains about libva missing at some point, but continues
	# XXX: Shader cache: no
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local --with-gallium-drivers=vc4 --enable-gles1 --enable-gles2 --with-egl-platforms=x11,drm --with-dri-drivers=swrast --enable-dri3", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	# undo workaround
	subprocess.check_call("mv /usr/lib/arm-linux-gnueabihf/tmp-libxcb/* /usr/lib/arm-linux-gnueabihf", shell=True)
	subprocess.check_call("rmdir /usr/lib/arm-linux-gnueabihf/tmp-libxcb", shell=True)
	subprocess.check_call("ldconfig", shell=True)

def buildXTrans():
	# xserver: Requested 'xtrans >= 1.3.5' but version of XTrans is 1.2.7
	if not os.path.exists("/usr/local/src/libxtrans"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/lib/libxtrans /usr/local/src/libxtrans", shell=True)
	os.chdir("/usr/local/src/libxtrans")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)

def buildXProto():
	# xserver: Requested 'xproto >= 7.0.26' but version of Xproto is 7.0.23
	if not os.path.exists("/usr/local/src/xproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/xproto /usr/local/src/xproto", shell=True)
	os.chdir("/usr/local/src/xproto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)

def buildXExtProto():
	# xserver: Requested 'xextproto >= 7.2.99.901' but version of XExtProto is 7.2.1
	if not os.path.exists("/usr/local/src/xextproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/xextproto /usr/local/src/xextproto", shell=True)
	os.chdir("/usr/local/src/xextproto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)

def buildInputProto():
	# xserver: Requested 'inputproto >= 2.3' but version of InputProto is 2.2
	if not os.path.exists("/usr/local/src/inputproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/inputproto /usr/local/src/inputproto", shell=True)
	os.chdir("/usr/local/src/inputproto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)

def buildRandrProto():
	# xserver: Requested 'randrproto >= 1.4.0' but version of RandrProto is 1.3.2
	if not os.path.exists("/usr/local/src/randrproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/randrproto /usr/local/src/randrproto", shell=True)
	os.chdir("/usr/local/src/randrproto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)

def buildFontsProto():
	# xserver: Requested 'fontsproto >= 2.1.3' but version of FontsProto is 2.1.2
	if not os.path.exists("/usr/local/src/fontsproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/fontsproto /usr/local/src/fontsproto", shell=True)
	os.chdir("/usr/local/src/fontsproto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)

def buildLibEpoxy():
	# xserver: needed for glamor, unavailable in raspbian
	if not os.path.exists("/usr/local/src/libepoxy"):
		subprocess.check_call("git clone https://github.com/anholt/libepoxy.git /usr/local/src/libepoxy", shell=True)
	os.chdir("/usr/local/src/libepoxy")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)

def buildXServer():
	subprocess.check_call("apt-get -y install libpixman-1-dev libssl-dev x11proto-xcmisc-dev x11proto-bigreqs-dev x11proto-render-dev x11proto-video-dev x11proto-composite-dev x11proto-record-dev x11proto-scrnsaver-dev x11proto-resource-dev x11proto-xf86dri-dev x11proto-xinerama-dev libxkbfile-dev libxfont-dev libpciaccess-dev libxcb-keysyms1-dev", shell=True)
	# without libxcb-keysyms1-dev compiling fails with "Keyboard.c:21:29: fatal error: xcb/xcb_keysyms.h: No such file or directory compilation terminated.
	if not os.path.exists("/usr/local/src/xserver"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/xserver /usr/local/src/xserver", shell=True)
	os.chdir("/usr/local/src/xserver")
	subprocess.check_call("git pull", shell=True)
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

def buildLibEvdev():
	# >= 0.4 needed for xf86-input-evdev
	if not os.path.exists("/usr/local/src/libevdev"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/libevdev /usr/local/src/libevdev", shell=True)
	os.chdir("/usr/local/src/libevdev")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)

def buildInputEvdev():
	# ABI major version on raspbian is 16 (vs. currently 22), so build evdev module
	subprocess.check_call("apt-get -y install libmtdev-dev", shell=True)
	if not os.path.exists("/usr/local/src/xf86-input-evdev"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/driver/xf86-input-evdev /usr/local/src/xf86-input-evdev", shell=True)
	os.chdir("/usr/local/src/xf86-input-evdev")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)

def buildLinux():
	# install dependencies
	subprocess.check_call("apt-get -y install bc", shell=True)
	if not os.path.exists("/usr/local/src/raspberrypi-tools"):
		subprocess.check_call("git clone https://github.com/raspberrypi/tools /usr/local/src/raspberrypi-tools", shell=True)
	os.chdir("/usr/local/src/raspberrypi-tools")
	subprocess.check_call("git pull", shell=True)
	# get up-to-date git tree
	if not os.path.exists("/usr/local/src/linux"):
		subprocess.check_call("git clone " + LINUX_GIT_REPO + " /usr/local/src/linux ", shell=True)
	os.chdir("/usr/local/src/linux")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("git checkout -f " + LINUX_GIT_BRANCH, shell=True)
	# compile for 2708
	subprocess.check_call("make clean", shell=True)
	subprocess.check_call("cp " + DATA_DIR + "/config-2708 .config", shell=True)
	# XXX: change localversion, document changes to raspbian original
	subprocess.check_call("make olddefconfig", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make " + MAKE_OPTS + " modules", shell=True)
	# XXX: remove old module versions
	subprocess.check_call("make modules_install", shell=True)
	subprocess.check_call("make bcm2835-rpi-b.dtb", shell=True)
	subprocess.check_call("cp arch/arm/boot/dts/bcm2835-rpi-b.dtb /boot/bcm2708-rpi-b.dtb", shell=True)
	subprocess.check_call("make bcm2835-rpi-b-plus.dtb", shell=True)
	subprocess.check_call("cp arch/arm/boot/dts/bcm2835-rpi-b-plus.dtb /boot/bcm2708-rpi-b-plus.dtb", shell=True)
	# this signals to the bootloader that device tree is supported
	subprocess.check_call("/usr/local/src/raspberrypi-tools/mkimage/mkknlimg --dtok arch/arm/boot/zImage arch/arm/boot/zImage", shell=True)
	subprocess.check_call("cp arch/arm/boot/zImage /boot/kernel.img", shell=True)
	subprocess.check_call("cp .config /boot/kernel.img-config", shell=True)
	# compile for 2709
	subprocess.check_call("make clean", shell=True)
	subprocess.check_call("cp " + DATA_DIR + "/config-2709 .config", shell=True)
	subprocess.check_call("make olddefconfig", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make " + MAKE_OPTS + " modules", shell=True)
	subprocess.check_call("make modules_install", shell=True)
	# there's currently no dt for 2709 in vc4-kms-v3d, so try without device tree support there
	#subprocess.check_call("/usr/local/src/raspberrypi-tools/mkimage/mkknlimg --dtok arch/arm/boot/zImage arch/arm/boot/zImage", shell=True)
	subprocess.check_call("cp arch/arm/boot/zImage /boot/kernel7.img", shell=True)
	subprocess.check_call("cp .config /boot/kernel7.img-config", shell=True)
	if CLEANUP:
		subprocess.check_call("make clean", shell=True)


# XXX: apt-get update?
# XXX: any benefits of using a later version of libdri? (https://github.com/robclark/libdri2.git)

checkRoot()
updateConfigTxt()
updateLdConfig()
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
# xserver modules
buildLibEvdev()
buildInputEvdev()
# build kernel last to minimize window where we would boot an
# untested kernel on power outage etc
# XXX: test order with vanilla Raspbian
buildLinux()

# XXX: issue.json
