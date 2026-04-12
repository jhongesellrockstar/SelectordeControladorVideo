import subprocess
import datetime
import os
import sys

OUTPUT_FILE = "diagnostico_gpu.txt"

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip() if result.stdout else result.stderr.strip()
    except Exception as e:
        return f"ERROR ejecutando comando: {e}"

def write_section(f, title, content):
    f.write("\n" + "="*80 + "\n")
    f.write(f"{title}\n")
    f.write("="*80 + "\n")
    f.write(content + "\n")

def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"DIAGNÓSTICO DEL SISTEMA - GPU / DRIVERS\n")
        f.write(f"Fecha: {datetime.datetime.now()}\n")
        f.write(f"Usuario: {os.getlogin()}\n")
        f.write(f"Python: {sys.version}\n")

        # --- INFO GENERAL ---
        write_section(f, "Sistema operativo",
                      run_cmd("systeminfo"))

        # --- GPU DETECTADA ---
        write_section(f, "GPU detectadas (WMIC)",
                      run_cmd("wmic path win32_VideoController get Name,DriverVersion,PNPDeviceID"))

        # --- PNP DEVICES DISPLAY ---
        write_section(f, "Dispositivos de pantalla (PnP)",
                      run_cmd("powershell \"Get-PnpDevice -Class Display | Select-Object FriendlyName,InstanceId,Status\""))

        # --- DRIVERS INSTALADOS DISPLAY ---
        write_section(f, "Drivers firmados (Display)",
                      run_cmd("powershell \"Get-CimInstance Win32_PnPSignedDriver | Where-Object {$_.DeviceClass -eq 'DISPLAY'} | Select DeviceName,DriverVersion,DriverProviderName,InfName\""))

        # --- DRIVER STORE ---
        write_section(f, "Driver Store (pnputil)",
                      run_cmd("pnputil /enum-drivers"))

        # --- EVENTOS CRÍTICOS (GRÁFICOS) ---
        write_section(f, "Eventos recientes relacionados a gráficos",
                      run_cmd("powershell \"Get-WinEvent -LogName System | Where-Object {$_.Message -like '*display*' -or $_.Message -like '*graphics*'} | Select-Object -First 20 TimeCreated,Message\""))

        # --- DISPOSITIVOS META ---
        write_section(f, "Dispositivos relacionados a Meta",
                      run_cmd("powershell \"Get-PnpDevice | Where-Object {$_.FriendlyName -like '*Meta*'}\""))

        # --- VARIABLES IMPORTANTES ---
        write_section(f, "Variables de entorno relevantes",
                      str({k: v for k, v in os.environ.items() if 'PATH' in k or 'CUDA' in k or 'GRAPHICS' in k}))

        # --- RUTAS CRÍTICAS ---
        write_section(f, "Contenido de carpeta Drivers Intel (System32)",
                      run_cmd("dir C:\\Windows\\System32\\DriverStore\\FileRepository"))

        # --- VERSIONES DX ---
        write_section(f, "DirectX info",
                      run_cmd("dxdiag /t dxdiag_output.txt"))

    print(f"\nDiagnóstico generado en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()