{pkgs}: {
  deps = [
    pkgs.dbus
    pkgs.xorg.libXinerama
    pkgs.xorg.libXrandr
    pkgs.xorg.libXcursor
    pkgs.xorg.libXi
    pkgs.freetype
    pkgs.fontconfig
    pkgs.libxkbcommon
    pkgs.libGL
    pkgs.xorg.xcbutilrenderutil
    pkgs.xorg.xcbutilkeysyms
    pkgs.xorg.xcbutilimage
    pkgs.xorg.xcbutilwm
    pkgs.xorg.xcbutil
    pkgs.xorg.libXext
    pkgs.xorg.libXrender
    pkgs.xorg.libxcb
    pkgs.xorg.libXft
    pkgs.xorg.libX11
    pkgs.tcl
    pkgs.tk
  ];
}
