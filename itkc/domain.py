import re
from datetime import datetime

ESTADO_PERMITIDA = "Permitida"
ESTADO_REVISION = "En revisión"
ESTADO_NO_PERMITIDA = "No permitida"

ESTADOS_VALIDOS = {ESTADO_PERMITIDA, ESTADO_REVISION, ESTADO_NO_PERMITIDA}

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def normalizar_texto(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s
