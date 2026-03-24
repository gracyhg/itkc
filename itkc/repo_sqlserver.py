import pandas as pd
from itkc.domain import normalizar_texto


class SqlServerCatalogoRepo:
    """
    Repo Supabase (PostgreSQL) alineado al esquema del proyecto.

    Tabla: aplicacion

    Mapeo app (DF) -> SQL:
      programa            -> nombre
      version             -> version
      compatibilidad      -> compatibilidad
      licencia            -> tipo_licencia
      periodo             -> periodo_licencia
      descripcion         -> descripcion
      estado              -> estado
      fecha_revision      -> fecha_solicitud
      fecha_decision      -> fecha_decision
      decision            -> decision
      motivo_rechazo      -> motivo_rechazo
    """

    def __init__(self, conn_str: str, table: str = "aplicacion"):
        self.conn_str = conn_str
        self.table = table

    def _connect(self):
        import psycopg2
        return psycopg2.connect(self.conn_str)

    def cargar(self) -> pd.DataFrame:
        query = f"""
        SELECT
            nombre,
            version,
            compatibilidad,
            tipo_licencia,
            periodo_licencia,
            descripcion,
            estado,
            fecha_solicitud,
            fecha_decision,
            decision,
            motivo_rechazo
        FROM {self.table};
        """

        with self._connect() as conn:
            df = pd.read_sql(query, conn)

        # Renombrar a los nombres estándar que usa el service
        df = df.rename(columns={
            "nombre": "programa",
            "tipo_licencia": "licencia",
            "periodo_licencia": "periodo",
            "fecha_solicitud": "fecha_revision",
        })

        # Asegurar columnas de auditoría presentes
        for col in ["fecha_revision", "fecha_decision", "decision", "motivo_rechazo"]:
            if col not in df.columns:
                df[col] = None

        # Columna auxiliar usada por búsqueda
        df["programa_norm"] = df["programa"].astype(str).apply(normalizar_texto)

        return df

    def guardar(self, df: pd.DataFrame) -> None:
        # Quitamos columna auxiliar
        df2 = df.drop(columns=["programa_norm"], errors="ignore").copy()

        def get(r, key):
            val = r.get(key) if key in r else None
            if val is not None and pd.isna(val):
                return None
            return val

        upsert_sql = f"""
        INSERT INTO {self.table} (
            nombre,
            version,
            compatibilidad,
            tipo_licencia,
            periodo_licencia,
            descripcion,
            estado,
            fecha_solicitud,
            fecha_decision,
            decision,
            motivo_rechazo,
            creado_en,
            actualizado_en
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (nombre) DO UPDATE SET
            version = EXCLUDED.version,
            compatibilidad = EXCLUDED.compatibilidad,
            tipo_licencia = EXCLUDED.tipo_licencia,
            periodo_licencia = EXCLUDED.periodo_licencia,
            descripcion = EXCLUDED.descripcion,
            estado = EXCLUDED.estado,
            fecha_solicitud = EXCLUDED.fecha_solicitud,
            fecha_decision = EXCLUDED.fecha_decision,
            decision = EXCLUDED.decision,
            motivo_rechazo = EXCLUDED.motivo_rechazo,
            actualizado_en = NOW();
        """

        with self._connect() as conn:
            cur = conn.cursor()

            for _, r in df2.iterrows():
                programa = get(r, "programa")
                if programa is None or str(programa).strip() == "":
                    continue

                params = (
                    programa,
                    get(r, "version"),
                    get(r, "compatibilidad"),
                    get(r, "licencia"),
                    get(r, "periodo"),
                    get(r, "descripcion"),
                    get(r, "estado"),
                    get(r, "fecha_revision"),
                    get(r, "fecha_decision"),
                    get(r, "decision"),
                    get(r, "motivo_rechazo"),
                )

                cur.execute(upsert_sql, params)

            conn.commit()
