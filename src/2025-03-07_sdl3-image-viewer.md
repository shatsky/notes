---
title: SDL3 image viewer development notes
summary: Notes about development of https://github.com/shatsky/lightning-image-viewer
---

Notes which might be useful for someone who might want to get into the project.

Project chronology:
- 2021 created prototype with SDL2. Published on github but did not try to promote, though I was using it as my primary image viewer since then. Window transparency only worked with X11 with my patch for SDL which I didn't try to upstream
- 2024 resumed work, partly inspired by news about upcoming SDL3 release with good cross-platform support for transparent windows. Switched to SDL3, released 0.1, created 1st post on reddit about it 1st time, mostly to check that there are still no other projects with similar UI/UX possibly obsoleting it
- 2025-early-summer added EXIF support via libexif, released 0.2.0 (initially targeted Ubuntu 25.10 release day because it shipped with SDL3, missed it ofc), promoted on several websites, got some feedback
- 2025-mid-summer added HEIC support via libheif, released 0.3.0
- 2025-late-summer implemented animation playback with SDL_image IMG_Animation, wanted to release 0.4.0 but never did
- 2025-autumn started learning Rust, learnt that Rust image-rs is good and relatively easy to plug in instead of SDL_image, switched to it, released 0.5.1

# Rewrite in Rust

What? Yes.

Rust already has 2 very mature components fitting the project well:
- image-rs: "the" Rust image decoding library
- winit: "the" Rust window library. Corresponds to SDL window and event APIs. Doesn't handle drawing

As for drawing/rendering, I haven't found mature equivalent to SDL Render API ( https://wiki.libsdl.org/SDL3/CategoryRender ). There's wgpu (used, among others, by Firefox and indirectly by Cosmic desktop), but it's much closer to Vulkan than to simple "throw this rect of texture into that rect of window".

Migration plan:
- (done) move to image-rs for image decoding; with everything else written in C and image-rs being Rust library with no C API, this requires writing FFI for it; but app only needs few functions to decode still and animated images
- rewrite app itself in Rust, using sdl3-rs to call SDL3
- (maybe) move to winit for window and event handling, leaving SDL3 for rendering
- (maybe) move to some Rust rendering lib

https://xkcd.com/3164/ "When switching to metric, make the process easier by doing it in steps"

## Rust and runtime code sharing

My first thought was to enter Nix env with Rust libs which I wanted to use; I immediately found out that NixOS does not provide Nix libs as nixpkgs units, as typical Rust libs are not designed to be built as standalone binaries like C shared libs or Python modules; Cargo expects that concrete versions of deps are specified in project config, and builds them for project, statically linking all code built from Rust src.

Split into [2025-12-22_runtime-code-sharing-rust.html](2025-12-22_runtime-code-sharing-rust.html)

## Rust and Nix

Cargo default build time deps fetching conflicts with Nix deterministic offline build sandbox. Nix solves this with its "rustPlatform.buildRustPackage" which, given Cargo.lock, fetches all Rust deps separately before entering sandbox and sets env vars to make Cargo work offline and use pre fetched deps.

## image-rs

