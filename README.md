# DriverSwitch GUI - Selector de controlador de video

Herramienta de escritorio en Python/Tkinter para Windows 11 orientada a la gestión visual de controladores gráficos (Intel UHD y otros adaptadores Display), con soporte de perfiles de equipo en formato `.txt` tipo INI.

## Capacidades actuales
- Lectura del estado del sistema con:
  - `Get-CimInstance Win32_VideoController`
  - `Get-PnpDevice -Class Display`
  - `pnputil /enum-drivers /class Display`
- Inventario de drivers Display del Driver Store.
- Escaneo de carpetas externas con `.inf` compatibles.
- Detección automática de carpeta Intel2115 (`iigd_dch.inf`) y marcado preferido.
- Flujo de aplicación de controlador con validación, instalación (`pnputil`) y refresco del adaptador.
- Sistema de perfiles de equipo:
  - `cargar_perfil(ruta)`
  - `guardar_perfil(ruta)`
  - `crear_perfil_vacio()`
  - `comparar_perfil_vs_sistema()`
- Advertencia de compatibilidad para Realidad Mixta si el driver activo no es `31.0.101.2115`.
- Persistencia de preferidos/rutas y log de auditoría exportable.

## Estructura
- `app.py`: punto de entrada.
- `driverswitch_gui/ui.py`: GUI y flujo de usuario.
- `driverswitch_gui/models.py`: modelos `DriverCandidate`, `ProfileData`, `ProfileComparison`.
- `driverswitch_gui/services/system_info.py`: lectura de estado del hardware/controlador.
- `driverswitch_gui/services/driver_inventory.py`: inventario Driver Store + INF externos + detección Intel2115.
- `driverswitch_gui/services/driver_actions.py`: validación/aplicación/refresco/reinicio.
- `driverswitch_gui/services/profile_service.py`: parser INI `.txt` de perfiles de equipo.
- `driverswitch_gui/services/config_store.py`: persistencia de configuración.
- `driverswitch_gui/services/audit_logger.py`: trazabilidad de acciones.

## Ejecución
```powershell
python app.py
```

> Recomendado: ejecutar como Administrador para instalar/controlar drivers.

## Persistencia
- `%APPDATA%\DriverSwitchGUI\config.json`
- `%APPDATA%\DriverSwitchGUI\driverswitch.log`
- `%APPDATA%\DriverSwitchGUI\perfil_base.txt` (perfil por defecto)
