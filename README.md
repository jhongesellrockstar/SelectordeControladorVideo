# DriverSwitch GUI - Selector de controlador de video

Aplicación de escritorio en Python/Tkinter para Windows 11 centrada en resolver Intel + Meta Quest 3.

## Flujo real implementado
- Agrega driver con: `pnputil /add-driver <INF> /install /force`.
- Detecta `InstanceId` Intel (`pnputil /enum-devices /class Display`).
- Actualiza dispositivo con: `pnputil /update-driver oemXX.inf <InstanceId>`.
- Refresca adaptador Intel y verifica versión post-instalación.
- Si la versión final no es `31.0.101.2115`, informa reversión automática de Windows.

## Funcionalidad clave
- Detección separada: adaptador virtual vs GPU Intel física objetivo.
- Validación previa estricta antes de aplicar INF.
- Confirmación explícita (INF, destino, motivo).
- Log humano en GUI + log técnico exportable.
- Modo administrador detectado + botón "Reabrir como administrador".
- Opción opcional para bloquear actualización automática de drivers.
