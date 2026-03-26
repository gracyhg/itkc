import os
import sys
import pandas as pd
import streamlit as st
from datetime import datetime

# =========================
# IDENTIDAD DEL MÓDULO (reutilizable)
# =========================
APP_TITLE = "IT Knowledge Core"
MODULE_TITLE = "Aplicaciones Permitidas"
DATA_FILENAME = "Aplicaciones_permitidas.xlsx"

# =========================
# RUTAS (CORRECTAS)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Funciona tanto local como en Streamlit Cloud
for path in [
    os.path.abspath(os.path.join(BASE_DIR, "..")),      # Streamlit Cloud
    os.path.abspath(os.path.join(BASE_DIR, "..", "..")), # Local
]:
    if path not in sys.path:
        sys.path.insert(0, path)

PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
SCRIPTS_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

from itkc.config import load_settings
from itkc.repo_excel import ExcelCatalogoRepo
from itkc.repo_sqlserver import SqlServerCatalogoRepo
from itkc.domain import (
    normalizar_texto,
    ESTADO_PERMITIDA,
    ESTADO_REVISION,
    ESTADO_NO_PERMITIDA
)

# -------------------------
# Build repo según backend
# -------------------------

def build_repo(settings):
    if settings.backend == "sqlserver":
        if not settings.sqlserver_conn_str:
            raise ValueError("Backend SQL Server seleccionado pero falta ITKC_SQLSERVER_CONN_STR.")
        return SqlServerCatalogoRepo(settings.sqlserver_conn_str)
    # default: excel
    excel_path = os.path.join(PROJECT_ROOT, "Data", DATA_FILENAME)
    return ExcelCatalogoRepo(excel_path)

