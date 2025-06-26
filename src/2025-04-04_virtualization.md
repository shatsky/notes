---
title: Virtualization notes
summary: Generic notes mostly about recurring issues with running Windows guest on Linux amd64 host with libvirt/KVM stack
---

Linux virtualization stack:
- virt-manager: "VM manager and viewer" GUI app which acts as frontend for libvirt (allowing to create/configure/list/start/stop/delete VMs) and qemu (allowing to view running VMs and interact with them)
- libvirt: service which allows to manage VMs using XML descriptions (which are translated to qemu cmdline, also it acts as supervisor for qemu processes of running VMs)
- qemu (qemu-kvm): userspace app which emulates virtual PC (using underlying kernel and hardware features for acceleration) and provides APIs to pass input (incl. kb&mouse) and capture output (incl. display)
- KVM subsystem in kernel, providing /dev/kvm
- Intel VT-x/VT-d/AMD processor virtualization extensions

Note: processor virtualization extensions are often disabled by default in firmware, and virt-manager doesn't notify about it during VM creation, instead it silently creates VM which uses software virtualization known as "QEMU TCG" (as opposed to KVM which requires hardware support, can be seen in UI in "virtual hardware details" window/"overview" tab/"Hypervisor Detail"/"Hypervisor"), which works painfully slow and with issues with Windows guest

# VirtIO devices and drivers, SPICE

By default new libvirt VM invokes qemu with options to emulate some real ancient devices such as storage/network/graphics/etc. controllers, for which typical OS like Windows has drivers included, but this emulation has significant overhead. VirtIO is "family" of "minimal overhead" virtual devices, "emulation" of which  is basically reduced to minimal nessessary communication with respective host OS subsystems, but this requires custom drivers in guest OS.

https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso ( https://github.com/virtio-win/virtio-win-pkg-scripts/blob/master/README.md )

https://pve.proxmox.com/wiki/Windows_VirtIO_Drivers#Using_the_ISO

`virtio-win-gt-x64.msi` is VirtIO drivers package for Windows x64, currently including:
- balloon
- network
- pvpanic
- fwcfg (FWCfg)
- qemupciserial
- vioinput
- viorng
- vioscsi (SCSI passthrough)
- vioserial
- viostor (block)
- viofs
- viogpudo (GPU DOD)
- viomem

## Switching storage from SATA to VirtIO

## SPICE

SPICE is the protocol which is used by VM viewer for interacting with VM. Typically guest OS itself knows nothing about it, additional "SPICE agent" guest software is needed for integration with host, giving such possibilities as:
- clipboard sharing
- drag-and-drop between guest and host
- auto adjusting guest resolution to host VM viewer window size (note: virt-manager requires additional setting to enable sending resolution setting request to guest: View->Scale display->auto resize VM with window)

`virtio-win-guest-tools.exe` from same ISO image installs "QEMU Guest Agent" and "SPICE agent"

https://en.wikipedia.org/wiki/Simple_Protocol_for_Independent_Computing_Environments

https://www.spice-space.org/spice-for-newbies.html

# Windows specific optimizations

There are many guides of performance optimization but they usually miss good explanation of what and why.

https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/configuring_and_managing_windows_virtual_machines/optimizing-windows-virtual-machines

# Other

To make virt-manager request guest OS to resize its SPICE display device resolution to match current VM display presentation area in 

Currently virt-manager has bug which causes VM display zoomed out with Wayland backend in Wayland env with display scaling, I force x11 backend via `GDK_BACKEND=x11` env var.
