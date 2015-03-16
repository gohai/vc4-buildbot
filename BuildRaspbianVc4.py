#!/usr/bin/env python

import os
import subprocess

# make sure to delete the directory when changing this
LINUX_GIT_REPO = "https://github.com/anholt/linux.git"
LINUX_GIT_BRANCH = "vc4-3.18"
DATA_DIR = os.getcwd()
MAKE_OPTS = "-j3"

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
	subprocess.check_call("make olddefconfig", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make " + MAKE_OPTS + " modules", shell=True)
	subprocess.check_call("make modules_install", shell=True)
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
	subprocess.check_call("/usr/local/src/raspberrypi-tools/mkimage/mkknlimg --dtok arch/arm/boot/zImage arch/arm/boot/zImage", shell=True)
	subprocess.check_call("cp arch/arm/boot/zImage /boot/kernel7.img", shell=True)
	subprocess.check_call("cp .config /boot/kernel7.img-config", shell=True)
	# clean up
	# XXX: flag
	subprocess.check_call("make clean", shell=True)

def changeLdConfig():
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
	subprocess.check_call("./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)

def buildXcbProto():
	if not os.path.exists("/usr/local/src/xcb-proto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xcb/proto /usr/local/src/xcb-proto", shell=True)
	os.chdir("/usr/local/src/xcb-proto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
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
	subprocess.check_call("./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
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
	if not os.path.exists("/usr/local/src/dri3proto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/dri3proto /usr/local/src/dri3proto", shell=True)
	os.chdir("/usr/local/src/dri3proto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)

def buildPresentProto():
	if not os.path.exists("/usr/local/src/presentproto"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/proto/presentproto /usr/local/src/presentproto", shell=True)
	os.chdir("/usr/local/src/presentproto")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	# has no make all, make clean
	subprocess.check_call("make install", shell=True)

def buildLibXshmfence():
	if not os.path.exists("/usr/local/src/libxshmfence"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/lib/libxshmfence /usr/local/src/libxshmfence", shell=True)
	os.chdir("/usr/local/src/libxshmfence")
	subprocess.check_call("git pull", shell=True)
	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	subprocess.check_call("make clean", shell=True)
	subprocess.check_call("ldconfig", shell=True)

# not needed
#def buildLibX11():
#	subprocess.check_call("apt-get -y install x11proto-xext-dev xtrans-dev x11proto-kb-dev x11proto-input-dev", shell=True)
#	if not os.path.exists("/usr/local/src/libx11"):
#		subprocess.check_call("git clone git://anongit.freedesktop.org/xorg/lib/libX11 /usr/local/src/libx11", shell=True)
#	os.chdir("/usr/local/src/libx11")
#	subprocess.check_call("git pull", shell=True)
#	subprocess.check_call("ACLOCAL_PATH=/usr/local/share/aclocal ./autogen.sh --prefix=/usr/local", shell=True)
#	subprocess.check_call("make " + MAKE_OPTS, shell=True)
#	subprocess.check_call("make install", shell=True)
#	subprocess.check_call("make clean", shell=True)
#	subprocess.check_call("ldconfig", shell=True)

def buildMesa():
	subprocess.check_call("apt-get -y install bison flex python-mako libx11-dev libx11-xcb-dev libxext-dev libxdamage-dev libxfixes-dev libudev-dev libexpat-dev gettext", shell=True)
	if not os.path.exists("/usr/local/src/mesa"):
		subprocess.check_call("git clone git://anongit.freedesktop.org/mesa/mesa /usr/local/src/mesa", shell=True)
	os.chdir("/usr/local/src/mesa")
	subprocess.check_call("git pull", shell=True)
	# workaround https://bugs.freedesktop.org/show_bug.cgi?id=80848
	subprocess.check_call("mkdir /usr/lib/arm-linux-gnueabihf/tmp-libxcb", shell=True)
	subprocess.check_call("mv /usr/lib/arm-linux-gnueabihf/libxcb* /usr/lib/arm-linux-gnueabihf/tmp-libxcb", shell=True)
	subprocess.check_call("ldconfig", shell=True)
	# XXX: unsure if swrast is needed
	# XXX: this complains about libva missing at some point, but continues
	# XXX: Shader cache: no
	subprocess.check_call("./autogen.sh --prefix=/usr/local --with-gallium-drivers=vc4 --enable-gles1 --enable-gles2 --with-egl-platforms=x11,drm --with-dri-drivers=swrast --enable-dri3", shell=True)
	subprocess.check_call("make " + MAKE_OPTS, shell=True)
	subprocess.check_call("make install", shell=True)
	subprocess.check_call("make clean", shell=True)
	subprocess.check_call("mv /usr/lib/arm-linux-gnueabihf/tmp-libxcb/* /usr/lib/arm-linux-gnueabihf", shell=True)
	subprocess.check_call("rmdir /usr/lib/arm-linux-gnueabihf/tmp-libxcb", shell=True)
	subprocess.check_call("ldconfig", shell=True)

# XXX: check root?

buildLinux()
# XXX: config.txt

changeLdConfig()

buildXorgMacros()
buildXcbProto()
buildLibXcb()
buildGlProto()
buildLibDrm()
buildDri2Proto()
buildDri3Proto()
buildPresentProto()
buildLibXshmfence()
buildMesa()
