# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path('.').resolve()

# Include compiled frontend
datas = [
    (str(project_root / 'frontend' / 'dist'), 'frontend/dist'),
    (str(project_root / 'build_assets' / 'app_icon.ico'), 'assets'),
    (str(project_root / 'frontend' / 'src' / 'assets' / 'gf-farmer-mark.png'), 'assets'),
]

# Include SQLite migration files
migrations_dir = project_root / 'src' / 'gf_dashboard' / 'infrastructure' / 'migrations'
for sql_file in sorted(migrations_dir.glob('*.sql')):
    datas.append((str(sql_file), 'gf_dashboard/infrastructure/migrations'))

hiddenimports = [
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebChannel',
    'PySide6.QtNetwork',
    'PySide6.QtGui',
    'PySide6.QtCore',
    'PySide6.QtWidgets',
    'winreg',
    'tzdata',
]

a = Analysis(
    ['src/gf_dashboard/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GF Farmer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'build_assets' / 'app_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='GF Farmer',
)
