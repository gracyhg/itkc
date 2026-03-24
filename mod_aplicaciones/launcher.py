import os

from itkc.config import load_settings
from itkc.service import AplicacionesService
from itkc.repo_excel import ExcelCatalogoRepo
from itkc.repo_sqlserver import SqlServerCatalogoRepo


# =========================
# RUTAS ROBUSTAS
# =========================
# launcher.py está en: ...\Scripts\mod_aplicaciones\launcher.py
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))     # ...\Scripts\mod_aplicaciones
SCRIPTS_DIR = os.path.dirname(MODULE_DIR)                   # ...\Scripts
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)                 # ...\IT_KNOWLEDGE_CORE

EXCEL_PATH = os.path.join(PROJECT_ROOT, "Data", "Aplicaciones_permitidas.xlsx")


def build_repo(settings):
    # Excel (activo hoy)
    if settings.backend == "excel":
        return ExcelCatalogoRepo(EXCEL_PATH)

    # SQL Server (cuando TI lo habilite)
    if settings.backend == "sqlserver":
        if not settings.sqlserver_conn_str:
            raise ValueError("Backend SQL Server seleccionado pero falta ITKC_SQLSERVER_CONN_STR.")
        return SqlServerCatalogoRepo(settings.sqlserver_conn_str)

    raise ValueError(f"Backend inválido: {settings.backend}. Usa 'excel' o 'sqlserver'.")


def diagnostico(settings):
    print("\n=== Diagnóstico de backend ===")
    print("Backend:", settings.backend)
    print("Project root:", PROJECT_ROOT)
    print("Excel path:", EXCEL_PATH)
    print("Supervisor PIN configurado:", "SI" if bool(settings.supervisor_pin) else "NO")

    if settings.backend == "sqlserver":
        print("SQL ConnStr presente:", "SI" if bool(settings.sqlserver_conn_str) else "NO")
        try:
            import pyodbc  # noqa: F401
            print("pyodbc instalado: SI")
        except Exception:
            print("pyodbc instalado: NO (cuando uses SQL, instalarlo con: python -m pip install pyodbc)")
    else:
        print("SQL no activo. Para activarlo: ITKC_BACKEND=sqlserver")

    print("=== Fin diagnóstico ===\n")


def main():
    # Importante: load_settings debe apuntar a Scripts (donde está itkc/config.py)
    settings = load_settings(SCRIPTS_DIR)

    try:
        repo = build_repo(settings)
    except Exception as e:
        print("\n[ERROR] No se pudo construir el repositorio:", e)
        raise SystemExit(1)

    svc = AplicacionesService()

    try:
        df = repo.cargar()
    except Exception as e:
        print("\n[ERROR] No se pudo cargar el catálogo:", e)
        raise SystemExit(1)

    while True:
        print("\n\t========================================================")
        print("\n\t=== IT Knowledge Core | Aplicaciones Permitidas ===")
        print("\n\t========================================================")
        print("\n")
        print("-----------------------------")
        print(f"---Backend activo: {settings.backend}---")
        print("-----------------------------")
        print("1) Consulta de aplicaciones (Agente)")
        print("2) Modo supervisor (Aprobar/Rechazar)")
        print("3) Diagnóstico de backend")
        print("4) Salir")

        opcion = input("Seleccione una opción: ").strip()

        # 1) Agente: consultar
        if opcion == "1":
            consulta = input("Ingrese el nombre del programa: ").strip()

            df_before = df.copy(deep=True)
            df = svc.consultar(df, consulta)

            # Guardar SOLO si hubo cambios (ej: enviar a revisión)
            try:
                if not df.equals(df_before):
                    repo.guardar(df)
                    df = repo.cargar()  # recargar para evitar desincronización
            except Exception as e:
                print("\n[ERROR] No se pudo guardar/recargar el catálogo:", e)

        # 2) Supervisor
        elif opcion == "2":
            df = svc.supervisor_menu(df, settings.supervisor_pin)

            # política simple: guardar y recargar
            try:
                repo.guardar(df)
                df = repo.cargar()
            except Exception as e:
                print("\n[ERROR] No se pudo guardar/recargar el catálogo:", e)

        # 3) Diagnóstico
        elif opcion == "3":
            diagnostico(settings)

        # 4) Salir
        elif opcion == "4":
            print("Saliendo.")
            break

        else:
            print("Opción inválida.")


if __name__ == "__main__":
    main()
