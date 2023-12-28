---
title:  If you REALLY need to boot Linux on a Windows machine and don't have any bootable media 
summary: Got laptop with Windows while traveling and had to find hacky way to boot Linux on it
---
You can boot Slax Linux from Windows NTFS partition using GRUB4DOS, not even touching the Windows bootsector. This HOWTO assumes that machine has a typical Windows 7 installation.

1. Download [GRUB4DOS](http://download.gna.org/grub4dos/?C=M;O=D), extract grldr.mbr and grldr to your C:\

2. Use bcdedit commandline tool to add GRUB4DOS to bootmgr:

```
> BCDEDIT.EXE /store C:\boot\BCD /create /d "Start GRUB4DOS" /application bootsector
< {guid}
> BCDEDIT.EXE /store C:\boot\BCD /set {guid} device boot
> BCDEDIT.EXE /store C:\boot\BCD /set {guid} path \grldr.mbr
> BCDEDIT.EXE /store C:\boot\BCD /displayorder {guid} /addlast
```

See http://diddy.boot-land.net/grub4dos/files/install_windows.htm for more details.

3. Download [Slax](https://www.slax.org/en/download.php) and extract slax directory to C:\

4. Create C:\menu.lst for GRUB4DOS menu and add menu item for booting Slax:

```
title slax
kernel /slax/boot/vmlinuz vga=normal load_ramdisk=1 prompt_ramdisk=0 rw printk.time=0 slax.flags=xmode,toram
initrd /slax/boot/initrfs.img
```
If you wonder where these boot parameters are from, Slax has a syslinux boot config C:\slax\boot\syslinux.cfg which defines a complex boot menu with toggleable options. There are several 'MENU BEGIN xxxxx' blocks, where first 4 menuname characters are 0 or 1, 1st one representing 'Persistent changes' option state, 2nd for 'Graphical desktop', 3rd for 'Copy to RAM' and 4th for 'Act as PXE server'. 5th character is 0...3, meaning nothing but a highlighted menu item number. I've chosen a variant with graphical desktop and copy-to-ram, so I'm using boot parameters from 'MENU BEGIN 01100' block:

```
KERNEL /slax/boot/vmlinuz
APPEND vga=normal initrd=/slax/boot/initrfs.img load_ramdisk=1 prompt_ramdisk=0 rw printk.time=0 slax.flags=xmode,toram
```

Note that grub syntax differs from syslinux one (inline kernel arguments, separate initrd line instead of kernel pseudo-argument).

Now you can choose 'Start GRUB4DOS' in Windows boot menu and 'slax' in GRUB4DOS menu to boot Slax.
