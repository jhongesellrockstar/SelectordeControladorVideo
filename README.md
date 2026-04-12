# DriverSwitch GUI - Intel Driver Manager

Aplicación de escritorio (Python/Tkinter) para Windows 11 orientada a gestionar el driver Intel UHD y compatibilidad con Meta Quest 3.

## Estado funcional
- Diagnóstico Intel vs adaptador virtual.
- Aplicación de driver objetivo Intel con `pnputil` y validación post-instalación.
- Opción avanzada: desinstalar controlador Intel actual (controlada y con advertencias).
- Logs humano (GUI) y técnico (archivo).

## Iconos y recursos
Archivos esperados en la raíz del proyecto:
- `image1.ico` (icono Windows/ejecutable)
- `image1.png` (icono GUI)

La app usa `get_resource_path()` para resolver rutas en modo fuente y en modo PyInstaller (`_MEIPASS`).

## Build con PyInstaller
### Opción recomendada (spec)
```powershell
pyinstaller packaging/driverswitch_gui.spec
```

Salida esperada:
- `dist/DriverSwitchGUI/DriverSwitchGUI.exe`

### Archivos incluidos como `datas`
- `image1.ico`
- `image1.png`
- `resources/default_profile.txt`
- `objetivo_proyecto_driver_gui.txt`
- `README.md`

## Instalador con Inno Setup
Se incluye plantilla base:
- `packaging/installer.iss`

Flujo típico:
1. Generar build con PyInstaller.
2. Abrir `packaging/installer.iss` en Inno Setup.
3. Ajustar versión/nombre/editor/rutas.
4. Compilar instalador.

## Distribución y firma digital (importante)
PyInstaller e Inno Setup **no eliminan por sí solos** advertencias de seguridad de Windows/SmartScreen.
Para reducir advertencias en distribución real normalmente se requiere:
- certificado de **code signing** válido,
- firma del `.exe` y del instalador,
- reputación progresiva del binario firmado.

## Flujo seguro recomendado
1. Ejecutar como administrador.
2. Diagnosticar estado Intel.
3. Si no está en `31.0.101.2115`, aplicar INF Intel objetivo.
4. Si Windows mantiene driver anterior por ranking OEM, usar desinstalación avanzada con precaución.
5. Reiniciar y re-diagnosticar.


## Iconos en Windows (fuente vs .exe)
- **Icono de ventana Tkinter**: se aplica en runtime con `iconbitmap()` / `iconphoto()` y afecta la ventana visible.
- **Icono de barra de tareas**: en Windows depende de AppUserModelID + icono de ventana; por eso la app configura `SetCurrentProcessExplicitAppUserModelID`.
- **Icono del `.exe` (PyInstaller)**: se define en build (`icon='image1.ico'` en el `.spec`) y afecta el archivo ejecutable/firma visual en Explorer.

Notas:
- En `python app.py`, el icono puede depender del proceso `python.exe/pythonw.exe`, por lo que AppUserModelID ayuda a que taskbar use el icono correcto.
- En `.exe` compilado, el icono del ejecutable y AppUserModelID suelen dar el resultado más consistente.


## Limpieza UX en Windows (sin ventanas negras)
Las llamadas a PowerShell/pnputil/cmd se ejecutan con banderas de proceso oculto (`CREATE_NO_WINDOW` + `STARTUPINFO/SW_HIDE`) para evitar flashes de consola y mantener captura de `stdout/stderr` en logs.

## Comandos finales de recompilación
### Ejecutable
```powershell
pyinstaller --clean packaging/driverswitch_gui.spec
```

### Instalador
1. Verifica que exista `dist/DriverSwitchGUI/`.
2. Abre `packaging/installer.iss` con Inno Setup Compiler.
3. Compila el script para generar `DriverSwitchGUI-Setup.exe`.
