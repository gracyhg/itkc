import os
import pandas as pd

from itkc.service import AplicacionesService
from itkc.domain import ESTADO_REVISION, ESTADO_PERMITIDA, ESTADO_NO_PERMITIDA, normalizar_texto

def make_df():
    # DF mínimo con columnas requeridas por el service
    df = pd.DataFrame([
        {
            "programa": "Google Chrome",
            "version": "120",
            "compatibilidad": "Windows 10/11",
            "licencia": "Free",
            "periodo": None,
            "descripcion": "Browser",
            "estado": ESTADO_PERMITIDA,
            "fecha_revision": None,
            "fecha_decision": None,
            "decision": None,
            "motivo_rechazo": None,
        },
        {
            "programa": "App X",
            "version": None,
            "compatibilidad": None,
            "licencia": None,
            "periodo": None,
            "descripcion": None,
            "estado": ESTADO_REVISION,
            "fecha_revision": "2026-01-01 10:00:00",
            "fecha_decision": None,
            "decision": None,
            "motivo_rechazo": None,
        }
    ])
    df["programa_norm"] = df["programa"].astype(str).apply(normalizar_texto)
    return df

def run():
    svc = AplicacionesService()
    df = make_df()

    # 1) Normalización no vacía
    assert normalizar_texto("  Google  Chrome!! ") == "googlechrome"

    # 2) Consulta exacta no modifica DF
    before = df.copy()
    df2 = svc.consultar(df, "Google Chrome")
    assert len(df2) == len(before)

    # 3) Consulta con múltiples coincidencias no revienta
    df3 = svc.consultar(df, "app")
    assert isinstance(df3, pd.DataFrame)

    # Nota: el envío a revisión es interactivo (input). No lo testeamos aquí.
    # Lo que sí testeamos es que DF mantiene esquema mínimo:
    required_cols = {"programa","estado","programa_norm","fecha_revision","fecha_decision","decision","motivo_rechazo"}
    assert required_cols.issubset(set(df.columns))

    print("✅ Smoke tests OK")

if __name__ == "__main__":
    run()
