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
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "Scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.append(SCRIPTS_DIR)

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

    with st.expander("🔒 Acceso Supervisor", expanded=True):
        pin = st.text_input("PIN Supervisor", type="password", key="pin_supervisor")
        if not pin:
            st.info("Ingresa el PIN para desbloquear el panel.")
            return
        if pin != settings.supervisor_pin:
            st.error("PIN incorrecto.")
            return

    show_success("Panel desbloqueado ✅")

    df_all = asegurar_columnas(st.session_state.df)
    en_rev = df_all[df_all["estado"] == ESTADO_REVISION].copy()

    st.markdown("### 📊 Resumen")
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
            if col1.button("✅ Aprobar", key="btn_aprobar", use_container_width=True):
                df2 = actualizar_decision(df_all, programa_norm_sel, True)
                df2 = guardar_y_recargar(repo, df2)
                st.session_state.df = asegurar_columnas(df2)
                show_success("✅ Solicitud aprobada y guardada.")
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
    st.title(f"{APP_TITLE} | {MODULE_TITLE}")

    settings = load_settings(BASE_DIR)

    try:
        repo = build_repo(settings)
    except Exception as e:
        st.error(f"No se pudo construir el repositorio: {e}")
        st.stop()

    st.sidebar.title(APP_TITLE)
    st.sidebar.caption(f"Módulo: {MODULE_TITLE}")
    st.sidebar.caption(f"Backend: {settings.backend}")

    rol = st.sidebar.radio("Rol", ["👤 Agente", "🛠 Supervisor"], index=0)

    with st.sidebar.expander("ℹ️ Diagnóstico", expanded=False):
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

    if rol == "👤 Agente":
        render_agente(df, repo)
    else:
        render_supervisor(df, repo, settings)


if __name__ == "__main__":
    main()
