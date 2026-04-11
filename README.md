# DriverSwitch GUI - Selector de controlador de video

Aplicación de escritorio en Python/Tkinter para Windows 11 enfocada en resolver el caso real de compatibilidad Intel + Meta Quest 3.

## Qué incluye ahora
- Arranque rápido de GUI + carga pesada en segundo plano (thread + queue + `after`).
- Panel de log en tiempo real para usuario (mensajes con hora).
- Log técnico persistente (`driverswitch_technical.log`) exportable desde la GUI.
- Asistente textual “¿Qué hizo el software?” con recomendación del siguiente paso.
- Botón **Diagnosticar mi equipo** orientado a Meta Quest 3.
- Flujo guiado para detectar driver activo y comparar contra objetivo `31.0.101.2115`.
- Inventario de Driver Store (`pnputil`) + carpetas INF externas + detección Intel2115 (`iigd_dch.inf`).
- Sistema de perfiles `.txt` tipo INI (crear/cargar/guardar/comparar).
- Aplicación de controlador con validación, `pnputil /add-driver /install` y refresco de adaptador.

## Estructura
- `app.py`: entrada.
- `driverswitch_gui/ui.py`: GUI, tareas background y flujo guiado.
- `driverswitch_gui/services/system_info.py`: lectura Win32/PnP con timeouts.
- `driverswitch_gui/services/driver_inventory.py`: inventario y escaneo INF.
- `driverswitch_gui/services/driver_actions.py`: validación y aplicación de driver.
- `driverswitch_gui/services/profile_service.py`: parser de perfiles.
- `driverswitch_gui/services/diagnostic_service.py`: diagnóstico centrado en Meta Quest 3.
- `driverswitch_gui/services/audit_logger.py`: log técnico.

## Ejecutar
```powershell
python app.py
```

> Recomendado: ejecutar como Administrador para aplicar controladores.
