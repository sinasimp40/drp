# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/home/runner/workspace/license_server/builds/_work/1_5/launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('/home/runner/workspace/license_server/builds/_work/1_5/splash_logo.gif', '.'), ('/home/runner/workspace/license_server/builds/_work/1_5/splash_logo.png', '.'), ('/home/runner/workspace/license_server/builds/_work/1_5/Roblox2017.ttf', '.')],
    hiddenimports=['_socket', 'socket', 'ssl', '_ssl', 'select', '_hashlib', 'encodings.idna', '_bz2', '_lzma'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PremiumActiveTest',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
