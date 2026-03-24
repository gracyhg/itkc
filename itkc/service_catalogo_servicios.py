import pandas as pd
from itkc.domain import normalizar_texto


class CatalogoServiciosService:
    def buscar(self, df: pd.DataFrame, texto: str) -> pd.DataFrame:
        q = normalizar_texto(texto)
        if not q:
            return df.copy()

        mask = (
            df["servicio_norm"].str.contains(q, na=False)
            | df["categoria_norm"].str.contains(q, na=False)
            | df["subcategoria_norm"].str.contains(q, na=False)
        )
        return df[mask].copy()

    def agregar(self, df: pd.DataFrame, servicio: str, categoria: str, subcategoria: str) -> pd.DataFrame:
        servicio = (servicio or "").strip()
        categoria = (categoria or "").strip()
        subcategoria = (subcategoria or "").strip()

        if not servicio:
            print("❌ El campo 'servicio' es obligatorio.")
            return df

        sn = normalizar_texto(servicio)
        cn = normalizar_texto(categoria)
        scn = normalizar_texto(subcategoria)

        # evitar duplicados por triple clave (si categoría/subcategoría vienen vacías, igual cuenta)
        dup = df[
            (df["servicio_norm"] == sn)
            & (df["categoria_norm"] == cn)
            & (df["subcategoria_norm"] == scn)
        ]
        if not dup.empty:
            print("⚠️ Ya existe ese registro (servicio + categoría + subcategoría).")
            return df

        nuevo = {
            "servicio": servicio,
            "categoria": categoria,
            "subcategoria": subcategoria,
            "servicio_norm": sn,
            "categoria_norm": cn,
            "subcategoria_norm": scn,
        }
        df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
        print("✅ Servicio agregado.")
        return df

    def eliminar_por_indice(self, df: pd.DataFrame, idx: int) -> pd.DataFrame:
        if idx < 0 or idx >= len(df):
            print("❌ Índice fuera de rango.")
            return df

        row = df.iloc[idx]
        print(f"Eliminando: {row['servicio']} | {row['categoria']} > {row['subcategoria']}")
        df2 = df.drop(df.index[idx]).reset_index(drop=True)
        print("✅ Servicio eliminado.")
        return df2
