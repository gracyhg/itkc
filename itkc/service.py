import pandas as pd
from .domain import (
    ESTADO_PERMITIDA, ESTADO_REVISION, ESTADO_NO_PERMITIDA,
    now_str, normalizar_texto
)

class AplicacionesService:
    def consultar(self, df: pd.DataFrame, consulta: str) -> pd.DataFrame:
        consulta = (consulta or "").strip()
        consulta_norm = normalizar_texto(consulta)

        print("\nResultado de la consulta\n" + "-" * 30)

        if not consulta_norm:
            print("No ingresaste un nombre válido.")
            return df

        exactos = df[df["programa_norm"] == consulta_norm]
        resultado = exactos if not exactos.empty else df[df["programa_norm"].str.contains(consulta_norm, na=False)]

        if resultado.empty:
            print("El programa no se encuentra registrado.")
            enviar = input("¿Deseas enviar esta aplicación a revisión? (S/N): ").strip().lower()
            if enviar == "s":
                df = self._enviar_a_revision_interactivo(df, nombre_ingresado=consulta)
            else:
                print("No se envió a revisión.")
            return df

        if len(resultado) > 1:
            print(f"Se encontraron {len(resultado)} coincidencias. Mostrando lista (máx 10):")
            for _, row in resultado.head(10).iterrows():
                print(f"- {row.get('programa','N/D')} (Estado: {row.get('estado','N/D')})")
            print("\nTip: intenta escribir el nombre más específico.")
            return df

        fila = resultado.iloc[0]
        print(f"Programa: {fila.get('programa', 'N/D')}")
        print(f"Estado: {fila.get('estado', 'No definido')}")
        print(f"Versión: {self._mostrar(fila.get('version', None), 'No especificada')}")
        print(f"Compatibilidad: {self._mostrar(fila.get('compatibilidad', None), 'No especificada')}")
        print(f"Tipo de licencia: {self._mostrar(fila.get('licencia', None), 'No especificada')}")
        print(f"Periodo de licenciamiento: {self._mostrar(fila.get('periodo', None), 'No definido')}")
        print(f"Descripción: {self._mostrar(fila.get('descripcion', None), 'Sin descripción')}")
        return df

    def _enviar_a_revision_interactivo(self, df: pd.DataFrame, nombre_ingresado: str) -> pd.DataFrame:
        print("\n--- Enviar aplicación a revisión ---")
        programa = input(f"Nombre del programa [{nombre_ingresado}]: ").strip() or nombre_ingresado

        version = input("Versión del programa (opcional): ").strip() or None
        compatibilidad = input("Compatibilidad (opcional, ej. Windows 10/11): ").strip() or None
        licencia = input("Tipo de licencia (opcional, ej. Licenciado / N/A / FreeTrial): ").strip() or None
        periodo = input("Periodo de licenciamiento (opcional): ").strip() or None
        descripcion = input("Descripción / comentarios (opcional): ").strip() or None

        nuevo = {
            "programa": programa,
            "version": version,
            "compatibilidad": compatibilidad,
            "licencia": licencia,
            "periodo": periodo,
            "descripcion": descripcion,
            "estado": ESTADO_REVISION,
            "fecha_revision": now_str(),
            "fecha_decision": None,
            "decision": None,
            "motivo_rechazo": None,
        }

        for col in nuevo.keys():
            if col not in df.columns:
                df[col] = None
        for col in df.columns:
            nuevo.setdefault(col, None)

        df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
        df["programa_norm"] = df["programa"].astype(str).apply(normalizar_texto)
        print("Aplicación registrada como 'En revisión'.")
        return df

    def supervisor_menu(self, df: pd.DataFrame, supervisor_pin: str) -> pd.DataFrame:
        pin = input("Ingrese PIN de supervisor: ").strip()
        if pin != supervisor_pin:
            print("PIN incorrecto. Acceso denegado.")
            return df

        for col in ["fecha_revision", "fecha_decision", "decision", "motivo_rechazo"]:
            if col not in df.columns:
                df[col] = None

        while True:
            print("\n=== MODO SUPERVISOR ===")
            print("1) Ver aplicaciones en revisión")
            print("2) Aprobar / Rechazar una solicitud")
            print("3) Salir de modo supervisor")

            opcion = input("Seleccione una opción: ").strip()

            if opcion == "1":
                en_rev = df[df["estado"].astype(str).str.strip().str.lower() == ESTADO_REVISION.lower()].copy()
                if en_rev.empty:
                    print("No hay aplicaciones en revisión.")
                else:
                    print(f"\nAplicaciones en revisión (Total: {len(en_rev)}):")
                    for i, row in en_rev.reset_index(drop=True).iterrows():
                        print(f"{i+1}. {row['programa']}")
            elif opcion == "2":
                df = self._aprobar_rechazar(df)
            elif opcion == "3":
                print("Saliendo de modo supervisor.")
                return df
            else:
                print("Opción inválida. Intente nuevamente.")

    def _aprobar_rechazar(self, df: pd.DataFrame) -> pd.DataFrame:
        en_rev = df[df["estado"].astype(str).str.strip().str.lower() == ESTADO_REVISION.lower()].copy()
        if en_rev.empty:
            print("No hay solicitudes en revisión.")
            return df

        en_rev = en_rev.reset_index()
        print(f"\nSolicitudes en revisión (Total: {len(en_rev)}):")
        for i, row in en_rev.iterrows():
            print(f"{i+1}. {row['programa']}")

        sel = input("Seleccione el número (0 para volver): ").strip()
        if sel == "0":
            return df
        if not sel.isdigit():
            print("Entrada inválida.")
            return df

        sel_num = int(sel)
        if not (1 <= sel_num <= len(en_rev)):
            print("Selección inválida.")
            return df

        fila_sel = en_rev.iloc[sel_num - 1]
        original_index = int(fila_sel["index"])

        print("\nAcción:")
        print(f"1) Aprobar ({ESTADO_PERMITIDA})")
        print(f"2) Rechazar ({ESTADO_NO_PERMITIDA})")
        print("3) Cancelar")

        acc = input("Seleccione una opción: ").strip()
        if acc == "1":
            df.loc[original_index, "estado"] = ESTADO_PERMITIDA
            df.loc[original_index, "fecha_decision"] = now_str()
            df.loc[original_index, "decision"] = "Aprobada"
            df.loc[original_index, "motivo_rechazo"] = None
            print("Solicitud aprobada.")
            return df

        if acc == "2":
            motivo = input("Motivo de rechazo (opcional): ").strip() or None
            df.loc[original_index, "estado"] = ESTADO_NO_PERMITIDA
            df.loc[original_index, "fecha_decision"] = now_str()
            df.loc[original_index, "decision"] = "Rechazada"
            df.loc[original_index, "motivo_rechazo"] = motivo
            print("Solicitud rechazada.")
            return df

        print("Acción cancelada.")
        return df

    @staticmethod
    def _mostrar(v, default: str) -> str:
        if v is None:
            return default
        try:
            if pd.isna(v):
                return default
        except Exception:
            pass
        s = str(v).strip()
        return s if s else default
