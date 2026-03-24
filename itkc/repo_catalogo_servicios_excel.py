import os
import pandas as pd
from itkc.domain import normalizar_texto


class ExcelCatalogoServiciosRepo:
    REQUIRED = ["servicio", "categoria", "subcategoria"]

    # variantes típicas de encabezados (con y sin tildes, plural, etc.)
    RENAME_MAP = {
        "servicios": "servicio",
        "servicio": "servicio",

        "categoría": "categoria",
        "categoria": "categoria",

        "subcategoría": "subcategoria",
        "subcategoria": "subcategoria",
    }

    def __init__(self, excel_path: str):
        self.excel_path = excel_path

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.excel_path), exist_ok=True)
        if not os.path.exists(self.excel_path):
            df = pd.DataFrame(columns=self.REQUIRED)
            df.to_excel(self.excel_path, index=False)

    def cargar(self) -> pd.DataFrame:
        self._ensure_file()

        df = pd.read_excel(self.excel_path, header=0)
        df.columns = df.columns.astype(str).str.strip().str.lower()

        # Renombrar columnas según variantes conocidas
        df = df.rename(columns=self.RENAME_MAP)

        # Si alguna requerida no existe, la creamos vacía
        for c in self.REQUIRED:
            if c not in df.columns:
                df[c] = ""

        # Mantener SOLO las columnas requeridas (y en orden estándar)
        df = df[self.REQUIRED].copy()

        # limpiar
        for c in self.REQUIRED:
            df[c] = df[c].astype(str).fillna("").str.strip()

        # eliminar filas totalmente vacías
        df = df[(df["servicio"] != "") | (df["categoria"] != "") | (df["subcategoria"] != "")].copy()

        # normalizados para búsqueda/duplicados
        df["servicio_norm"] = df["servicio"].apply(normalizar_texto)
        df["categoria_norm"] = df["categoria"].apply(normalizar_texto)
        df["subcategoria_norm"] = df["subcategoria"].apply(normalizar_texto)

        # eliminar inválidos: servicio vacío (porque es el identificador)
        df = df[df["servicio_norm"] != ""].copy()

        return df

    def guardar(self, df: pd.DataFrame) -> None:
        df_guardar = df.drop(
            columns=["servicio_norm", "categoria_norm", "subcategoria_norm"],
            errors="ignore"
        ).copy()

        try:
            df_guardar.to_excel(self.excel_path, index=False)
        except PermissionError:
            raise PermissionError(
                "No se pudo guardar el Excel del catálogo. Cierra el archivo si está abierto."
            )
