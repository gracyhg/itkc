import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    backend: str
    excel_path: str
    supervisor_pin: str
    sqlserver_conn_str: str

def load_settings(base_dir: str) -> Settings:
    # Excel path: asume ../Data/Aplicaciones_permitidas.xlsx desde Scripts/
    excel_default = os.path.join(base_dir, "..", "Data", "Aplicaciones_permitidas.xlsx")

    return Settings(
        backend=os.getenv("ITKC_BACKEND", "excel").strip().lower(),
        excel_path=os.getenv("ITKC_EXCEL_PATH", excel_default).strip(),
        supervisor_pin=os.getenv("ITKC_SUPERVISOR_PIN", "1234").strip(),
        sqlserver_conn_str=os.getenv("ITKC_SQLSERVER_CONN_STR", "").strip(),
    )
