# Selector de Controlador de Video (Windows 11)

Aplicación de escritorio en Python + Tkinter para gestionar visualmente controladores gráficos en Windows 11.

## Funciones incluidas
- Detección del estado actual del sistema (equipo, adaptador activo, versión, fecha, INF, fabricante).
- Inventario de controladores gráficos del Driver Store mediante `pnputil`.
- Carga de carpetas externas con archivos `.inf` y validación de controladores de pantalla.
- Selección y marcado de versión preferida.
- Aplicación de controlador con flujo asistido (`pnputil /add-driver /install`).
- Refresco del adaptador gráfico (`pnputil /restart-device`).
- Modo de recuperación rápida usando la versión preferida.
- Persistencia de configuración del usuario y rutas externas.
- Registro/auditoría exportable.

## Estructura
- `app.py`: punto de entrada.
- `driverswitch_gui/ui.py`: interfaz gráfica y flujo principal.
- `driverswitch_gui/services/system_info.py`: lectura del estado actual.
- `driverswitch_gui/services/driver_inventory.py`: inventario Driver Store + carpetas externas.
- `driverswitch_gui/services/driver_actions.py`: aplicación de cambios, refresco y reinicio.
- `driverswitch_gui/services/config_store.py`: persistencia de configuración.
- `driverswitch_gui/services/audit_logger.py`: auditoría.
- `driverswitch_gui/models.py`: modelos de datos.

## Ejecución
En Windows 11 con Python 3.10+:

```powershell
python app.py
```

> Recomendado: ejecutar la app como Administrador para aplicar controladores y reiniciar dispositivos.

## Datos persistidos
La aplicación guarda su información en:

- `%APPDATA%\DriverSwitchGUI\config.json`
- `%APPDATA%\DriverSwitchGUI\driverswitch.log`
