---
title: My Nix FAQ
summary: Answers to questions which arise when trying to understand Nix
---

WARNING: I'm not a Nix expert, there can be false and misleading statements.

It is implied that you have used Nix, know what Nix can do and what Nix expression language is, understand basic concepts like "closure", "nix store" and "build hash".

Q: Why Nix and not OSTree/Flatpak/Docker/another edgy software deployment solution?
A: In addition to its advertised advantages, I believe that Nix preserves a valuable property of classical package managers which competitors seem to discard: structural clearness of the managed system. Every upstream project is represented by separate nix function, bound to separate attribute in the scope, producing separate paths in /nix/store when built and installed; dependencies are easily analyzeable. Besides, Nix is flexible like Gentoo Portage, it's possible to write nix package expressions which allow altering package and its dependencies set similarly to Portage USE flags.

Q: Where are all these nix expression files located in my Nix system and how Nix knows about them?
A: Nixpkgs snapshots are in /nix/store, Nix finds them via NIX_PATH env var and symlinks. Nix uses "path names" (`<>`-bracketed) which are translated to actual paths using NIX_PATH. E. g. `<nixpkgs>` is translated to `/nix/var/nix/profiles/per-user/root/channels/nixos` which is symlink to `/nix/store/<current nixpkgs snapshot path>/nixos` . Basically, Nix is configured to load `<nixpkgs>` first when you're using it via its package management utils.

Q: What is package name in Nix? I see that there are directories with relevant names in nixpkgs source tree, some nix tools use "nixpkgs.${program_name}" form, others use "${program_name}-${program_version}", how all these are related?
A: I think that one of things which makes it hard to understand Nix is that it has multiple entities which can be considered a "package name". They don't have to match each other, although policy requires that they do unless there's a good reason not to. Here I've tried to summarize them in a table.

