import os

from itkc.config import load_settings
from itkc.repo_catalogo_servicios_excel import ExcelCatalogoServiciosRepo
from itkc.service_catalogo_servicios import CatalogoServiciosService


# RUTAS ROBUSTAS
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))     # ...\Scripts\mod_catalogo_servicios
SCRIPTS_DIR = os.path.dirname(MODULE_DIR)                   # ...\Scripts
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)                 # ...\IT_Knowledge_Core

EXCEL_PATH = os.path.join(PROJECT_ROOT, "Data", "Catalogo_servicios.xlsx")


def mostrar_lista(df, limit=30):
    if df.empty:
        print("No hay registros.")
        return
    print(f"\nRegistros (mostrando hasta {limit} de {len(df)}):")
    for i, r in df.head(limit).reset_index(drop=True).iterrows():
        print(f"{i}. {r['servicio']} | {r['categoria']} > {r['subcategoria']}")


def main():
    settings = load_settings(SCRIPTS_DIR)

    repo = ExcelCatalogoServiciosRepo(EXCEL_PATH)
    svc = CatalogoServiciosService()

    try:
        df = repo.cargar().reset_index(drop=True)
    except Exception as e:
        print("\n[ERROR] No se pudo cargar el catálogo:", e)
        raise SystemExit(1)

    while True:
        print("\n=== IT Knowledge Core | Catálogo de Servicios ===")
        print("1) Consultar (Agente)")
        print("2) Modo supervisor (Agregar/Eliminar)")
        print("3) Salir")

        op = input("Seleccione una opción: ").strip()

        if op == "1":
            q = input("Buscar (servicio/categoría/subcategoría). Enter = ver todo: ").strip()
            res = svc.buscar(df, q)
            mostrar_lista(res, limit=50)

        elif op == "2":
            pin = input("Ingrese PIN de supervisor: ").strip()
            if pin != settings.supervisor_pin:
                print("PIN incorrecto.")
                continue

            print("\n=== MODO SUPERVISOR ===")
            print("1) Agregar servicio")
            print("2) Eliminar servicio (por número)")
            print("3) Volver")

            sop = input("Seleccione: ").strip()

            if sop == "1":
                servicio = input("Servicio (obligatorio): ").strip()
                categoria = input("Categoría (opcional): ").strip()
                subcategoria = input("Subcategoría (opcional): ").strip()

                df_before = df.copy(deep=True)
                df = svc.agregar(df, servicio, categoria, subcategoria).reset_index(drop=True)

                if not df.equals(df_before):
                    repo.guardar(df)
                    df = repo.cargar().reset_index(drop=True)

            elif sop == "2":
                mostrar_lista(df, limit=200)
                sel = input("Ingrese el número exacto a eliminar (o 999 para cancelar): ").strip()
                if sel == "999":
                    continue
                if not sel.isdigit():
                    print("Entrada inválida.")
                    continue

                idx = int(sel)
                df_before = df.copy(deep=True)
                df = svc.eliminar_por_indice(df, idx)

                if not df.equals(df_before):
                    repo.guardar(df)
                    df = repo.cargar().reset_index(drop=True)

            else:
                continue

        elif op == "3":
            print("Saliendo.")
            break

        else:
            print("Opción inválida.")


if __name__ == "__main__":
    main()
