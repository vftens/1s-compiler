# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui\\desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src',           'src'),
        ('examples',      'examples'),
        ('config',        'config'),
        ('gui\\assets',   'gui\\assets'),
    ],
    hiddenimports=[
        'webview', 'webview.platforms.winforms',
        'flask', 'jinja2', 'werkzeug',
        'src.server', 'src.auth', 'src.cli',
        'src.lexer', 'src.parser', 'src.runtime', 'src.transpiler',
        'src.i18n', 'clr',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='1S-ERP',
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
    icon=['gui\\assets\\icon.ico'],
    version='gui\\version_info.txt',
)
