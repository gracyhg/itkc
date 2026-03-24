import pandas as pd
from .domain import ESTADO_PERMITIDA, normalizar_texto

def leer_excel_robusto(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, header=1)
    df.columns = df.columns.astype(str).str.lower().str.strip()

    if "programas" not in df.columns and "programa" not in df.columns:
        df = pd.read_excel(path, header=0)
        df.columns = df.columns.astype(str).str.lower().str.strip()

    return df

def mapear_columnas(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={
        "programas": "programa",
        "programa": "programa",
        "versión del programa": "version",
        "version del programa": "version",
        "compatibilidad": "compatibilidad",
        "tipo de licencia": "licencia",
        "periodo de licenciamiento": "periodo",
        "período de licenciamiento": "periodo",
        "descripción del software": "descripcion",
        "descripcion del software": "descripcion",
        "estado": "estado",
        "fecha revisión": "fecha_revision",
        "fecha revision": "fecha_revision",
        "fecha decisión": "fecha_decision",
        "fecha decision": "fecha_decision",
        "motivo rechazo": "motivo_rechazo",
    })

def asegurar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    if "programa" not in df.columns:
        raise ValueError(f"No se encontró 'programa'. Columnas: {df.columns.tolist()}")

    df = df[df["programa"].notna() & (df["programa"].astype(str).str.strip() != "")].copy()

    if "estado" not in df.columns:
        df["estado"] = ESTADO_PERMITIDA
    else:
        df["estado"] = df["estado"].fillna(ESTADO_PERMITIDA).astype(str).str.strip()

    for col in ["fecha_revision", "fecha_decision", "decision", "motivo_rechazo"]:
        if col not in df.columns:
            df[col] = None

    df["programa_norm"] = df["programa"].astype(str).apply(normalizar_texto)
    return df

class ExcelCatalogoRepo:
    def __init__(self, ruta_excel: str):
        self.ruta_excel = ruta_excel

    def cargar(self) -> pd.DataFrame:
        df = leer_excel_robusto(self.ruta_excel)
        df = mapear_columnas(df)
        df = asegurar_columnas(df)
        return df

    def guardar(self, df: pd.DataFrame) -> None:
        df_guardar = df.drop(columns=["programa_norm"], errors="ignore")
        try:
            df_guardar.to_excel(self.ruta_excel, index=False)
        except PermissionError:
            raise PermissionError(
                "No se pudo guardar el Excel. Está abierto/bloqueado. Cierra el archivo y reintenta."
            )
