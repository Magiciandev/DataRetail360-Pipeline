"""App Streamlit de DataRetail 360: los mismos KPIs y gráficos del notebook, con filtros.

Desde la raíz del repo (con el DW ya cargado por `python run_pipeline.py`):
    pip install -r requirements-storytelling.txt
    streamlit run storytelling/app.py
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from storytelling import kpis as K  # noqa: E402

st.set_page_config(page_title="DataRetail 360 · KPIs", layout="wide")


@st.cache_data(show_spinner="Leyendo el Data Warehouse…")
def cargar():
    engine = K.get_engine()
    return K.cargar_k1_k2(engine), K.cargar_k4(engine), K.cargar_k5(engine)


def mostrar(contenedor, fig):
    """Gráfico a todo el ancho y con NUESTRA paleta (theme=None evita que Streamlit recolore las series)."""
    try:
        contenedor.plotly_chart(fig, width="stretch", theme=None)
    except TypeError:                      # Streamlit antiguo (< 1.46) no tiene `width`
        contenedor.plotly_chart(fig, use_container_width=True, theme=None)


k1, k4, k5 = cargar()

st.title("DataRetail 360 · KPIs de ventas, inventario y campañas")
st.caption("Datos sintéticos de ejemplo (marzo–agosto de 2025) leídos desde el Data Warehouse. "
           "Umbrales de la ficha de KPI 3.1.3.")

# ---------------------------------------------------------------------------- Filtros
st.sidebar.header("Filtros")
meses = k1["mes"].tolist()
desde, hasta = st.sidebar.select_slider("Meses (K1 y K2)", options=meses, value=(meses[0], meses[-1]),
                                        format_func=K.mes_corto)
categorias = sorted(k4["categoria"].unique())
destacada = st.sidebar.selectbox("Categoría a destacar (K4)", categorias,
                                 index=categorias.index("Tecnología") if "Tecnología" in categorias else 0)
campanas = st.sidebar.multiselect("Campañas (K5)", k5["campana"].tolist(), default=k5["campana"].tolist())

k1_f = k1[(k1["mes"] >= desde) & (k1["mes"] <= hasta)]
k5_f = k5[k5["campana"].isin(campanas)]

# ---------------------------------------------------------------------------- Tarjetas (con texto, no solo color)
ult = k1_f.iloc[-1]
sem = K.k4_serie(k4).iloc[-1]
peor = k5_f.loc[k5_f["roas"].idxmin()] if len(k5_f) else None
c1, c2, c3, c4 = st.columns(4)
if ult["ratio"] == ult["ratio"]:        # no es NaN: hay meta con qué comparar
    delta_k1 = f"{'+' if ult['ratio'] >= 1 else '-'}{K.n(abs(ult['ratio'] - 1) * 100)} % vs meta · {ult['estado']}"
else:
    delta_k1 = "Sin base de comparación"
c1.metric(f"K1 · Venta neta de {K.mes_largo(ult['mes'])}", f"{K.n(ult['venta_mm'])} MM", delta_k1, delta_color="off")
if ult["ticket_var"] == ult["ticket_var"]:
    delta_k2 = f"{'+' if ult['ticket_var'] >= 0 else '-'}{K.n(abs(ult['ticket_var']), 1)} % vs mes anterior"
else:
    delta_k2 = "Sin mes anterior"
c2.metric("K2 · Ticket promedio", f"${K.n(ult['ticket'])}", delta_k2, delta_color="off")
c3.metric(f"K4 · Quiebre, semana del {K.dia_mes(sem['desde'])}", f"{K.n(sem['pct'], 1)} %",
          f"Meta ≤ {K.n(K.K4_META)} % · Alerta > {K.n(K.K4_ALERTA)} %", delta_color="off")
if peor is not None:
    c4.metric("K5 · Peor ROAS", f"{K.n(peor['roas'], 2)}x", f"{peor['campana']} · {peor['estado']}", delta_color="off")

# ---------------------------------------------------------------------------- Gráficos
mostrar(st, K.fig_k1(k1_f))
izq, der = st.columns(2)
mostrar(izq, K.fig_k4(k4, destacada))
if len(k5_f):
    mostrar(der, K.fig_k5(k5_f))
else:
    der.info("Elige al menos una campaña para ver K5.")

# ---------------------------------------------------------------------------- Narrativa
with st.expander("La historia en una mirada (Situación · Complicación · Idea)", expanded=True):
    sci = K.narrativa_sci(k1, k4, k5)
    st.markdown(f"**Situación.** {sci['situacion']}")
    st.markdown(f"**Complicación.** {sci['complicacion']}")
    st.markdown(f"**Idea.** {sci['idea']}")
