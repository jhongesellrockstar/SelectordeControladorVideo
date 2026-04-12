# PyInstaller spec para DriverSwitch GUI
# Ejecutar: pyinstaller packaging/driverswitch_gui.spec

from pathlib import Path

block_cipher = None
ROOT = Path(__file__).resolve().parents[1]

added_files = [
    (str(ROOT / 'image1.ico'), '.'),
    (str(ROOT / 'image1.png'), '.'),
    (str(ROOT / 'resources' / 'default_profile.txt'), 'resources'),
    (str(ROOT / 'objetivo_proyecto_driver_gui.txt'), '.'),
    (str(ROOT / 'README.md'), '.'),
]

a = Analysis(
    [str(ROOT / 'app.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DriverSwitchGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(ROOT / 'image1.ico'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DriverSwitchGUI',
)
