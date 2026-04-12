# PyInstaller spec para DriverSwitch GUI
# Ejecutar: pyinstaller packaging/driverswitch_gui.spec

block_cipher = None

added_files = [
    ('image1.ico', '.'),
    ('image1.png', '.'),
    ('resources/default_profile.txt', 'resources'),
    ('objetivo_proyecto_driver_gui.txt', '.'),
    ('README.md', '.'),
]

a = Analysis(
    ['app.py'],
    pathex=['.'],
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
    icon='image1.ico',
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
