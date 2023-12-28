---
title: Notes about installing Debian/Ubuntu from other Linux distro with debootstrap
summary: Why need OS installer when there's booted Linux?
---
Existing guides are either incomplete, inaccurate or assume that the base system is Debian or Ubuntu: https://help.ubuntu.com/community/Installation/FromLinux#Without_CD

If you want to set it up manually, you can download the latest .tar.gz package from http://ftp.debian.org/debian/pool/main/d/debootstrap/ and run debootstrap from the source tree with DEBOOTSTRAP_DIR env variable. Note that it requires devices.tar.gz to be present in the same directory; you can either build it by running

```
make devices.tar.gz
```

or extract prebuilt one from debootstrap .deb package. Besides, it can require explicit arch and mirror URL in commandline, e. g.:

```
DEBOOTSTRAP_DIR=. ./debootstrap --arch=i386 vivid /mnt/installroot https://mirrors.kernel.org/ubuntu
```

Without the explicit URL it can attempt to get Release file from https://mirrors.kernel.org/debian even if an Ubuntu release (e. g. vivid) is specified.
All external dependencies are usually present in any Linux system, with the possible exception for Perl, which I installed in my live Slax [with no effort](https://www.slax.org/hi/modules.php?detail=perl) (you may also find the previous blogpost about booting Slax from the Windows partition without using removeable media useful).

If everything has been set up properly, debootstrap should succeed installing the base system and you can proceed with mounting, chrooting, basic configuration (remember to configure apt sources) and installing packages. You can find names of Ubuntu metapackages for installing the whole system at https://help.ubuntu.com/community/MetaPackages (although it misses several variants like lubuntu-core).
