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
    # CSS personalizado
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;600;700&family=Inter:wght@300;400;500&display=swap');

    [data-testid="stAppViewContainer"] {
        background-color: #0a0a0a;
        background-image: 
            linear-gradient(rgba(74, 222, 128, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(74, 222, 128, 0.03) 1px, transparent 1px);
        background-size: 40px 40px;
    }

    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { display: none; }

    .login-container {
        max-width: 420px;
        margin: 60px auto 0 auto;
        padding: 48px 40px;
        background: #111111;
        border: 1px solid #1f1f1f;
        border-top: 2px solid #4ade80;
        box-shadow: 0 0 60px rgba(74, 222, 128, 0.05);
    }

    .login-logo {
        text-align: center;
        margin-bottom: 32px;
    }

    .login-logo img {
    height: 48px;
}
```

    .login-title {
        font-family: 'Rajdhani', sans-serif;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #4ade80;
        text-align: center;
        margin-bottom: 8px;
    }

    .login-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        color: #444;
        text-align: center;
        margin-bottom: 36px;
        letter-spacing: 0.5px;
    }

    .stTextInput > div > div > input {
        background-color: #0a0a0a !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 0 !important;
        color: #e0e0e0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        padding: 12px 16px !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #4ade80 !important;
        box-shadow: 0 0 0 1px #4ade80 !important;
    }

    .stTextInput label {
        font-family: 'Inter', sans-serif !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        color: #555 !important;
    }

    .stButton > button {
        background-color: #4ade80 !important;
        color: #0a0a0a !important;
        border: none !important;
        border-radius: 0 !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        padding: 12px 24px !important;
        width: 100% !important;
        transition: all 0.2s !important;
    }

    .stButton > button:hover {
        background-color: #86efac !important;
        transform: translateY(-1px) !important;
    }

    .divider {
        border: none;
        border-top: 1px solid #1f1f1f;
        margin: 28px 0;
    }

    .login-links {
        display: flex;
        justify-content: space-between;
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        letter-spacing: 0.5px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Logo y encabezado
    logo_path = os.path.join(BASE_DIR, "logo.jpeg")
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-logo">', unsafe_allow_html=True)
    if os.path.exists(logo_path):
        st.image(logo_path, width=160)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-title">IT Knowledge Core</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Acceso restringido · Solo personal autorizado</div>', unsafe_allow_html=True)

    correo = st.text_input("Correo corporativo", key="login_correo", placeholder="usuario@techcrg.com")
    password = st.text_input("Contraseña", type="password", key="login_password", placeholder="••••••••")

    if st.button("INGRESAR"):
        if not correo.endswith("@techcrg.com"):
            st.error("Solo se permiten correos @techcrg.com")
            return
        usuario = verificar_login(correo, password, settings.sqlserver_conn_str)
        if usuario:
            st.session_state.usuario = usuario
            st.session_state.pantalla = "app"
            st.rerun()
        else:
            st.error("Correo o contraseña incorrectos.")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    if col1.button("Crear cuenta"):
        st.session_state.pantalla = "registro"
        st.rerun()
    if col2.button("Olvidé mi contraseña"):
        st.session_state.pantalla = "olvide_password"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

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
    st.subheader("📋 Catálogo completo")
    st.dataframe(df.drop(columns=["programa_norm"], errors="ignore"), use_container_width=True)


# -------------------------
# PANTALLA SUPERVISOR
# -------------------------

def render_supervisor(df: pd.DataFrame, repo, settings):
    show_info_header(
        "🛠 Supervisor | Panel de Gobierno",
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
        st.markdown("### 🧾 Bandeja de revisión")
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
            st.markdown("#### 📌 Detalle")
            st.json({
                "programa": safe_str(fila.get("programa")),
                "estado": safe_str(fila.get("estado")),
                "version": safe_str(fila.get("version")),
                "compatibilidad": safe_str(fila.get("compatibilidad")),
                "licencia": safe_str(fila.get("licencia")),
                "periodo": safe_str(fila.get("periodo")),
                "descripcion": safe_str(fila.get("descripcion")),
                "fecha_revision": safe_str(fila.get("fecha_revision")),
            })

            motivo = st.text_input("Motivo rechazo (solo si rechaza)", key="motivo_rechazo")

            col1, col2 = st.columns(2)
            if col1.button(" Aprobar", key="btn_aprobar", use_container_width=True):
                df2 = actualizar_decision(df_all, programa_norm_sel, True)
                df2 = guardar_y_recargar(repo, df2)
                st.session_state.df = asegurar_columnas(df2)
                show_success(" Solicitud aprobada y guardada.")
                st.rerun()

            if col2.button("⛔ Rechazar", key="btn_rechazar", use_container_width=True):
                df2 = actualizar_decision(df_all, programa_norm_sel, False, motivo)
                df2 = guardar_y_recargar(repo, df2)
                st.session_state.df = asegurar_columnas(df2)
                show_success("⛔ Solicitud rechazada y guardada.")
                st.rerun()

            with st.expander("Ver todas las solicitudes en revisión"):
                st.dataframe(en_rev.drop(columns=["programa_norm"], errors="ignore"), use_container_width=True)

    with sup_tab2:
        st.markdown("### Administración del catálogo")
        st.caption(f"Backend activo: {settings.backend}")

        gestion_tab1, gestion_tab2, gestion_tab3 = st.tabs(["➕ Agregar", "✏️ Editar", "🗑️ Eliminar"])

        with gestion_tab1:
            st.markdown("#### ➕ Agregar aplicación")
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
                            show_success("✅ Agregado y guardado.")
                            st.rerun()

        with gestion_tab2:
            st.markdown("#### ✏️ Editar aplicación")
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
                            show_success("✅ Actualizado y guardado.")
                            st.rerun()

        with gestion_tab3:
            st.markdown("#### 🗑️ Eliminar aplicación")
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
                            show_success("✅ Eliminado y guardado.")
                            st.rerun()
                        else:
                            st.error("Confirmación inválida.")

# -------------------------
# App principal
# -------------------------

def main():
    st.set_page_config(page_title=f"{APP_TITLE} | {MODULE_TITLE}", layout="wide")
    

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