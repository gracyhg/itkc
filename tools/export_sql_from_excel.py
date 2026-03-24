import os
import pandas as pd

from itkc.repo_excel import leer_excel_robusto, mapear_columnas, asegurar_columnas
from itkc.domain import normalizar_texto, ESTADO_PERMITIDA


# =========================
# RUTAS ROBUSTAS (Project Root)
# =========================
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))   # ...\Scripts\tools
SCRIPTS_DIR = os.path.dirname(TOOLS_DIR)                 # ...\Scripts
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)              # ...\IT_Knowledge_Core

EXCEL_PATH = os.path.join(PROJECT_ROOT, "Data", "Aplicaciones_permitidas.xlsx")

MIGRATIONS_DIR = os.path.join(PROJECT_ROOT, "Migrations")
os.makedirs(MIGRATIONS_DIR, exist_ok=True)

OUT_SQL = os.path.join(MIGRATIONS_DIR, "migration_aplicaciones.sql")

# Tabla real usada en tu BD (según tu script SQL actual)
TABLE = "Aplicacion"  # dbo.Aplicacion


def sql_escape(v) -> str:
    """Escapa valores para SQL Server. None/NaN -> NULL."""
    if v is None:
        return "NULL"
    # pandas NaN
    try:
        if pd.isna(v):
            return "NULL"
    except Exception:
        pass

    s = str(v)
    s = s.replace("'", "''")
    return f"N'{s}'"  # N'' para Unicode (tildes, etc.)


def main():
    # 1) Leer Excel y normalizar columnas
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"No se encontró el Excel en: {EXCEL_PATH}")

    df = leer_excel_robusto(EXCEL_PATH)
    df = mapear_columnas(df)
    df = asegurar_columnas(df)

    # 2) Defaults
    if "estado" not in df.columns:
        df["estado"] = ESTADO_PERMITIDA
    df["estado"] = df["estado"].fillna(ESTADO_PERMITIDA).astype(str).str.strip()

    # 3) Normalizado para clave
    df["nombre_norm"] = df["programa"].astype(str).apply(normalizar_texto)

    # Quitamos filas inválidas (nombre vacío)
    df = df[df["nombre_norm"].astype(str).str.strip() != ""].copy()

    # 4) Generar SQL
    lines = []
    lines.append("-- =========================================")
    lines.append("-- IT Knowledge Core | Migración Excel -> SQL Server")
    lines.append("-- Archivo generado automáticamente. Ejecutar en SQL Server.")
    lines.append("-- =========================================")
    lines.append("")
    lines.append(f"-- Excel origen: {EXCEL_PATH}")
    lines.append(f"-- Salida SQL:  {OUT_SQL}")
    lines.append(f"-- Tabla objetivo: dbo.{TABLE}")
    lines.append("")

    # Nota: NO creamos la BD aquí, solo insertamos.
    # Si quieres un CREATE TABLE adicional, se puede agregar, pero tú ya tienes dbo.Aplicacion.

    # Inserts idempotentes por 'nombre'
    # (Tu tabla dbo.Aplicacion tiene índice único por nombre según tu script)
    for _, r in df.iterrows():
        nombre = r.get("programa")
        version = r.get("version")
        compatibilidad = r.get("compatibilidad")
        tipo_licencia = r.get("licencia")
        periodo_licencia = r.get("periodo")
        descripcion = r.get("descripcion")
        estado = r.get("estado")

        # auditoría (si vienen del excel, los pasamos)
        fecha_solicitud = r.get("fecha_revision")  # tu excel usa fecha_revision
        fecha_decision = r.get("fecha_decision")
        decision = r.get("decision")
        motivo_rechazo = r.get("motivo_rechazo")

        lines.append(f"""
IF NOT EXISTS (SELECT 1 FROM dbo.{TABLE} WHERE nombre = {sql_escape(nombre)})
BEGIN
    INSERT INTO dbo.{TABLE} (
        nombre, version, compatibilidad, tipo_licencia, periodo_licencia, descripcion,
        estado, fecha_solicitud, fecha_decision, decision, motivo_rechazo
    )
    VALUES (
        {sql_escape(nombre)},
        {sql_escape(version)},
        {sql_escape(compatibilidad)},
        {sql_escape(tipo_licencia)},
        {sql_escape(periodo_licencia)},
        {sql_escape(descripcion)},
        {sql_escape(estado)},
        {sql_escape(fecha_solicitud)},
        {sql_escape(fecha_decision)},
        {sql_escape(decision)},
        {sql_escape(motivo_rechazo)}
    );
END
""".strip())
        lines.append("")

    with open(OUT_SQL, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("✅ SQL generado:", OUT_SQL)
    print("Siguiente: abre este .sql en SSMS/Azure Data Studio y ejecútalo en tu SQL Server.")


if __name__ == "__main__":
    main()
