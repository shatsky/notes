---
title: Workaround for Linux amdgpu reset bug for Polaris GPU
summary: Found workaround for irritating bug occuring in Linux VFIO setups with Polaris GPU passthrough
---

This is a copy of my post at https://www.reddit.com/r/VFIO/comments/enmnnj/trying_to_understand_amd_polaris_reset_bug/

DISCLAIMER: I'm not an expert in kernel programming/amdgpu/vfio/PCI architecture and may be wrong.

As many others here, I want to be able to switch between using my graphics card in Linux host and in Windows guest at wish. As many others, I run into "Unknown PCI header type '127'" error. I've noticed that:

- card fails only during VM launch
- card never fails if it has not been touched by amdgpu since host boot
- card never fails if amdgpu emitted "enabling device" message during last card init (which only happens when amdgpu grabs fresh card after host boot or remove-suspend-resume-rescan workaround)
- card always fails if amdgpu emitted "GPU PCI config reset" message during last card init (which happens on subsequent rebinds)
- vfio-pci emits several "reset recovery - restoring BARs" messages during VM launch every time the card fails and only then (these do not indicate device reset attempt by vfio-pci, see below); if ROM BAR is enabled, the well-known PCI header error appears for the first time at this point
- if VM launch succeeded, I can reboot/shutdown and launch it again without an issue, even if I shutdown it forcibly, even SIGKILL qemu process - as long as I prevent amdgpu from grabbing the card in the meanwhile

I've done many tests and tried to visualize observed regularities:

[State machine representation](https://preview.redd.it/ef9g6y3ynba41.png?width=546&format=png&auto=webp&s=ca1d24906a7ee5dcb43e1b7ba30925ae2f539b73)

I've studied kernel source to understand what happens behind mentioned messages. vfio-pci "reset recovery - restoring BARs" is emitted by the code which, according to comments, is meant to restore BARs if it's detected that device has undergone "backdoor reset". In practice, it is run when VM tries to enable memory or I/O access flag in card's PCI command register and copies values from vdev to backing pdev (real card's PCI config) registers if:

- this flag is enabled in vdev config but not in backing pdev
- any BAR value in vdev config does not match one in pdev, or if pdev one is not accessible

See vfio_basic_config_write(), vfio_need_bar_restore() and vfio_bar_restore() in drivers/vfio/pci/vfio_pci_config.c

amdgpu "GPU PCI config reset" is emitted by the code which writes value 0x39d5e86b to card's PCI config register at offset 0x7c (not defined as a named constant in the code but ~~is documented e. g. by Intel as ["Data PM Control/Status Bridge Extensions Power Management Status & Control"](https://www.intel.com/content/www/us/en/programmable/documentation/lbl1415230609011.html#nik1410564908773)~~ it's in the area of PCI capabilities linked list, for my card 0x7c happens to be "Device Capabilities 2" register of PCI Express Capability Structure, and writing to it doesn't seem to make sense, as all its bits are RO or HwInit; value is defined as AMDGPU_ASIC_RESET_DATA, probably vendor-specific). It is run if "SMC is already running" (sic) on init, which is checked by looking into some memory-mapped SMU registers (SMU and SMC are System Management Unit/Controller, part of AMD GPU SoC). See vi_need_reset_on_init() in drivers/gpu/drm/amd/amdgpu/vi.c, amdgpu_pci_config_reset() in drivers/gpu/drm/amd/amdgpu/amdgpu_device.c

As for "Unknown PCI header type '127'", it's 0xff, and if you dump PCI config of failed card, you see it's all-0xff. Actually, 0xffff in the first PCI config register (device ID) conventionally means that there's no device at this PCI address, so these bytes are probably coming from PCI bus controller which can no longer see the card.

So far I have more questions then answers:

- ~~is vfio-pci BARs recovery causing failure or is it another consequence of the common cause? ("background reset" looks like reference to amdgpu PCI config reset, but this might be coincidence, and restore might be triggered by PCI config suddenly becoming all-0xff, including command register access bits)~~ PCI bus reset causes failure
- ~~is this what devs call "reset bug" or something else with similar symptom? (inability to reset failed card is disappointing, but isn't the failure primary problem?)~~ it is and the name is valid, see above
- ~~why do people get exited about BACO reset or FLR, which require writing either to memory mapped or PCI config registers, when card's PCI config itself becomes inaccessible after the card fails like this?~~ because people failed to adapt amdgpu's vendor-specific "PCI config reset" for qemu; BACO is expected to depend less on amdgpu complexity; AMD implementing any reliable reset method in card's firmware and exporting it as FLR would allow qemu to use it and not need to have device-specific quirks in its codebase
- can at least card's prefail state be reliably detected to prevent launching VM? (I see that PCI config states after 1st unbind from amdgpu and subsequent unbinds are identical)

Maybe [/u/gnif2](https://www.reddit.com/user/gnif2/), [/u/aw___](https://www.reddit.com/user/aw___/) and agd5f could add something... I'm going to try tracing VM startup PCI accesses next week, hoping to find one after which card's config space becomes inaccessible. I also ask Polaris cards owners to comment if their experience is same or different as mine, with hardware specs and kernel version. Mine, for reference:

- MSI RX 470 Gaming X (AMDGPU_FAMILY_VI/CHIP_POLARIS10 as per amdgpu classification)
- Xeon E3 1225 v2
- ASRock H61M-DGS R2.0
- kernel 5.5-rc5

UPDATE 1: I've found out that qemu has AMD GPU specific reset code which it runs on VM startup. It had been ported from amdgpu when Hawaii was the latest one and doesn't run for Polaris. Besides, Hawaii is AMDGPU_FAMILY_CI and it's reset can have differences. I'm going to try to add AMDGPU_FAMILY_VI reset for Polaris to qemu and see if it helps.

UPDATE 2: here are the differences in qemu reset quirk which I've found:

- it uses offsets 0x80\*4=0x200 and 0x81\*4=0x204 for index and data MMIO regs to access SMC regs (for VI cards these were changed to 0x1ac\*4=0x6b0 and x1ad\*4=0x6b4, respectively)
- qemu-only step: before triggering PCI config reset itself (identical to VI one) it checks ixCC_RCU_FUSES 6th bit and conditionally flips ixRCU_MISC_CTRL 2nd bit to "Make sure only the GFX function is reset" (in amdgpu regs are defined but not used)
- qemu-only step: after PCI config reset it resets SMU via writing to ixSMC_SYSCON_RESET_CNTL and stops its clock via writing to ixSMC_SYSCON_CLOCK_CNTL_1 (in amdgpu regs are defined but not used)

I'm going to double check before going further, would be nice to have comments from AMD people about purpose of qemu-only steps and whether it's safe to only change these offsets for Polaris.

UPDATE 3: as Alex Williamson explained, card fails on PCI bus reset, which qemu tries by default; indeed, if you do it manually as described e. g. [here](https://unix.stackexchange.com/a/474378) card will fail if it's in prefail state and will not fail if it's not (but will preserve its state, i. e. will not return to upper state as depicted in the state machine graph in this post). ~~It should be noted, however, that Windows driver does not seem to bring the card into prefail state (card does not fail on PCI bus reset even after forced VM shutdown)~~ amdgpu also doesn't until it grabs previously touched card.

UPDATE 4: some of the assumptions in the beginning of the post are more limited then I expected, e. g. switching between host and Linux guest doesn't make the card fail. Will do more tests later.

UPDATE 5: **I CONFIRM THAT SWITCHING GPU BETWEEN HOST AND GUEST MULTIPLE TIMES IS POSSIBLE IF BUS RESET IS DISABLED.** This requires patching kernel to prevent bus reset which is triggered by qemu/vfio-pci, e. g. for my RX 470 I've added following to drivers/pci/quirks.c:

```
DECLARE_PCI_FIXUP_HEADER(0x1002, 0x67df, quirk_no_bus_reset);DECLARE_PCI_FIXUP_HEADER(0x1002, 0xaaf0, quirk_no_bus_reset);
```

Before starting the VM I do following:

- lock card's amdgpu device nodes from userspace access and kill running processes which are still using them (to prevent issues upon the next step)
- unbind the card from amdgpu (to prevent issues upon the next step)
- run `setpci -s 0000:01:00.0 7c.l=39d5e86b` to trigger the same reset mechanism which amdgpu uses (this is only applicable after the card has been initialized by amdgpu, which I always know about, therefore don't care about checking SMU state)

Script and patch: https://gist.github.com/shatsky/2c8959eb3b9d2528ee8a7b9f58467aa0

UPDATE 6: 2020-03-19, after months of active use, I've encountered kernel issue for the first time; interpreter got stuck in uninterruptible sleep executing script line

```
echo "$device_addr" > "/sys/bus/pci/drivers/amdgpu/unbind"
```

, probably waiting for write syscall to complete. No relevant kernel messages after usual `[drm] amdgpu: finishing device.`, the `driver` symlink and some amdgpu-dependent stuff in `/sys/bus/pci/devices/$device_addr` disappeared, but some remained. `modprobe -r amdgpu` got stuck as well, had to forcibly power off the system. Anyway this has nothing to do with reset bug, and reliability seems fine for home use.
