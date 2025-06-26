---
title: SDL3 image viewer development notes
summary: notes about development of https://github.com/shatsky/lightning-image-viewer
---

This is not SDL3 app development guide. SDL3 documentation is quite good and complete. These are notes about some corner cases and related problems.

# SDL generic stuff

## Window size and position

Surprisingly, there seems to be a problem with creating maximized non-fullscreen window with exactly maximum size allowed by shell on the "current" display. SDL_CreateWindow() requires explicit width and height. Options:
- SDL_GetDesktopDisplayMode(): get full height and width, including shell UI
- SDL_GetDisplayUsableBounds(): get rectangle representing useable (not used by shell UI) area of the display in global coordinate system of multi-display setup; this seems to produce incorrect results on Plasma Wayland

SDL_GetCurrentDisplayMode() is NOT about "current display", it's about "current mode" for fullscreen apps switching display mode on platforms which support this, not relevant at all. All these functions require display id; however there seems to be no control over on which display new window is displayed. SDL2 SDL_CreateWindow() used to accept position x, y allowing to position it in top right corner of specific display in multi display setup with values from SDL_GetDisplayUsableBounds(); however SDL3 SDL_CreateWindow() doesn't have these args anymore

There seems to be no "current display from user perspective" concept (I'd define it as "display on which top left corner of currently active window is when SDL_CreateWindow() is called") and no way to get it

For now, I call SDL_CreateWindow() with w and h from SDL_GetDesktopDisplayMode() called with display id from SDL_GetPrimaryDisplay(), which works acceptable with single display, haven't tested in multi display setup yet.

## HiDPI and scaling

Desktop environments have scaling to make UI items look larger than some "default size". It is often enabled on HiDPI displays. It can affect program in 2 ways:
- make rendered window contents displayed scaled
- make queried coords and sizes reported in "scaled pixels"
Normally both do happen and I need to prevent both from happening to have pixel perfect rendering with consistent input handling.

For now I set SDL_HINT_VIDEO_WAYLAND_SCALE_TO_DISPLAY 1; it's Wayland-specific quirk which is discouraged from being used in docs, but it seems to work well on Plasma Wayland, and on Windows both displaying and reporting seems to be unscaled for "HiDPI/scaling-unaware" apps by default

SDL3 "proper way to write HiDPI aware apps" is described in https://wiki.libsdl.org/SDL3/README-highdpi , however (at least on Plasma Wayland) setting window flag SDL_WINDOW_HIGH_PIXEL_DENSITY only prevents displaying scaling, while reporting remains scaled, requiring additional calls like SDL_ConvertEventToRenderCoordinates() to get values in "physical pixels", which makes no sense for me; I think that sane approach would be to save single switch (like SDL_HINT_VIDEO_WAYLAND_SCALE_TO_DISPLAY but platform agnostic)

# Windows

## Cross building for Windows on NixOS Linux

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

## Windows encodings

By default Windows uses some mess of UTF16 and single byte encodings. For graphical program which has main() as entry point, argv is provided in single byte encoding which is chosen as "ANSI codepage", such as CP1251, causing issues with cross platform libraries which expect UTF8. Simplest way I found to force Windows to just use UTF8 everywhere for app is manifest as described in https://github.com/alf-p-steinbach/C---how-to---make-non-English-text-work-in-Windows/blob/main/how-to-use-utf8-in-windows.md

## Windows "antivirus"

Windows "antivirus" nowadays often blocks unknown unsigned binaries which are not yet in some trusted binaries db after having been downloaded and run by thousands of users, claiming it contains "Trojan/Wacatac.B!ml" or similarly named malware. Nobody knows for sure what this even means, but many claim that "!ml" suffix means it's AI detection.

# C file and directory I/O, Windows, POSIX and glibc

Surprisingly for me being used to "just use whatever glibc provides", "ISO C standard library" has file I/O but no directory I/O API at all (what is % of environments which have filesystem but without directory concept?). glibc (and other libc implementations for POSIX systems) implements ISO C standard library with POSIX extensions including POSIX directory I/O. However mingw gcc uses not glibc but Microsoft C runtime (msvcrt/ucrt) which doesn't have (most of?) POSIX extensions; native Windows software is expected to use Win32 API fileapi.h FindFirstFile()/FindNextFile()/FindClose(); mingw provides subset of POSIX implemented with these, but fairly incomplete, it misses scandir() among others which I needed to iterate image files sorted by mtime.

Another surprising discovery was that struct dirent which represents directory entry in POSIX directory I/O API is allowed to "overflow" its declared size; it's last member dirent.d_name, declared as char array of some impl-decided size, can "hold" longer \0-terminated str than its size allows. Implementations allocate mem of appropriate size for dirent to "safely" hold its data with this "overflow". It's often refered as case of "Flexible array member", but "Flexible array member" seems to be about allowing declaring last member of struct as array without specified size at all (treated by sizeof() as size of 0), while glibc seems to declare d_name as array of size 1.

# Emscripten

It's cool to provide app demo on app webpage, right?

Emscripten is solution which allows to compile C code to WASM and run it in browser. It includes emcc compiler which is basically drop-in replacement for gcc and runtime which emulates basic POSIX OS (including filesystem access, backed by MEMFS) and provides means for interop with webpage JS/HTML (including access to HTML canvas as framebuffer with harware accelerated graphics APIs supported by browser). Using latter requires support from app side, but I've noticed that SDL3 implements it, supporting Emscripten as another platform and allowing to build and run unmodified SDL3 app (at least if it only relies on basic SDL3 and POSIX APIs), and decided this hangs low enough to reach for.

However, Emscripten doesn't seem to care much about scenario "run unmodified/Emscripten-unaware app and control it from webpage JS"; they believe that app code must be aware and in control of webpage, not vice versa. Even with SDL3 Emscripten support this causes problems, but nothing showstopping.

## Building app

Generic build sequence is like:

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

To run Emscripten SDL app, it's basically enough for webpage to contain `<canvas id="canvas">` (SDL Emscripten backend looks for this id by default) and `<script src="/path/to/index.js">` (generated by emcc). However if one wants to change default Emscripten behaviour, one has to add JS which creates `Module` object with overrides before including index.js

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
- TIFF is file format which is much more complex than JIF/JFIF; TIFF file is something like archive, consisting of "TIFF directories", which include "TIFF tags", allowing to contain multiple images in different formats (incl. JPEG). TIFF is rarely used as standalone file format nowadays, but commonly used as embedded file format because of EXIF.
- EXIF is simultaneously metadata, file, TIFF and JPEG format. What? Yes.
  - EXIF ascronym stands for "Exchangeable Image File Format"
  - EXIF standard defines EXIF metadata format which is basically TIFF intended to be embedded in other files; "almost TIFF" because it misses some tags which are mandatory in valid TIFF file; but otherwise it is fully compatible with TIFF and can be parsed with tiffdump tool from libtiff project. But can't be parsed with libtiff, because its external API functions nessessarily trigger checks for those mandatory tags and libtiff doesn't provide any means to skip them. Anyway libtiff seems to have very poor security reputation and virtually all big software seems to use either libexif or exiv2 for parsing EXIF metadata
  - EXIF standard defines another JPEG file format which is also based on JIF and is similar to JFIF but, unlike JFIF, it requires that after SOI there is "APP1" segment (marker `\xff\xe1`) with embedded EXIF metadata. This EXIF JPEG file format is called... EXIF, of course (suggesting that writing of EXIF standard was started with the intention to produce just it, but then it got out of control)
  - EXIF standard also defines TIFF file format with embedded EXIF metadata (which is, again, "almost TIFF" itself)
  - EXIF standard also defines WAV audio file format with embedded EXIF metadata... Yes, "Image File Format" audio format
  - many other multimedia formats themselves define embedding of EXIF metadata

## EXIF orientation tag

EXIF metadata is mostly relevant in scope of image viewer development because of its orientation tag and its usage in JPEG. It's not uncommon that image pixmap is encoded in different orientation then it's supposed to be displayed, usually as result of camera being rotated when taking photo. For lossless image formats like PNG it's no problem to re-encode pixmap with corrected orientation, but for lossless image formats like JPEG re-encoding usually causes loss of quality. Therefore, common solution is to add metadata with some "orientation tag". Some newer lossy image formats have it defined in the format itself, but JPEG historically relies on EXIF one, and common JPEG decoders incl. libjpeg don't decode EXIF metadata, leaving this task to app.

Tag values and decoded pixmap->view transformations seen as pixmap mirroring (n/y) and rotation (1/4 turns clockwise):
- 1: n, 0
- 2: y, 0
- 3: n, 2
- 4: y, 2
- 5: y, 3
- 6: n, 1
- 7: y, 1
- 8: y, 3

## Test image set generation

```
exiftool -all= -o image-exif-removed.jpg image.jpg
exiftool -Orientation=1 -n -o image-exif-oriented-n-0.jpg image.jpg
exiftool -Orientation=2 -n -o image-exif-oriented-y-0.jpg image.jpg
exiftool -Orientation=3 -n -o image-exif-oriented-n-2.jpg image.jpg
exiftool -Orientation=4 -n -o image-exif-oriented-y-2.jpg image.jpg
exiftool -Orientation=5 -n -o image-exif-oriented-y-3.jpg image.jpg
exiftool -Orientation=6 -n -o image-exif-oriented-n-1.jpg image.jpg
exiftool -Orientation=7 -n -o image-exif-oriented-y-1.jpg image.jpg
exiftool -Orientation=8 -n -o image-exif-oriented-y-3.jpg image.jpg
magick image.jpg image.png
magick image.jpg image.gif
magick image.jpg image.webp
magick image.jpg image.avif
magick image.jpg image.heic
magick image.jpg image.tiff
magick image.jpg image.jxl
```

# GitHub actions workflows

Github actions means 2 things:
- github CI/CD with UI to manage "workflows"
- reusable "apps"/"modules" for these workflows which can be invoked in steps

Model is this:
- workflow: unit described by workflow file in YAML format in .github/workflows; contains details about events which should cause its execution and and list of jobs and steps
  - job: unit described by child of "jobs" item in workflow; contains details about environment (host OS, possibly container image name, env vars) and list of steps
    - step: unit described by child of "steps" item in job; contains `run` keyword with shell commands to exec or `uses` keyword with action id

Workflows are often set up to run automatically upon events such as push to some branch, but it's entirely possible to have manually launched workflow with manually provided vars; for this project I currently prefer to create releases via launching workflow manually

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