| Attribute name (of a derivation set*) | Derivation name (in a derivation set) | Package nix expression directory name |
| ---                                   | ---                                   | ---                                   |
| What it is | Name of attribute in nix scope which contains package's derivation set | String value of "name" attribute in package's derivation set | Name of directory which contains package nix expression |
| Where it comes from | Statement in some nix expression (usually pkgs/top-level/all-packages.nix) which binds derivation set produced by function from package nix expression to the attribute name | Statement in package nix expression which binds the value to "name" attribute in a set which is usually passed to the stdenv.mkDerivation | Path in nixpkgs source tree |
| How it can be used | Installing via "nix-env -iA" | Installing via "nix-env -i" (discouraged because search for derivation name in all derivation sets in nix scope is way more expensive than search for attribute name of derivation set) | - (nixpkgs source tree hierarchy exists for maintainers' convenience, paths are only used internally as callPackage arguments in statements which bind derivation sets to attribute names) |
| Where it can be seen | Searching via "nix search"; suggestions which Nix provides in the shell when user enters name of a program which doesn't exist in the system but is listed in binary cache index | Listing via "nix-env -q"; nix store paths (part following the buildhash) | nixpkgs git and /nix/store paths which contain nixpkgs snapshots; it seems that after nix expressions are loaded and namespace is populated, Nix doesn't remember anything about source file paths |

*derivation set is nix expression language set which produces derivation when evaluated (nix considers set to be a derivation set if it has type="derivation" attribute)

Q: What does typical package nix expression contain?
A: Usually there's something like {set1 keys}: let ... in stdenv.mkDerivation rec {set2 entries} inside; it's a function which takes set1 and produces derivation set via stdenv.mkDerivation, by composing set2 and passing it to stdenv.mkDerivation.
let ... in is used to name some entities which are used in following expression
rec is used to "resolve dependencies" in a set, e. g. turn {x=1; y=x+1;} into {x=1; y=2;}
stdenv.mkDerivation is a "builder" function which produces a derivation set.

Q: What is a derivation? How derivation sets, derivations, /nix/store/*.drv files and paths with package contents are related?
A: Another thing which can make Nix hard to understand is protruding of this entity. If you think as a programmer about how Nix can make package nix expression into package contents, it may be obvious there should be some intermediate representation with final values of dependencies locations, etc. Derivation is its name, and .drv files are used to store derivations. Derivation contains build hashes of inputs (i. e. locations of dependencies in /nix/store) and of own outputs (i. e. locations which will be used to store package contents in /nix/store when derivation will be built). Evaluating a derivation set causes derivation to be created and stored in .drv file, as well as derivations of all dependencies (closure). After that derivation can be built, causing package contents to be produced and stored. Here I've tried to summarize Nix flow in a table:
Nix entity 	Location 	derivative produced via 	antiderivative found via
Package nix expression 	nixpkgs source tree 	loading 	-
Derivation set (accessible via attribute name) 	nix scope 	evaluating 	?
Derivation 	/nix/store 	building 	?
Output path (package contents) 	/nix/store 	- 	nix show-derivation ${path}

Q: I see package nix expression directory in nixpkgs source tree, how can I build and install the package?
A: "nix-env -i ${name}" if you can isolate derivation name value in the source, but it's not guaranteed that exactly the one you're looking at will be build because another package expression can declare same ${name}; you can't even be sure that expression you're looking at is bound to an attribute in nix scope at all. Nix is all about the scope, you should think of nixpkgs nix expressions as of a single program, its source splitted into small files and structured into tree hierarchy only for programmer's convenience; browsing the source tree is not intended way to find packages, and there seems to be no straightforward way to map source file path to attribute in the scope.

Q: Why dependencies are listed without version numbers in package nix expressions? Where are familiar >=min_ver, <=max_ver?
A: Version ranges are used in traditional package management systems only because they allow only a single version; with Nix it's possible to have any number of instances of any versions. If an app can run with the newest version of a lib, there's no reason use older version. Version-less attribute names in Nix always refer to newest versions available in a nixpkgs snapshots; if older version of a library is needed for some app, there will be special ${name}_${version} attribute for it which will be used in deps of that app; if it will be installed, it will be only known to this specific app.

Q: Why do "nix search ${program_name}" results, in addition to "nixpkgs.${program_name}", contain attributes like "nixpkgs.${something_else}.${program_name}" with same description? Why do Nix suggesstions in the shell sometimes only contain latter?
A: Nix scope is not flat, and some upper-level attributes can additionally appear nested in other sets which duplicate them for some internal purposes; "nix search" code seems to be imperfect and lists them as well as top level instances; nix suggestions code is even more imperfect. However it shouldn't matter which attribute name is used to build and install the package; (if) they all have identical derivation set, any of them will produce same derivation with same output buildhashes.

Q: What happens when I run "nix-env -iA nixpkgs.pkgname" ("nix-env --install --attr")?
A: nix loads `<nixpkgs>`, supposedly adding "pkgname" to the scope, builds a new "user-environment" derivation with "pkgname" added to its deps (causing "pkgname" derivation to be built and its outputs stored in /nix/store), creates a new `/nix/var/nix/profiles/per-user/<username>/profile-${next_available_number}` symlink pointing to its output path and points `/nix/var/nix/profiles/per-user/<username>/profile` symlink to that symlink.

Q: What happens when I run "nixos-rebuild switch"?
A: nix loads `<nixpkgs/nixos>`, evaluates "system" attribute and builds its derivation (which pulls all packages explicitly and implicitly specified in /etc/nixos/configuration.nix into the closure), creates /nix/var/nix/profiles/system-${next_available_number} symlink pointing to its output path and points /nix/var/nix/profiles/system symlink to that symlink; if bootloader is configured, Nix updates its config, adding a new entry which references kernel, initrd and init in /nix/store paths which belong to new system profile closure.

Q: What happens when I run "nix-channel --update"?
A: Nix build a new "user-environment" derivation which is dep tree root node and pulls in nixpkgs snapshots for all configured channels as its deps; symlinks pointing to the new env are created in `/nix/var/nix/profiles/per-user/<username>`, so that `<channel_name>` resolves to new snaphot path

Confusion: "user-environment" store path can be both for "channels" env (pulling in nixpkgs snapshots) and "profile" env (pulling in installed pkgs)

Q: How all those programs installed in /nix/store are available to user without requiring user to use paths with buildhashes?
A: PATH contains `/home/<username>/.nix-profile/bin` (which is in "user-environment" derivation output path and contains collected symlinks to programs in bin/ subdirs of all deps) and /run/current-system/sw/bin (which is in "system" derivation output path, ...)