# -------------------------
# Helpers
# -------------------------

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_str(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
        return ""
    return str(v)

def asegurar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    columnas = [
        "programa", "programa_norm", "version", "compatibilidad",
        "licencia", "periodo", "descripcion", "estado",
        "fecha_revision", "fecha_decision", "decision", "motivo_rechazo"
    ]
    for c in columnas:
        if c not in df.columns:
            df[c] = None
    df["programa_norm"] = df["programa"].astype(str).apply(normalizar_texto)
    return df

def guardar_y_recargar(repo, df):
    repo.guardar(df)
    return repo.cargar()

def existe_programa_norm(df, programa_norm):
    return (df["programa_norm"] == programa_norm).any()

def eliminar_aplicacion(df, programa_norm):
    return df[df["programa_norm"] != programa_norm].copy()

def actualizar_decision(df, programa_norm, aprobar=True, motivo=None):
    df2 = df.copy()
    mask = df2["programa_norm"] == programa_norm
    if not mask.any():
        return df2
    idx = df2[mask].index[0]
    df2.loc[idx, "estado"] = ESTADO_PERMITIDA if aprobar else ESTADO_NO_PERMITIDA
    df2.loc[idx, "decision"] = "Aprobada" if aprobar else "Rechazada"
    df2.loc[idx, "fecha_decision"] = now_str()
    df2.loc[idx, "motivo_rechazo"] = motivo if not aprobar else None
    return df2

# -------------------------
# UI Helpers
# -------------------------

def show_success(msg: str):
    st.success(msg)
    try:
        st.toast(msg)
    except Exception:
        pass

def show_info_header(role_title: str, caption: str):
    st.markdown(f"## {role_title}")
    st.caption(caption)
    st.divider()
def verificar_login(correo: str, password: str, conn_str: str) -> dict | None:
    import psycopg2, hashlib
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        cur.execute(
            "SELECT correo, rol FROM usuarios WHERE correo=%s AND password_hash=md5(%s) AND activo=TRUE",
            (correo, password)
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return {"correo": row[0], "rol": row[1]}
        return None
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None
    

def render_login(settings):
    import base64

    bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bg.jpg")
    bg_b64 = ""
    if os.path.exists(bg_path):
        with open(bg_path, "rb") as f:
            bg_b64 = base64.b64encode(f.read()).decode()

    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.jpg")
    logo_b64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Inter:wght@300;400;500&display=swap');

    html, body, [data-testid="stAppViewContainer"], .stApp {{
        background-image: url("data:image/jpeg;base64,{bg_b64}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }}

    [data-testid="stAppViewContainer"]::before {{
        content: '';
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.55);
        z-index: 0;
    }}

    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .stApp > header,
    header, #MainMenu, footer {{
        display: none !important;
        height: 0 !important;
    }}

    .stApp {{ margin-top: 0 !important; }}
    .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        position: relative;
        z-index: 1;
    }}

    /* Glassmorphism en la columna del centro */
    [data-testid="column"]:nth-child(2) {{
        background: rgba(10, 20, 10, 0.55) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border: 1px solid rgba(122, 196, 122, 0.15) !important;
        border-top: 2px solid #7AC47A !important;
        border-radius: 12px !important;
        padding: 36px 32px !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 60px rgba(122,196,122,0.05) !important;
    }}

    .stTextInput > div > div > input {{
        background: rgba(122, 196, 122, 0.04) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(122,196,122,0.2) !important;
        border-radius: 6px !important;
        color: #E0E0E0 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
        padding: 10px 14px !important;
    
    }}
    .stTextInput > div > div > input:focus {{
        border-color: #7AC47A !important;
        box-shadow: 0 0 0 1px rgba(122,196,122,0.3) !important;
        background-color: rgba(122,196,122,0.05) !important;
    }}
    .stTextInput > div > div > input::placeholder {{
        color: #404040 !important;
    }}
    .stTextInput label {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 10px !important;
        font-weight: 500 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        color: #B0B0B0 !important;
    }}

    div[data-testid="stButton"] button {{
        background-color: transparent !important;
        color: #7AC47A !important;
        border: 1px solid #7AC47A !important;
        border-radius: 6px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        padding: 8px 16px !important;
        width: 100% !important;
        transition: all 0.2s !important;
    }}
    div[data-testid="stButton"] button:hover {{
        background-color: #7AC47A !important;
        color: #0a0a0a !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    col_izq, col_centro, col_der = st.columns([1, 1.2, 1])

    with col_centro:
        # Logo
        if logo_b64:
            st.markdown(f'<img src="data:image/jpeg;base64,{logo_b64}" style="height:70px;border-radius:6px;margin-bottom:16px;">', unsafe_allow_html=True)

        st.markdown("""
            <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#7AC47A;
                 letter-spacing:3px;text-transform:uppercase;margin:16px 0 12px 0;opacity:0.9;">
                &gt; secure access portal
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;
                 color:#F0F0F0;margin-bottom:6px;">
                IT Knowledge Core
            </div>
            <div style="font-family:'Inter',sans-serif;font-size:12px;color:#AAAAAA;margin-bottom:24px;">
                Ingresa con tu cuenta corporativa @techcrg.com
            </div>
        """, unsafe_allow_html=True)

        correo = st.text_input("Correo", key="login_correo", placeholder="usuario@techcrg.com")
        password = st.text_input("Contraseña", type="password", key="login_password", placeholder="••••••••")

        if st.button("→ Iniciar sesión"):
            if not correo.endswith("@techcrg.com"):
                st.error("Solo se permiten correos @techcrg.com")
                return
            usuario = verificar_login(correo, password, settings.sqlserver_conn_str)
            if usuario:
                st.session_state.usuario = usuario
                st.session_state.pantalla = "app"
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")

        st.markdown("<hr style='border:none;border-top:1px solid rgba(122,196,122,0.1);margin:20px 0'>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        if col1.button("Crear cuenta"):
            st.session_state.pantalla = "registro"
            st.rerun()
        if col2.button("Olvidé contraseña"):
            st.session_state.pantalla = "olvide_password"
            st.rerun()

        st.markdown("""
            <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#707070;
            text-align:center;margin-top:16px;letter-spacing:1px;">
            CRG Solutions © 2026 · Acceso restringido</div>
        """, unsafe_allow_html=True)
           
       
    
  
# -------------------------
# REGISTRO
# -------------------------
def enviar_correo_verificacion(correo: str, token: str, api_key: str, from_email: str):
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    verify_url = f"https://itkcapp.streamlit.app?verify={token}"

    mensaje = Mail(
        from_email=from_email,
        to_emails=correo,
        subject="Verifica tu cuenta - IT Knowledge Core",
        html_content=f"""
        <p>Gracias por registrarte en IT Knowledge Core.</p>
        <p>Haz clic en el siguiente enlace para verificar tu cuenta:</p>
        <p><a href="{verify_url}">Verificar cuenta</a></p>
        <p>Este enlace expira en 24 horas.</p>
        """
    )

    sg = SendGridAPIClient(api_key)
    sg.send(mensaje)


def render_registro(settings):
    st.title(" IT Knowledge Core")
    st.subheader("Crear cuenta")

    correo = st.text_input("Correo corporativo", key="reg_correo")
    password = st.text_input("Contraseña", type="password", key="reg_password")
    password2 = st.text_input("Confirmar contraseña", type="password", key="reg_password2")

    if st.button("Registrarse"):
        if not correo.endswith("@techcrg.com"):
            st.error("Solo se permiten correos @techcrg.com")
            return
        if len(password) < 8:
            st.error("La contraseña debe tener al menos 8 caracteres.")
            return
        if password != password2:
            st.error("Las contraseñas no coinciden.")
            return

        import psycopg2
        try:
            conn = psycopg2.connect(settings.sqlserver_conn_str)
            cur = conn.cursor()

            # Verificar si ya existe
            cur.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
            if cur.fetchone():
                st.error("Ya existe una cuenta con ese correo.")
                conn.close()
                return

            import uuid
            token_verificacion = str(uuid.uuid4())

            cur.execute(
               "INSERT INTO usuarios (correo, password_hash, rol, activo) VALUES (%s, md5(%s), 'agente', FALSE)",
               (correo, password)
)
            cur.execute(
               "INSERT INTO password_reset_tokens (correo, token, expira_en) VALUES (%s, %s, NOW() + INTERVAL '24 hours')",
               (correo, token_verificacion)
)
            conn.commit()
            conn.close()

            # Enviar correo de verificación
            api_key = os.getenv("SENDGRID_API_KEY", "")
            from_email = os.getenv("SENDGRID_FROM_EMAIL", "")
            enviar_correo_verificacion(correo, token_verificacion, api_key, from_email)

            st.success("✅ Revisa tu correo para verificar tu cuenta.")
            st.session_state.pantalla = "login"
            st.rerun()

            conn.commit()
            conn.close()
            st.success(" Cuenta creada correctamente. Ya puedes iniciar sesión.")
            st.session_state.pantalla = "login"
            st.rerun()
        except Exception as e:
            st.error(f"Error al registrar: {e}")

    st.divider()
    if st.button("← Volver al login"):
        st.session_state.pantalla = "login"
        st.rerun()


# -------------------------
# RECUPERAR CONTRASEÑA
# -------------------------

def enviar_correo_reset(correo: str, token: str, api_key: str, from_email: str):
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    reset_url = f"https://itkcapp.streamlit.app?token={token}"

    mensaje = Mail(
        from_email=from_email,
        to_emails=correo,
        subject="Recuperación de contraseña - IT Knowledge Core",
        html_content=f"""
        <p>Recibimos una solicitud para restablecer tu contraseña.</p>
        <p>Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
        <p><a href="{reset_url}">Restablecer contraseña</a></p>
        <p>Este enlace expira en 30 minutos.</p>
        <p>Si no solicitaste esto, ignora este correo.</p>
        """
    )

    sg = SendGridAPIClient(api_key)
    sg.send(mensaje)


def render_olvide_password(settings):
    st.title(" IT Knowledge Core")
    st.subheader("Recuperar contraseña")

    correo = st.text_input("Ingresa tu correo corporativo", key="reset_correo")

    if st.button("Enviar correo de recuperación"):
        if not correo.endswith("@techcrg.com"):
            st.error("Solo se permiten correos @techcrg.com")
            return

        import psycopg2, uuid, hashlib
        from datetime import timedelta

        try:
            conn = psycopg2.connect(settings.sqlserver_conn_str)
            cur = conn.cursor()

            # Verificar si el correo existe
            cur.execute("SELECT id FROM usuarios WHERE correo = %s AND activo = TRUE", (correo,))
            if not cur.fetchone():
                st.error("No existe una cuenta con ese correo.")
                conn.close()
                return

            # Crear token
            token = str(uuid.uuid4())
            expira = datetime.now() + timedelta(minutes=30)

            cur.execute(
                "INSERT INTO password_reset_tokens (correo, token, expira_en) VALUES (%s, %s, %s)",
                (correo, token, expira)
            )
            conn.commit()
            conn.close()

            # Enviar correo
            api_key = os.getenv("SENDGRID_API_KEY", "")
            from_email = os.getenv("SENDGRID_FROM_EMAIL", "")
            enviar_correo_reset(correo, token, api_key, from_email)

            st.success("✅ Correo enviado. Revisa tu bandeja de entrada.")

        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    if st.button("← Volver al login"):
        st.session_state.pantalla = "login"
        st.rerun()


def render_nueva_password(token: str, settings):
    st.title(" IT Knowledge Core")
    st.subheader("Nueva contraseña")

    import psycopg2

    # Verificar token
    try:
        conn = psycopg2.connect(settings.sqlserver_conn_str)
        cur = conn.cursor()
        cur.execute(
            "SELECT correo FROM password_reset_tokens WHERE token=%s AND usado=FALSE AND expira_en > NOW()",
            (token,)
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            st.error("El enlace es inválido o ha expirado.")
            return

        correo = row[0]

    except Exception as e:
        st.error(f"Error: {e}")
        return

    password = st.text_input("Nueva contraseña", type="password", key="new_pass")
    password2 = st.text_input("Confirmar contraseña", type="password", key="new_pass2")

    if st.button("Guardar nueva contraseña"):
        if len(password) < 8:
            st.error("La contraseña debe tener al menos 8 caracteres.")
            return
        if password != password2:
            st.error("Las contraseñas no coinciden.")
            return

        try:
            conn = psycopg2.connect(settings.sqlserver_conn_str)
            cur = conn.cursor()

            cur.execute(
                "UPDATE usuarios SET password_hash = md5(%s) WHERE correo = %s",
                (password, correo)
            )
            cur.execute(
                "UPDATE password_reset_tokens SET usado = TRUE WHERE token = %s",
                (token,)
            )
            conn.commit()
            conn.close()

            st.success(" Contraseña actualizada. Ya puedes iniciar sesión.")
            st.session_state.pantalla = "login"
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")            

# -------------------------
# PANTALLA AGENTE
# -------------------------

def render_agente(df, repo):
    st.header("👤 Agente | Consulta")

    consulta = st.text_input("Buscar por nombre", key="q_buscar").strip()

    if "mostrar_form_revision" not in st.session_state:
        st.session_state.mostrar_form_revision = False

    if st.button("Buscar", key="btn_buscar"):
        st.session_state["last_query"] = consulta
        st.session_state.mostrar_form_revision = False

    q_raw = st.session_state.get("last_query", "").strip()

    if q_raw:
        q = normalizar_texto(q_raw)
        df_f = df[df["programa_norm"].str.contains(q, na=False)].copy()

        if df_f.empty:
            st.error("No existe en el catálogo.")

            if st.button("📩 Solicitar revisión", key="btn_show_form"):
                st.session_state.mostrar_form_revision = True

            if st.session_state.mostrar_form_revision:
                with st.form("form_revision", clear_on_submit=True):
                    st.markdown("### Enviar solicitud a revisión")
                    programa_rev = st.text_input("Nombre del programa", value=q_raw)
                    version_rev = st.text_input("Versión (opcional)")
                    compat_rev = st.text_input("Compatibilidad (opcional)")
                    lic_rev = st.text_input("Tipo de licencia (opcional)")
                    per_rev = st.text_input("Periodo (opcional)")
                    desc_rev = st.text_area("Descripción / comentarios (opcional)")

                    submit_rev = st.form_submit_button("Enviar a revisión")

                    if submit_rev:
                        if not programa_rev.strip():
                            st.error("El nombre del programa es obligatorio.")
                        else:
                            p_norm = normalizar_texto(programa_rev)
                            if existe_programa_norm(df, p_norm):
                                st.error("Ya existe una aplicación con ese nombre (normalizado).")
                            else:
                                nuevo = {
                                    "programa": programa_rev.strip(),
                                    "programa_norm": p_norm,
                                    "version": version_rev.strip() or None,
                                    "compatibilidad": compat_rev.strip() or None,
                                    "licencia": lic_rev.strip() or None,
                                    "periodo": per_rev.strip() or None,
                                    "descripcion": desc_rev.strip() or None,
                                    "estado": ESTADO_REVISION,
                                    "fecha_revision": now_str(),
                                    "fecha_decision": None,
                                    "decision": None,
                                    "motivo_rechazo": None
                                }
                                df2 = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
                                try:
                                    df2 = guardar_y_recargar(repo, df2)
                                    st.session_state.df = asegurar_columnas(df2)
                                    show_success("✅ Enviado a revisión y guardado.")
                                    st.session_state["last_query"] = ""
                                    st.session_state.mostrar_form_revision = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"No se pudo guardar: {e}")
        else:
            st.success(f"{len(df_f)} resultado(s) encontrado(s).")
            st.dataframe(df_f.drop(columns=["programa_norm"], errors="ignore"), use_container_width=True)

    st.divider()
    st.subheader(" Catálogo completo")
    st.dataframe(df.drop(columns=["programa_norm"], errors="ignore"), use_container_width=True)


# -------------------------
# PANTALLA SUPERVISOR
# -------------------------

def render_supervisor(df: pd.DataFrame, repo, settings):
    show_info_header(
        " Supervisor | Panel de Gobierno",
        "Aprueba/rechaza solicitudes y administra el catálogo (agregar/editar/eliminar)."
    )

    with st.expander(" Acceso Supervisor", expanded=True):
        pin = st.text_input("PIN Supervisor", type="password", key="pin_supervisor")
        if not pin:
            st.info("Ingresa el PIN para desbloquear el panel.")
            return
        if pin != settings.supervisor_pin:
            st.error("PIN incorrecto.")
            return

    show_success("Panel desbloqueado ")

    df_all = asegurar_columnas(st.session_state.df)
    en_rev = df_all[df_all["estado"] == ESTADO_REVISION].copy()

    st.markdown("###  Resumen")
    c1, c2, c3 = st.columns(3)
    c1.metric("Solicitudes en revisión", int(len(en_rev)))
    c2.metric("Total en catálogo", int(len(df_all)))
    c3.metric("Permitidas", int((df_all["estado"] == ESTADO_PERMITIDA).sum()))
    st.divider()

    sup_tab1, sup_tab2 = st.tabs([" Solicitudes en revisión", " Gestión del catálogo"])

    with sup_tab1:
        st.markdown("###  Bandeja de revisión")
        df_all = asegurar_columnas(st.session_state.df)
        en_rev = df_all[df_all["estado"] == ESTADO_REVISION].copy()

        if en_rev.empty:
            st.info("No hay solicitudes en revisión.")
        else:
            en_rev = en_rev.sort_values("programa").reset_index(drop=True)
            opciones = [f"{r['programa']} ({r['programa_norm']})" for _, r in en_rev.iterrows()]
            sel = st.selectbox("Seleccionar solicitud", opciones, key="sel_revision")
            programa_norm_sel = sel.split("(")[-1].replace(")", "").strip()

            fila = en_rev[en_rev["programa_norm"] == programa_norm_sel].iloc[0]
            st.markdown("####  Detalle")

            programa = safe_str(fila.get("programa"))
            estado = safe_str(fila.get("estado"))
            version = safe_str(fila.get("version")) or "No especificada"
            compat = safe_str(fila.get("compatibilidad")) or "No especificada"
            licencia = safe_str(fila.get("licencia")) or "No especificada"
            periodo = safe_str(fila.get("periodo")) or "No definido"
            descripcion = safe_str(fila.get("descripcion")) or "Sin descripción"
            fecha = safe_str(fila.get("fecha_revision")) or "No registrada"

            estado_color = "#7AC47A" if estado == "Permitida" else "#FFB347" if estado == "En revisión" else "#FF6B6B"

            st.markdown(f"""
<div style="
    background: rgba(122,196,122,0.04);
    border: 1px solid rgba(122,196,122,0.15);
    border-left: 3px solid {estado_color};
    border-radius: 6px;
    padding: 20px 24px;
    margin-bottom: 16px;
">
    <div style="font-size:20px;font-weight:700;color:#F0F0F0;margin-bottom:4px;">{programa}</div>
    <div style="display:inline-block;background:{estado_color}22;border:1px solid {estado_color}44;
         color:{estado_color};font-size:11px;padding:2px 10px;border-radius:4px;margin-bottom:16px;">
         {estado}
    </div>
    <table style="width:100%;border-collapse:collapse;">
        <tr>
            <td style="color:#888;font-size:11px;padding:5px 0;width:40%;">Versión</td>
            <td style="color:#D0D0D0;font-size:12px;padding:5px 0;">{version}</td>
        </tr>
        <tr>
            <td style="color:#888;font-size:11px;padding:5px 0;">Compatibilidad</td>
            <td style="color:#D0D0D0;font-size:12px;padding:5px 0;">{compat}</td>
        </tr>
        <tr>
            <td style="color:#888;font-size:11px;padding:5px 0;">Licencia</td>
            <td style="color:#D0D0D0;font-size:12px;padding:5px 0;">{licencia}</td>
        </tr>
        <tr>
            <td style="color:#888;font-size:11px;padding:5px 0;">Periodo</td>
            <td style="color:#D0D0D0;font-size:12px;padding:5px 0;">{periodo}</td>
        </tr>
        <tr>
            <td style="color:#888;font-size:11px;padding:5px 0;">Descripción</td>
            <td style="color:#D0D0D0;font-size:12px;padding:5px 0;">{descripcion}</td>
        </tr>
        <tr>
            <td style="color:#888;font-size:11px;padding:5px 0;">Fecha solicitud</td>
            <td style="color:#D0D0D0;font-size:12px;padding:5px 0;">{fecha}</td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

            motivo = st.text_input("Motivo rechazo (solo si rechaza)", key="motivo_rechazo")

            col1, col2 = st.columns(2)
            if col1.button(" Aprobar", key="btn_aprobar", use_container_width=True):
                df2 = actualizar_decision(df_all, programa_norm_sel, True)
                df2 = guardar_y_recargar(repo, df2)
                st.session_state.df = asegurar_columnas(df2)
                show_success(" Solicitud aprobada y guardada.")
                st.rerun()

            if col2.button(" Rechazar", key="btn_rechazar", use_container_width=True):
                df2 = actualizar_decision(df_all, programa_norm_sel, False, motivo)
                df2 = guardar_y_recargar(repo, df2)
                st.session_state.df = asegurar_columnas(df2)
                show_success(" Solicitud rechazada y guardada.")
                st.rerun()

            with st.expander("Ver todas las solicitudes en revisión"):
                st.dataframe(en_rev.drop(columns=["programa_norm"], errors="ignore"), use_container_width=True)

    with sup_tab2:
        st.markdown("### Administración del catálogo")
        st.caption(f"Backend activo: {settings.backend}")

        gestion_tab1, gestion_tab2, gestion_tab3 = st.tabs([" Agregar", " Editar", " Eliminar"])

        with gestion_tab1:
            st.markdown("####  Agregar aplicación")
            df_all = asegurar_columnas(st.session_state.df)

            with st.form("form_add_app", clear_on_submit=True):
                programa = st.text_input("Nombre (obligatorio)", key="add_programa")
                estado = st.selectbox("Estado", [ESTADO_PERMITIDA, ESTADO_REVISION, ESTADO_NO_PERMITIDA], key="add_estado")
                version = st.text_input("Versión", key="add_version")
                compat = st.text_input("Compatibilidad", key="add_compat")
                lic = st.text_input("Licencia", key="add_lic")
                per = st.text_input("Periodo", key="add_per")
                desc = st.text_area("Descripción", key="add_desc")
                submit_add = st.form_submit_button("Guardar nuevo")

                if submit_add:
                    df_all = asegurar_columnas(st.session_state.df)
                    if not programa.strip():
                        st.error("Nombre obligatorio.")
                    else:
                        p_norm = normalizar_texto(programa)
                        if existe_programa_norm(df_all, p_norm):
                            st.error("Ya existe una aplicación con ese nombre.")
                        else:
                            nuevo = {
                                "programa": programa.strip(),
                                "programa_norm": p_norm,
                                "version": version.strip() or None,
                                "compatibilidad": compat.strip() or None,
                                "licencia": lic.strip() or None,
                                "periodo": per.strip() or None,
                                "descripcion": desc.strip() or None,
                                "estado": estado,
                                "fecha_revision": now_str() if estado == ESTADO_REVISION else None,
                                "fecha_decision": None,
                                "decision": None,
                                "motivo_rechazo": None
                            }
                            df2 = pd.concat([df_all, pd.DataFrame([nuevo])], ignore_index=True)
                            df2 = guardar_y_recargar(repo, df2)
                            st.session_state.df = asegurar_columnas(df2)
                            show_success(" Agregado y guardado.")
                            st.rerun()

        with gestion_tab2:
            st.markdown("####  Editar aplicación")
            df_all = asegurar_columnas(st.session_state.df).sort_values("programa").reset_index(drop=True)

            if df_all.empty:
                st.info("El catálogo está vacío.")
            else:
                opciones = [f"{r['programa']} ({r['programa_norm']})" for _, r in df_all.iterrows()]
                sel = st.selectbox("Seleccionar", opciones, key="edit_sel")
                sel_norm = sel.split("(")[-1].replace(")", "").strip()

                fila = df_all[df_all["programa_norm"] == sel_norm].iloc[0]

                with st.form("form_edit_app"):
                    programa_new = st.text_input("Nombre", value=safe_str(fila.get("programa")), key="edit_programa")
                    estado_new = st.selectbox(
                        "Estado",
                        [ESTADO_PERMITIDA, ESTADO_REVISION, ESTADO_NO_PERMITIDA],
                        index=[ESTADO_PERMITIDA, ESTADO_REVISION, ESTADO_NO_PERMITIDA].index(
                            safe_str(fila.get("estado")) or ESTADO_PERMITIDA
                        ),
                        key="edit_estado"
                    )
                    version_new = st.text_input("Versión", value=safe_str(fila.get("version")), key="edit_version")
                    compat_new = st.text_input("Compatibilidad", value=safe_str(fila.get("compatibilidad")), key="edit_compat")
                    lic_new = st.text_input("Licencia", value=safe_str(fila.get("licencia")), key="edit_lic")
                    per_new = st.text_input("Periodo", value=safe_str(fila.get("periodo")), key="edit_per")
                    desc_new = st.text_area("Descripción", value=safe_str(fila.get("descripcion")), key="edit_desc")
                    submit_edit = st.form_submit_button("Guardar cambios")

                    if submit_edit:
                        df2 = df_all.copy()
                        new_norm = normalizar_texto(programa_new)
                        if new_norm != sel_norm and existe_programa_norm(df2, new_norm):
                            st.error("No se puede renombrar: ya existe otra aplicación con ese nombre.")
                        else:
                            mask = df2["programa_norm"] == sel_norm
                            df2.loc[mask, "programa"] = programa_new.strip()
                            df2.loc[mask, "estado"] = estado_new
                            df2.loc[mask, "version"] = version_new.strip() or None
                            df2.loc[mask, "compatibilidad"] = compat_new.strip() or None
                            df2.loc[mask, "licencia"] = lic_new.strip() or None
                            df2.loc[mask, "periodo"] = per_new.strip() or None
                            df2.loc[mask, "descripcion"] = desc_new.strip() or None
                            df2["programa_norm"] = df2["programa"].astype(str).apply(normalizar_texto)
                            df2 = guardar_y_recargar(repo, df2)
                            st.session_state.df = asegurar_columnas(df2)
                            show_success(" Actualizado y guardado.")
                            st.rerun()

        with gestion_tab3:
            st.markdown("####  Eliminar aplicación")
            df_all = asegurar_columnas(st.session_state.df).sort_values("programa").reset_index(drop=True)

            if df_all.empty:
                st.info("El catálogo está vacío.")
            else:
                opciones = [f"{r['programa']} ({r['programa_norm']})" for _, r in df_all.iterrows()]
                sel = st.selectbox("Eliminar", opciones, key="del_sel")
                sel_norm = sel.split("(")[-1].replace(")", "").strip()

                st.warning("Esta acción elimina el registro permanentemente.")
                with st.form("form_delete_app", clear_on_submit=True):
                    confirm = st.text_input("Escriba ELIMINAR para confirmar", key="del_confirm")
                    submit_del = st.form_submit_button("Eliminar definitivamente")

                    if submit_del:
                        if confirm.strip().upper() == "ELIMINAR":
                            df2 = eliminar_aplicacion(df_all, sel_norm)
                            df2 = guardar_y_recargar(repo, df2)
                            st.session_state.df = asegurar_columnas(df2)
                            show_success(" Eliminado y guardado.")
                            st.rerun()
                        else:
                            st.error("Confirmación inválida.")

# -------------------------
# App principal
# -------------------------
def apply_global_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Inter:wght@300;400;500;600&display=swap');

    /* ── FONDO Y BASE ── */
    [data-testid="stAppViewContainer"] {
        background-color: #0d0f0d !important;
    }
    .stApp { background-color: #0d0f0d !important; }
    .block-container { padding-top: 2rem !important; }

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"] {
        background-color: #0a0c0a !important;
        border-right: 1px solid #1a2a1a !important;
    }
    [data-testid="stSidebar"] * {
        font-family: 'Inter', sans-serif !important;
        color: #B0B0B0 !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        color: #C0C0C0 !important;
    }
    [data-testid="stSidebar"] button {
        background: transparent !important;
        border: 1px solid rgba(122,196,122,0.3) !important;
        color: #7AC47A !important;
        border-radius: 4px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        letter-spacing: 1px !important;
    }
    [data-testid="stSidebar"] button:hover {
        background: rgba(122,196,122,0.1) !important;
    }

    /* ── TIPOGRAFÍA GENERAL ── */
    h1, h2, h3, h4 {
        font-family: 'JetBrains Mono', monospace !important;
        color: #E8F5E8 !important;
        font-weight: 600 !important;
    }
    p, span, label, div {
        font-family: 'Inter', sans-serif !important;
        color: #C0C0C0 !important;
    }

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 1px solid #1a2a1a !important;
        gap: 8px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #666 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        border: none !important;
        padding: 8px 16px !important;
    }
    .stTabs [aria-selected="true"] {
        background: transparent !important;
        color: #7AC47A !important;
        border-bottom: 2px solid #7AC47A !important;
    }

    /* ── INPUTS ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #111811 !important;
        border: 1px solid #1a2a1a !important;
        border-radius: 4px !important;
        color: #E0E0E0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #7AC47A !important;
        box-shadow: 0 0 0 1px rgba(122,196,122,0.2) !important;
    }
    .stTextInput label, .stTextArea label {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px !important;
        color: #888 !important;
    }

    /* ── SELECTBOX ── */
    .stSelectbox > div > div {
        background-color: #111811 !important;
        border: 1px solid #1a2a1a !important;
        border-radius: 4px !important;
        color: #E0E0E0 !important;
    }
    .stSelectbox label {
        color: #888 !important;
        font-size: 12px !important;
    }

    /* ── BOTONES ── */
    div[data-testid="stButton"] button {
        background-color: transparent !important;
        color: #7AC47A !important;
        border: 1px solid #7AC47A !important;
        border-radius: 4px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        letter-spacing: 1px !important;
        transition: all 0.2s !important;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #7AC47A !important;
        color: #0a0a0a !important;
    }

    /* ── MÉTRICAS ── */
    [data-testid="stMetric"] {
        background: #111811 !important;
        border: 1px solid #1a2a1a !important;
        border-radius: 6px !important;
        padding: 16px !important;
    }
    [data-testid="stMetricLabel"] {
        color: #888 !important;
        font-size: 11px !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stMetricValue"] {
        color: #7AC47A !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 28px !important;
    }

    /* ── DATAFRAME ── */
    [data-testid="stDataFrame"] {
        border: 1px solid #1a2a1a !important;
        border-radius: 6px !important;
    }

    /* ── ALERTS ── */
    .stSuccess {
        background: rgba(122,196,122,0.08) !important;
        border: 1px solid rgba(122,196,122,0.3) !important;
        color: #7AC47A !important;
        border-radius: 4px !important;
    }
    .stError {
        background: rgba(255,80,80,0.08) !important;
        border: 1px solid rgba(255,80,80,0.3) !important;
        border-radius: 4px !important;
    }
    .stWarning {
        background: rgba(255,179,71,0.08) !important;
        border: 1px solid rgba(255,179,71,0.3) !important;
        border-radius: 4px !important;
    }

    /* ── EXPANDER ── */
    .streamlit-expanderHeader {
        background: #111811 !important;
        border: 1px solid #1a2a1a !important;
        border-radius: 4px !important;
        color: #C0C0C0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 12px !important;
    }

    /* ── DIVIDER ── */
    hr {
        border-color: #1a2a1a !important;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    
    

    settings = load_settings(BASE_DIR)

    if "pantalla" not in st.session_state:
        st.session_state.pantalla = "login"

    token = st.query_params.get("token", None)
    if token and "usuario" not in st.session_state:
        st.session_state.pantalla = "nueva_password"
        st.session_state.reset_token = token

    verify_token = st.query_params.get("verify", None)
    if verify_token:
        import psycopg2
        try:
            conn = psycopg2.connect(settings.sqlserver_conn_str)
            cur = conn.cursor()
            cur.execute(
                "SELECT correo FROM password_reset_tokens WHERE token=%s AND usado=FALSE AND expira_en > NOW()",
                (verify_token,)
            )
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE usuarios SET activo=TRUE WHERE correo=%s", (row[0],))
                cur.execute("UPDATE password_reset_tokens SET usado=TRUE WHERE token=%s", (verify_token,))
                conn.commit()
                st.success("✅ Cuenta verificada. Ya puedes iniciar sesión.")
            else:
                st.error("El enlace es inválido o ha expirado.")
            conn.close()
        except Exception as e:
            st.error(f"Error: {e}")

    if st.session_state.pantalla == "login" and "usuario" not in st.session_state:
        render_login(settings)
        st.stop()
    elif st.session_state.pantalla == "registro":
        render_registro(settings)
        st.stop()
    elif st.session_state.pantalla == "olvide_password":
        render_olvide_password(settings)
        st.stop()
    elif st.session_state.pantalla == "nueva_password":
        render_nueva_password(st.session_state.get("reset_token", ""), settings)
        st.stop()

    try:
        repo = build_repo(settings)
    except Exception as e:
        st.error(f"No se pudo construir el repositorio: {e}")
        st.stop()

    apply_global_css()    

    st.sidebar.title(APP_TITLE)
    st.sidebar.caption(f"Módulo: {MODULE_TITLE}")
    st.sidebar.caption(f"Backend: {settings.backend}")

    rol = st.sidebar.radio("Rol", [" Agente", " Supervisor"], index=0)
    st.sidebar.divider()
    st.sidebar.write(f" {st.session_state.usuario['correo']}")
    if st.sidebar.button(" Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

    with st.sidebar.expander("ℹ Diagnóstico", expanded=False):
        st.write("Backend:", settings.backend)
        st.write("PROJECT_ROOT:", PROJECT_ROOT)
        st.write("SCRIPTS_DIR:", SCRIPTS_DIR)

    if "df" not in st.session_state:
        try:
            df0 = repo.cargar()
            df0 = asegurar_columnas(df0)
            st.session_state.df = df0
        except Exception as e:
            st.error(f"No se pudo cargar el catálogo: {e}")
            st.stop()

    df = asegurar_columnas(st.session_state.df)

    if rol == " Agente":
        render_agente(df, repo)
    else:
        render_supervisor(df, repo, settings)


if __name__ == "__main__":
    main()