- flow: get decoder -> read metadata -> try to decode as animation, getting frame iter -> get frames or, if failed to get iter, decode as still image
- no generic animation decoding API yet ( https://github.com/image-rs/image/issues/2360 ); reader.into_decoder() returns decoder as `dyn ImageDecoder`, but animation decoding is done via other trait AnimationDecoder, which is implemented only by some decoders (gif, png, webp) and can't be used via `dyn ImageDecoder` even via casting to concrete decoder type because it's boxed; current solution is to check detected format via `reader.type()` and then instantiate decoder via `<concrete_decoder_type>::new(reader.into_inner())` if decoder of detected format implements trait AnimationDecoder; then pass decoder as `dyn ImageDecoder` and, when needed, check concrete type and cast to it
- no inner support for JXL and HEIC; however there's plugin support and `jxl-oxide` and `libheif-rs` provide hooks

# SDL generic stuff

## Window size and position

Surprisingly, there seems to be a problem with creating maximized non-fullscreen window with exactly maximum size allowed by shell on the "current" display. `SDL_CreateWindow()` requires explicit width and height. Options:
- `SDL_GetDesktopDisplayMode()`: get full height and width, including shell UI
- `SDL_GetDisplayUsableBounds()`: get rectangle representing usable (not used by shell UI) area of the display in global coordinate system of multi-display setup; this seems to produce incorrect results on Plasma Wayland

`SDL_GetCurrentDisplayMode()` is NOT about "current display", it's about "current mode" for fullscreen apps switching display mode on platforms which support this, not relevant at all. All these functions require display id; however there seems to be no control over on which display new window is displayed. SDL2 SDL_CreateWindow() used to accept position x, y allowing to position it in top right corner of specific display in multi display setup with values from `SDL_GetDisplayUsableBounds()`; however SDL3 `SDL_CreateWindow()` doesn't have these args anymore

There seems to be no "current display from user perspective" concept (I'd define it as "display on which top left corner of currently active window is when `SDL_CreateWindow()` is called") and no way to get it

For now, I call `SDL_CreateWindow()` with w and h from SDL_GetDesktopDisplayMode() called with display id from SDL_GetPrimaryDisplay(), which works acceptable with single display, haven't tested in multi display setup yet.

## HiDPI and scaling

Desktop environments have scaling to make UI items look larger than some "default size". It is often enabled on HiDPI displays. It can affect program in 2 ways:
- make rendered window contents displayed scaled
- make queried coords and sizes reported in "scaled pixels"
Normally both do happen and I need to prevent both from happening to have pixel perfect rendering with consistent input handling.

For now I set `SDL_HINT_VIDEO_WAYLAND_SCALE_TO_DISPLAY` 1; it's Wayland-specific quirk which is discouraged from being used in docs, but it seems to work well on Plasma Wayland, and on Windows both displaying and reporting seems to be unscaled for "HiDPI/scaling-unaware" apps by default

SDL3 "proper way to write HiDPI aware apps" is described in https://wiki.libsdl.org/SDL3/README-highdpi , however (at least on Plasma Wayland) setting window flag `SDL_WINDOW_HIGH_PIXEL_DENSITY` only prevents displaying scaling, while reporting remains scaled, requiring additional calls like `SDL_ConvertEventToRenderCoordinates()` to get values in "physical pixels", which makes no sense for me; I think that sane approach would be to save single switch (like `SDL_HINT_VIDEO_WAYLAND_SCALE_TO_DISPLAY` but platform agnostic)

# Linux

Makefile can be seen as convenient encapsulation of project-specific build commands. Initially I thought that for simple project built with single gcc command even Makefile is not needed, but both people and packaging systems widely assume that `make && make install` is default thing.

I've used Suckless as reference for project Makefile. It has 2 typical vars:
- DESTIR: tmp dir to install to from which it will be copied by pkg manager to "hierarchy root" (make is normally run with limited privileges in sandboxed build env and final destination is not available or readonly); on Nix it's `$out`
- PREFIX: subdir under "hierarchy root"; on "traditional" Linux distros for non-critical software it's /usr, on Nix /

## Nix flakes

Commands to update flake lock to nixpkgs rev which host currently uses and test flake:

`nixos-version --json` (prints nixpkgsRevision)

`nix --extra-experimental-features 'nix-command flakes' flake lock --override-input nixpkgs github:NixOS/nixpkgs/{nixpkgsRevision}`

`nix --extra-experimental-features 'nix-command flakes' run .`

To run from github:

`nix --extra-experimental-features 'nix-command flakes' run github:shatsky/lightning-image-viewer`

# Windows

## Cross building for Windows on NixOS Linux

Note: deprecated, for now I do it via GitHub Actions, locally with act, see relevant section

This is how I manually built Windows binary on NixOS:
- env with x86_64-w64-mingw32-gcc: `nix-shell -p pkgsCross.mingwW64.pkgsBuildHost.gcc`
- download and extract https://github.com/libsdl-org/SDL/releases/download/preview-3.1.6/SDL3-devel-3.1.6-mingw.tar.gz and https://github.com/libsdl-org/SDL_image/releases/download/preview-3.1.0/SDL3_image-devel-3.1.0-mingw.zip
- convert icon to .ico: `magick share/icons/hicolor/scalable/apps/lightning-image-viewer.svg lightning-image-viewer.ico`
- build .o with icon: `x86_64-w64-mingw32-windres src/viewer.rc icon.o`
- build .exe: `x86_64-w64-mingw32-gcc src/viewer.c icon.o -ISDL3-3.1.6/x86_64-w64-mingw32/include -ISDL3_image-3.1.0/x86_64-w64-mingw32/include -LSDL3-3.1.6/x86_64-w64-mingw32/lib -LSDL3_image-3.1.0/x86_64-w64-mingw32/lib -l:libSDL3.dll.a -l:libSDL3_image.dll.a -mwindows -o lightning-image-viewer.exe`
- download and extract https://github.com/libsdl-org/SDL_image/releases/download/preview-3.1.0/SDL3_image-devel-3.1.0-VC.zip (because mingw build is built without "optional formats" support incl. WebP)
- put SDL3-3.1.6/x86_64-w64-mingw32/bin/SDL3.dll , ~~SDL3_image-3.1.0/x86_64-w64-mingw32/bin/SDL3_image.dll~~ SDL3_image-3.1.0/lib/x64/SDL3_image.dll and SDL3_image-3.1.0/lib/x64/optional/*.dll in same dir with .exe

Note: I guess mixing DLLs built with mingw and VC in single process is not safe in general, but for SDL3 which is written in C and has stable ABI it should be fine and seems to work without issues, correct me if I'm wrong

Note: it might be possible to have unified Nix expr for cross building without using pre-built SDL, but ~~`pkgsCross.mingwW64.SDL2_image` currently fails to build (seems that most pkgs are broken for mingwW64, though SDL2 itself builds successfully)~~ might return to this after stable SDL3 version is released and added to nixpkgs

Note: nixpkgs has concept of 3 platforms:
- "buildPlatform" (on which program is to be built, i. e. on which Nix runs)
- "hostPlatform" (on which built program is to be executed)
- "targetPlatform" (for which built program emits code, only relevant for compilers)

On x86_64 NixOS:
- for any pkg, buildPlatform is "x86_64-linux" (overriding it doesn't make sense)
- for "usual" pkgs (which are to be executed on same platform), hostPlatform is also "x86_64-linux"
- for pkgs in `pkgsCross.mingwW64` set, hostPlatform is "x86_64-w64-mingw32"
- for pkgs in `pkgsCross.mingwW64.pkgsBuildHost` set, hostPlatform is "x86_64-linux", targetPlatform is "x86_64-w64-mingw32" (`pkgs<host><target>` pkgs sets have overridden "host" and "target" platforms, in case of `pkgsBuildHost` hostPlatform -> buildPlatform, targetPlatform -> hostPlatform)

Note: "x86_64-w64-mingw32" and "x86_64-linux" are "target triplets" describing target for which compiler produces binary, see https://wiki.osdev.org/Target_Triplet

## Mingw "Thread model"

`x86_64-w64-mingw32-gcc -v`

Currently on Ubuntu 25.04 with gcc v13, libs with "win32" threading model are in `/usr/lib/gcc/x86_64-w64-mingw32/13-posix/`, libs with "posix" threading model are in `/usr/lib/gcc/x86_64-w64-mingw32/13-posix/`

## Windows encodings

By default Windows uses some mess of UTF16 and single byte encodings. For graphical program which has main() as entry point, argv is provided in single byte encoding which is chosen as "ANSI codepage", such as CP1251, causing issues with cross platform libraries which expect UTF8. Simplest way I found to force Windows to just use UTF8 everywhere for app is manifest as described in https://github.com/alf-p-steinbach/C---how-to---make-non-English-text-work-in-Windows/blob/main/how-to-use-utf8-in-windows.md

## Windows "antivirus"

Windows "antivirus" nowadays often blocks unknown unsigned binaries which are not yet in some trusted binaries db after having been downloaded and run by thousands of users, claiming it contains "Trojan/Wacatac.B!ml" or similarly named malware. Nobody knows for sure what this even means, but many claim that "!ml" suffix means it's AI detection.

## C file and directory I/O, Windows, POSIX and glibc

Surprisingly for me being used to "just use whatever glibc provides", "ISO C standard library" has file I/O but no directory I/O API at all (are there platforms which have filesystem without directory concept?). glibc (and other libc implementations for POSIX systems) implements ISO C standard library with POSIX extensions including POSIX directory I/O. However mingw gcc uses not glibc but Microsoft C runtime (msvcrt/ucrt) which doesn't have (most of?) POSIX extensions; native Windows software is expected to use Win32 API fileapi.h `FindFirstFile()`/`FindNextFile()`/`FindClose()`; mingw provides subset of POSIX implemented with these, but fairly incomplete, it misses `scandir()` among others which I needed to iterate image files sorted by mtime.

Another surprising discovery was that struct `dirent` which represents directory entry in POSIX directory I/O API is allowed to "overflow" its declared size; it's last member `dirent.d_name`, declared as char array of some impl-decided size, can "hold" longer \0-terminated str than its size allows. Implementations allocate mem of appropriate size for `dirent` to "safely" hold its data with this "overflow". It's often referred as case of "Flexible array member", but "Flexible array member" seems to be about allowing declaring last member of struct as array without specified size at all (treated by sizeof() as size of 0), while glibc seems to declare `d_name` as array of size 1.

## Publishing in Windows Store

Flow:
- build Windows binaries
- package into MSIX pkg
- on Microsoft Partner Center app product page, upload MSIX (if it has same version and arch as already uploaded and validated one, latter has to be deleted first)
- submit update for certification

Managed via https://partner.microsoft.com/en-us/dashboard/account/v3/overview

Microsoft Partner Center reuses Microsoft account but can require additional checks. Microsoft tried to force me to add phone number and rejected UA one with reason something about sending auth SMS not supported for the country, eventually I went through https://developer.microsoft.com/en-us/microsoft-store/register "Create a developer account" blue button below and it worked (or did they just fix that?). Also forced to use mobile phone for document verification, but that worked well with Google Chrome on AOSP Android. "Publisher name" can be changed at https://partner.microsoft.com/en-us/dashboard/account/v3/organization/legalinfo#developer Contact Info -> Update, there's warning stating that apps will have to be re-submitted with new name.

Packages are uploaded in MSIX format. Seems that Microsoft considers its tool implementation as source of truth about MSIX format. It also provides subset as cross platform https://github.com/microsoft/msix-packaging which is semi abandoned and underdocumented, but useable to create MSIX on Linux from directory containing app files and manifest AppxManifest.xml. Despite what Microsoft pages tell, on Linux it has to be build with `./makelinux --pack`, which will produce makemsix executable with packaging support, which has to be used like `.vs/bin/makemsix pack -d /path/to/dir/with/app/files -p /path/to/package/file.msix`

MSIX is basically ZIP archive with app files + AppxManifest.xml + few other metadata files generated by packaging tool

Semi complete guide for manually writing `AppxManifest.xml`: https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-manual-conversion
Full schema reference: https://learn.microsoft.com/en-us/uwp/schemas/appxpackage/uapmanifestschema/schema-root
- https://learn.microsoft.com/en-us/uwp/schemas/appxpackage/uapmanifestschema/element-identity despite all examples, in "Publisher" only "CN" seems really needed
- must append `, OID.2.25.311729368913984317654407730594956997722=1` to allow installing unsigned MSIX via `Add-AppxPackage -AllowUnsigned` on Win11
- despite docs claiming that version major number can't be 0, it can; I use x.y.z app versioning, and assume a=x, b=y, c=z in MSIX a.b.c.d, d possibly used for numbering MSIX packaged from same app build

msix-packaging makemsix produces unsigned MSIX. Internet is full of non working suggestions how to install it. On Win10 it seems practically impossible, on Win11 it's enough to pkg with `OID.2.25.311729368913984317654407730594956997722=1` in Identity/Publisher and then run `Add-AppxPackage -AllowUnsigned -path path/to/pkg.msix` in admin powershell

Docs claim that Windows Certification Kit has to be used to test locally before submitting. Probably doesn't matter if app is not doing anything "unusual", but ok. It's now installed via Windows SDK installer which can be downloaded from https://learn.microsoft.com/en-us/windows/apps/windows-sdk/downloads . Usage is described here: https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit . In `appcert.exe test -packagefullname [package full name] -reportoutputpath [report file name]`, `[package full name]` I got as installed (from MSIX) apps parent dir name via process manager, `[report file name]` is any writeable filepath with filename ending with .xml .

# Emscripten

It's cool to provide app demo on app webpage, right?

Emscripten is solution which allows to compile C code to WASM and run it in browser. It includes emcc compiler which is basically drop-in replacement for gcc and runtime which emulates basic POSIX OS (including filesystem access, backed by MEMFS) and provides means for interop with webpage JS/HTML (including access to HTML canvas as framebuffer with harware accelerated graphics APIs supported by browser). Using latter requires support from app side, but I've noticed that SDL3 implements it, supporting Emscripten as another platform and allowing to build and run unmodified SDL3 app (at least if it only relies on basic SDL3 and POSIX APIs), and decided this hangs low enough to reach for.

However, Emscripten doesn't seem to care much about scenario "run unmodified/Emscripten-unaware app and control it from webpage JS"; they believe that app code must be aware and in control of webpage, not vice versa. Even with SDL3 Emscripten support this causes problems, but nothing showstopping.

## Building app

Generic build sequence is like:

Note: things related to SDL_image are deprecated

```
# build SDL
cd /path/to/SDL3
mkdir build
cd build
emcmake cmake ..
emmake make -j4

# build SDL_image
cd /path/to/SDL3_image
# fetch dependencies for extra image formats support (clones git repos)
sh external/download.sh
mkdir build
cd build
emcmake cmake .. -DSDL3_DIR=/path/to/SDL3/build -DSDLIMAGE_JXL=ON 
emmake make -j4

# build app
cd /path/to/app
# this will produce a.out.js (which has to be included in webpage) and a.out.wasm (which is loaded and executed by a.out.js)
emcc -I/path/to/SDL3/include -I/path/to/SDL3_image/include -L/path/to/SDL3/build -L/path/to/SDL3_image/build -lSDL3 -lSDL3_image -sEXPORTED_RUNTIME_METHODS="['callMain']" -sASYNCIFY -sEXIT_RUNTIME=1 -sALLOW_MEMORY_GROWTH app.c
```

## Webpage aka HTML Shell

The term "HTML Shell" again emphasizes that Emscripten crew considers Emscripten app to be the one in control.

To run Emscripten SDL app, it's basically enough for webpage to contain `<canvas id="canvas">` (SDL Emscripten backend looks for this id by default) and `<script src="/path/to/index.js">` (generated by emcc). However if one wants to change default Emscripten behavior, one has to add JS which creates `Module` object with overrides before including index.js

## Starting app

By default if you include Emscripten index.js it just starts app immediately. I wanted to delay it until user selects file using HTML input, and then provide file path as cmdline arg. Solution:
- app needs to be compiled with emcc option `-sEXPORTED_RUNTIME_METHODS="['callMain']"`
- `Module.callMain([arg])`

## Restarting app

By default Emscripten doesn't seem to provide any means to track the moment when app exits from webpage JS code. If built with emcc option `-sEXIT_RUNTIME=1` it causes runtime exit upon app exit and calls `Module.onExit()` callback. I ended up with this and reloading webpage via `Module.onExit()` callback

## Canvas size

Somewhy I assumed initially that canvas is treated as display and its size should be display mode. I was surprised that it was resized to 960x540 upon app start no matter what I did. Finally I went to SDL3 and Emscripten source code and understood what is happening: SDL3 Emscripten backend doesn't get display mode from canvas size, it calls Emscripten `emscripten_get_screen_size()` which gets JS screen.width and screen.height. I have no idea why Firefox reported 960x540 on my 1280x1080 display, perhaps a bug, but it did; then, when my app code requests window with these values, SDL3 Emscripten backend resizes canvas. I ended up with overriding screen.with and screen.height to canvas size.

Another problem was that in fullscreen SDL3 Emscripten backend triggers actual browser fullscreen, stretching fixed-size canvas, which causes blurriness and black bars; I ended up with overriding handlers to prevent enabling actual browser fullscreen, i. e. just treating canvas as display

## Memory limits

By default Emscripten app seems to be limited to only 17MiB of memory, which usually isn't enough, causing app termination when it tries to allocate more:
```
Uncaught RuntimeError: Aborted(Cannot enlarge memory arrays to size 20746240 bytes (OOM). Either (1) compile with -sINITIAL_MEMORY=X with X higher than the current value 17039360, (2) compile with -sALLOW_MEMORY_GROWTH which allows increasing the size at runtime, or (3) if you want malloc to return NULL (0) instead of this abort, compile with -sABORTING_MALLOC=0)
```

This limitation can be disabled with emcc option `-sALLOW_MEMORY_GROWTH`

# Image formats notes

## JPEG, JIF, JFIF, EXIF and TIFF

- JPEG standard defines 2 formats:
  - JIF "JPEG Interchange Format", basic JPEG file format starting with SOI (Start of Image), ending with EOI (End of Image) and generic definition of embedding generic "APPn" "application segments" along with image data between SOI and EOI
  - JFIF "JPEG File Interchange Format", "improved" JPEG file format based on JIF with specific "JFIF APP0" application segment (marker `\xff\xe0`) following SOI
- TIFF is another image file format which is much more complex than JIF/JFIF; TIFF file is something like archive, consisting of "TIFF directories", which include "TIFF tags", allowing to contain multiple images in different formats (incl. JPEG). TIFF is rarely used as standalone file format nowadays, but commonly used as embedded file format because of EXIF.
- EXIF is simultaneously metadata, file, TIFF and JPEG format. What? Yes.
  - EXIF acronym stands for "Exchangeable Image File Format"
  - EXIF standard defines EXIF metadata format which is based on TIFF, one can say it's basically TIFF intended to be embedded in other files; "almost TIFF" because it misses some tags which are mandatory in valid TIFF file; but otherwise it is fully compatible with TIFF and can be parsed with tiffdump tool from libtiff project. But can't be parsed with libtiff, because its external API functions necessarily trigger checks for those mandatory tags and libtiff doesn't provide any means to skip them. Anyway libtiff seems to have very poor security reputation and virtually all big software seems to use either libexif or exiv2 for parsing EXIF metadata
  - EXIF standard defines another JPEG file format which is also based on JIF and is similar to JFIF but, unlike JFIF, it requires that after SOI there is "APP1" segment (marker `\xff\xe1`) with embedded EXIF metadata. This EXIF JPEG file format is called... EXIF, of course (suggesting that writing of EXIF standard was started with the intention to produce just it, but then it got out of control)
  - EXIF standard also defines TIFF file format with embedded EXIF metadata (which is, again, "almost TIFF" itself)
  - EXIF standard also defines WAV audio file format with embedded EXIF metadata... Yes, "Image File Format" audio format
  - many other multimedia formats themselves define embedding of EXIF metadata

So, any JPEG is valid JIF; many JPEGs are also either valid JFIF or EXIF (file format); many JPEGs contain EXIF metadata, but not always embedded as specified in EXIF (file format) spec

## EXIF orientation tag

Note: things related to libexif are deprecated, exif orientation is obtained via image-rs

EXIF metadata is mostly relevant in scope of image viewer development because of its orientation tag and its usage in JPEG. It's not uncommon that image pixmap is encoded in different orientation then it's supposed to be displayed, usually as result of camera being rotated when taking photo. For lossless image formats like PNG it's no problem to re-encode pixmap with corrected orientation, but for lossless image formats like JPEG re-encoding usually causes loss of quality. Therefore, common solution is to add metadata with some "orientation tag" which tells viewer to apply transformation to pixmap after decoding it before displaying it. Some newer lossy image formats have it defined in the format itself, but JPEG historically relies on EXIF one, and common JPEG decoders incl. libjpeg don't decode EXIF metadata, leaving this task up to app.

Tag values and decoded pixmap->view transformations seen as decoded pixmap mirroring (n/y) and rotation (1/4 turns clockwise):
- 1: n, 0
- 2: y, 0
- 3: n, 2
- 4: y, 2 (or flip vertical)
- 5: y, 3 (or rotate 1/4 and flip horizontal)
- 6: n, 1
- 7: y, 1 (or rotate 3/4 and flip horizontal)
- 8: n, 3

## Test image set generation

```
magick img.png img.jpg
magick img.png img.gif
magick img.png img.webp
magick img.png img.heic
magick img.png img.jxl
magick img.png img.tiff
magick img.png img.avif
magick img.png img.bmp
exiftool -Orientation=1 -n -o img-exif-oriented-n-0.jpg img.jpg
exiftool -Orientation=6 -n -o img-exif-oriented-n-1.jpg img.jpg
exiftool -Orientation=3 -n -o img-exif-oriented-n-2.jpg img.jpg
exiftool -Orientation=8 -n -o img-exif-oriented-n-3.jpg img.jpg
exiftool -Orientation=2 -n -o img-exif-oriented-y-0.jpg img.jpg
exiftool -Orientation=7 -n -o img-exif-oriented-y-1.jpg img.jpg
exiftool -Orientation=4 -n -o img-exif-oriented-y-2.jpg img.jpg
exiftool -Orientation=5 -n -o img-exif-oriented-y-3.jpg img.jpg
magick img.png -rotate 0 img-rotated-0.png
magick img.png -rotate 90 img-rotated-1.png
magick img.png -rotate 180 img-rotated-2.png
magick img.png -rotate 270 img-rotated-3.png
magick -delay 100 -loop 0 img-rotated-*.png img-animation.gif
magick -delay 100 -loop 0 img-rotated-*.png APNG:img-animation.png
magick -delay 100 -loop 0 img-rotated-*.png img-animation.webp
magick img.png img.dds
magick img.png img.exr
magick img.png img.ff
magick img.png img.hdr
magick img.png img.ico
magick img.png img.pnm
magick img.png img.tga
```

Test image must be not square to test rotation.

## Animation

Note: things related to SDL_image are deprecated, anim is decoded via image-rs and loaded into app-specific Frame arr holding frame textures and delays

SDL_image provides IMG_Animation struct with arrays of frame pixmaps and their "delays"; it can load animated GIFs into IMG_Animation; animated PNGs seem to be not supported.

SDL does not provide any playback mechanism; app developer is free to implement any loop which will render frames, somehow using their "delays" for waiting. In my current understanding, perfect loop should by the time of a display update event (vsync) get the frame which should be displayed during this vsync ready in the window backbuffer. Implementing this is hard and probably doesn't make sense at this point; I'll probably switch to something like libmpv eventually and get it together with proper video playback support. For now, I came up with such simple loop:
- before loop, set time_to_display_next_frame=now()+current_frame_delay (initially 0th)
- (1) calculate delay=time_to_display_next_frame-now() (delay till next frame)
- (2) if delay<0: set next frame as current (only frame counter, do not display), time_to_display_next_frame+=current_frame_delay (i. e. if missed time for next frame(s), the loop will run idle, skipping frames and only incrementing frame counter and time, until it catches up)
- (3) else (delay>0): wait for event or timeout time_to_display_next_frame-now() (whatever comes first, via `SDL_WaitEventTimeout()`)
- (4) if wait interrupted by event: handle it
- (5) else (wait interrupted by timeout): set next frame as current and display it; set time_to_display_next_frame+=current_frame_delay

This has assumption that all operations which are executed to display next frame (incl. waiting for display update event) take neglectable time compared to frame delay intervals. In reality some varying time will pass between wait timeout and frame being displayed, causing some jitter, but it seems unnoticeable.

I've also checked https://github.com/libsdl-org/SDL_image/blob/main/examples/showanim.c to see how SDL developers do this; that example has such loop:
- (1) handle events which are currently enqueued (via `SDL_PollEvent()`)
- (2) display current frame
- (3) wait for the duration of the current_frame_delay (via `SDL_Delay()`)
- (4) set next frame as current

However it causes frame time interval to grow by the time which it takes to handle events and display it, getting animation out of sync; also event handling happens in bursts between frames, causing delays for events which arrive during waiting

# GitHub actions workflows

GitHub actions means 2 things:
- GitHub CI/CD with UI to manage "workflows"
- reusable "apps"/"modules" for these workflows which can be invoked in steps

Model is this:
- workflow: unit described by workflow file in YAML format in .github/workflows; contains details about events which should cause its execution and and list of jobs and steps
  - job: unit described by child of "jobs" item in workflow; contains details about environment (host OS, possibly container image name, env vars) and list of steps
    - step: unit described by child of "steps" item in job; contains `run` keyword with shell commands to exec or `uses` keyword with action id

Workflows are often set up to run automatically upon events such as push to some branch, but it's entirely possible to have manually launched workflow with manually provided vars; for this project I currently prefer to create releases via launching workflow manually; via "Run workflow" button on `https://github.com/<user>/<repo>/actions/workflows/<workflow_filename>.yaml`, also available via "Actions" tab

## Build provenance attestation

For some reason, providing proof that release artifact was built on GitHub CI/CD infrastructure using GitHub Actions workflow is not "just there". There is "attest-build-provenance" action which can be added to workflow with list of filepaths, and it causes generation of "build provenance attestation" which is effectively such proof and can be found at `https://github.com/<user>/<repo>/attestations`, containing SHA hashes of files, information about build env and workflow, and GitHub signature.

## GitHub pages deployment

It is possible to deploy GitHub pages from GitHub actions workflow. To enable it, one must go to repo settings/pages and select "GitHub Actions" in "Source" selector. Initially it suggests few workflow templates incl. simplest "Static HTML"/"Simple workflow for deploying static content to GitHub Pages" one, which can be also seen at https://github.com/actions/starter-workflows/blob/main/pages/static.yml , with steps like:

```
      - name: step-pages-setup
        uses: actions/configure-pages@v5

      - name: step-pages-upload-artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: path/to/pages/artifact

      - name: step-pages-deploy-to-github
        id: deploy_pages
        uses: actions/deploy-pages@v4
```

Here `path/to/pages/artifact` is any directory on GitHub actions runner filesystem which should be created and populated before `step-pages-upload-artifact` step; its contents are copied to `<name-of-repo-to-which-actions-workflow-belongs>` subdir in `<repo-owner-username>.github.io` website dir on GitHub pages webserver; contents are not pushed to any branch of `<repo-owner-username>.github.io` repo or any other repo

## Running locally with Act

Act allows to run workflow locally: `act --reuse --input <input_name>=<value>`. `--reuse` for persistent container which is not destroyed upon completion and is reused upon next launch, allowing to enter container env with `docker exec -it <container_name> /bin/bash`

Of course workflow will fail on action which depends on something which is only avail on GitHub cloud runners

# Comparison with other viewers

- (template)
  - "fullscreen overlay":
  - "pan with drag with lmousebtn pressed":
  - "pan with kb arrows":
  - "zoom with scroll into point under cursor":
  - "zoom with kb +/- into central point":
  - "zoom with kb 0 to 1:1":
  - "toggle fullscreen with middle mouse btn":
  - "toggle fullscreen with F":
  - "toggle fullscreen with F11":
  - "switch prev/next with pgup/pgdn":
  - "exit with click on img":
  - "exit with Esc":
  - "exit with Enter":
- qview
  - "fullscreen overlay": N
  - "pan with drag with lmousebtn pressed": Y
  - "pan with kb arrows": N (left/right switch prev/next, up/down rotate)
  - "zoom with scroll into point under cursor": N (pan)
  - "zoom with kb +/- into central point": N (not used)
  - "zoom with kb 0 to 1:1": N (not used)
  - "toggle fullscreen with middle mouse btn": N (zoom to fit window)
  - "toggle fullscreen with F": N (mirror)
  - "toggle fullscreen with F11": N (not used)
  - "switch prev/next with pgup/pgdn": N (pan vertically, with win h step)
  - "exit with click on img": N (double click toggles fullscreen)
  - "exit with Esc": N (not used)
  - "exit with Enter": N (not used)
- feh
  - "fullscreen overlay": N
  - "pan with drag with lmousebtn pressed": Y
  - "pan with kb arrows": N (up/down zoom into point in the center)
  - "zoom with scroll into point under cursor": N (not used)
  - "zoom with kb +/- into central point": N (not used)
  - "zoom with kb 0 to 1:1": N (not used)
  - "toggle fullscreen with middle mouse btn": N (zoom to 1:1 and center)
  - "toggle fullscreen with F": Y (ugly, windows seems recreated)
  - "toggle fullscreen with F11": N (not used)
  - "switch prev/next with pgup/pgdn": N (not used)
  - "exit with click on img": N (not used)
  - "exit with Esc": Y
  - "exit with Enter": N (not used)
- sxiv
  - "fullscreen overlay": N
  - "pan with drag with lmousebtn pressed": N
  - "pan with kb arrows": Y
  - "zoom with scroll into point under cursor": Y (inconsistent)
  - "zoom with kb +/- into central point": N (Shift+=/-, into point under cursor, inconsistent, + zoom to 1:1, - mirror vertically)
  - "zoom with kb 0 to 1:1": N (not used)
  - "toggle fullscreen with middle mouse btn": N (pan, in a way I find inconvinient)
  - "toggle fullscreen with F": Y (preserving scale and left top corner)
  - "toggle fullscreen with F11": N (not used)
  - "switch prev/next with pgup/pgdn": N (not used)
  - "exit with click on img": N (not used)
  - "exit with Esc": N (not used)
  - "exit with Enter": N (gallery of files specified as cmdine args)
- Loupe (Gnome image viewer)
  - "fullscreen overlay": X
  - "pan with drag with lmousebtn pressed": Y
  - "pan with kb arrows": N (left/right switches prev/next, also doesn't loop)
  - "zoom with scroll into point under cursor": N (vertical scroll pans vertically, horizontal horizontally, zoom via multitouch)
  - "zoom with kb +/- into central point": N (zooms into point under cursor)
  - "zoom with kb 0 to 1:1": N (zooms to fit window)
  - "toggle fullscreen with middle mouse btn": X (does nothing, Enter toggles fullscreen)
  - "toggle fullscreen with F": N (does nothing)
  - "toggle fullscreen with F11": Y
  - "switch prev/next with pgup/pgdn": Y
  - "exit with click on img": N (double click toggles fullscreen)
  - "exit with Esc": N
  - "exit with Enter": N (toggles fullscreen)
- Win11 image viewer
  - "fullscreen overlay": N
  - "pan with drag with lmousebtn pressed": Y
  - "pan with kb arrows": N (Y for up/down, but left/right switch prev/next)
  - "zoom with scroll into point under cursor": Y
  - "zoom with kb +/- into central point": N
  - "zoom with kb 0 to 1:1": N
  - "toggle fullscreen with middle mouse btn": N (double click zoom to 1:1)
  - "toggle fullscreen with F": N (toggle images list panel)
  - "toggle fullscreen with F11": Y
  - "switch prev/next with pgup/pgdn": Y
  - "exit with click on img": N (double click zoom to 1:1)
  - "exit with Esc": N
  - "exit with Enter": N
- Gwenview (KDE/Plasma viewer)
  - "fullscreen overlay": N
  - "pan with drag with lmousebtn pressed": Y
  - "pan with kb arrows": Y
  - "zoom with scroll into point under cursor": N (vertical pan)
  - "zoom with kb +/- into central point": N
  - "zoom with kb 0 to 1:1": N
  - "toggle fullscreen with middle mouse btn":
  - "toggle fullscreen with F": N (toggles zoom between cur zoom and fit window, cur zoom into point under cursor)
  - "toggle fullscreen with F11": Y
  - "switch prev/next with pgup/pgdn": N (vertical pan with view area h step)
  - "exit with click on img": N (double click toggles fullscreen)
  - "exit with Esc": N (switch to gallery view)
  - "exit with Enter": N
- Sushi
- IrfanView
- LightView

UI/UX which makes feeling that "activated" image miniature from gallery is "expanded" into larger view, which can be closed by clicking anywhere outside its rect, is commonly called "lightbox", "modal image viewing" or "quick view"; however close by clicking on image itself is not really popular, and UX designers seem to be obsessed with idea that user will often accidentally click on image and disruptive action like close should not be bound to it; even QuickLook/Sushi which is designed for toggling uses Space key.

Vertical scrolling bound to vertical scrolling seems to be connected with "touchscreen first" UI; if touch movement is handled as pan, vertical and horizontal scrolling are automatically handled as vertical and horizontal touch movements by UI toolkits

Panning image in pan area is usually only allowed when image does not fit in the area
