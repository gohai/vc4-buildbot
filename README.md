# vc4-buildbot

This script is designed to build the latest Kernel, Mesa and XServer packages, along with their dependencies from Git. After compilation the generated files are injected into a current Raspbian image, to be tested on a Raspberry Pi or Raspberry Pi 2.

## Modifying a local Raspbian installation

1. Download the latest [Raspbian](http://downloads.raspberrypi.org/raspbian_latest) and put it onto a SD or microSD card, depending on which version of the Raspberry Pi you want this to run on
2. In the initial setup screen (`raspi-config`) make sure to enlarge the filesystem, set the correct keyboard layout (the default is a British one), and enable the SSH server
3. Clone this repository onto your Pi by running `git clone https://github.com/gohai/vc4-buildbot.git`
4. Run the script by executing `sudo ./BuildRaspbianVc4.py`

## Generating/uploading a Raspbian image

To also create and upload an image file to a remote server make sure to:

5. Modify at least `UPLOAD_HOST`, `UPLOAD_USER`, `UPLOAD_KEY`, `UPLOAD_PATH` in `PackageRaspbianVc4.py`
6. Provide a private key file for use with the host you want to upload the file to (e.g. `sukzessiv-net.pem`, not part of the repository)
7. Make sure that your host is in the `known_hosts` file of the root user. This can be accomplished by running `sudo ssh` to connect to your host.
8. Install either screen and run the script by launching screen and then executing `sudo ./PackageRaspbianVc4.py` or consider setting up a cron job like this:
`00 21   * * *   root    /home/pi/vc4-buildbot/PackageRaspbianVc4.py`

## Output files

* `*-image.zip`: a zipped Raspbian image file, equivalent to the ones available from raspberrypi.org
* `*-issue.json`: a JSON encoded array containing information about all the packages used for the build, including the commit they were at when building (useful for bisecting). This file is also available at `/boot/issue.json`.
* `*-overlay.tar.bz2`: a tarball of files that can be added to a vanilla Raspbian image or installation. Make sure to run sudo ldconfig after initial bootup.
* `*-processing.tar.bz2`: a tarball of a recent build of Processing for ARM (alpha)
* `*-successs.log.bz2` or `*-error.log.bz2`: build log

Moreover, the kernel configuration used is available as `/boot/kernel.img-config` (Raspberry Pi), and `/boot/kernel7.img-config` (Raspberry Pi 2). The script does modify `/boot/config.txt` if needed.

## Testing on a Raspberry Pi

* Run `startx -- /usr/local/bin/Xorg`
* For troubleshooting, take a look at `dmesg` and `/usr/local/var/log/Xorg.0.log`.
