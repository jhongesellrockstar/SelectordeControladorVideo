# DriverSwitch GUI - Selector de controlador de video

Aplicación de escritorio en Python/Tkinter para Windows 11 centrada en resolver el caso real Intel + Meta Quest 3.

## Enfoque actual (caso real)
- Diagnóstico basado en **GPU física Intel** (no en Meta Virtual Monitor).
- Detección separada de adaptador virtual y adaptador Intel objetivo.
- Prioridad de INF para `Intel2115\iigd_dch.inf` si existe.
- Validación previa antes de aplicar (dispositivo objetivo, INF, versión/meta, admin).
- Confirmación explícita: INF exacto + destino Intel UHD + motivo de selección.

## Funcionalidad clave
- Log en tiempo real dentro de la GUI (humano) y log técnico exportable.
- Modo "Resolver mi caso real" y botón "Diagnosticar mi equipo".
- Ejecución no bloqueante (`threading` + `queue` + `after`).
- Detección de administrador + botón "Reabrir como administrador".
- Aplicación de driver con timeout extendido y detalle de comando/INF/dispositivo en caso de fallo.

## Ejecutar
```powershell
python app.py
```

> Recomendado: abrir siempre como administrador.
