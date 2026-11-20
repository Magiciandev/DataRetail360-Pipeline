"""KPIs de la ficha 3.1.3 leídos desde el Data Warehouse, gráficos Plotly y narrativa SCI.

Lo usan el notebook `3_2_2_storytelling_plotly.ipynb` y la app `app.py`, así la historia es la misma en los dos.
Todo sale de la capa Gold (el DW): ningún número del título o de la narrativa está escrito a mano.

Convenciones (guías 3.1.2 y 3.1.4):
  * el título de cada gráfico es el MENSAJE, no el nombre del dato;
  * paleta segura para daltonismo y NUNCA solo color: además hay etiquetas, símbolos (▼) y tipos de línea;
  * cada número va junto a su meta/alerta (contexto).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src import db  # noqa: E402
from src.config import get_settings  # noqa: E402

# ------------------------------------------------------------------------------ Diseño
NAVY, TEAL, AZUL, NARANJA, DORADO, GRIS = "#0F2C4C", "#0E8C84", "#1F77B4", "#FF7F0E", "#C8860D", "#9AA7B2"
TEXTO = "#33414D"

# Umbrales de la ficha de KPI (provisionales: se calibraron con los datos generados)
K1_ALERTA = 0.90          # alerta si la venta del mes es < 90 % del promedio de los 3 meses previos
K4_META, K4_ALERTA = 5.0, 10.0      # % de quiebre: meta ≤ 5, alerta > 10
K5_META, K5_ALERTA = 3.0, 1.0       # ROAS: meta ≥ 3x, alerta < 1x

MESES_LARGOS = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio",
                8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
MESES_CORTOS = {m: n[:3] for m, n in MESES_LARGOS.items()}


def n(valor: float, decimales: int = 0) -> str:
    """Número con formato chileno: miles con punto y decimales con coma (1.234,5)."""
    return f"{valor:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def mes_largo(anio_mes: str) -> str:
    return MESES_LARGOS[int(anio_mes[5:7])]


def mes_corto(anio_mes: str) -> str:
    return f"{MESES_CORTOS[int(anio_mes[5:7])].capitalize()} {anio_mes[:4]}"


def dia_mes(fecha: pd.Timestamp) -> str:
    return f"{fecha.day} {MESES_CORTOS[fecha.month]}"


def _layout(fig: go.Figure, titulo: str, alto: int = 470) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=alto, separators=",.",
        title=dict(text=titulo, x=0, xanchor="left", font=dict(size=19, color=NAVY)),
        font=dict(family="Calibri, 'Segoe UI', Arial, sans-serif", size=13, color=TEXTO),
        margin=dict(l=60, r=30, t=95, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, font=dict(size=12)),
        hoverlabel=dict(font_size=13),
    )
    return fig


# ------------------------------------------------------------------------------ Datos (capa Gold)
def get_engine():
    return db.get_engine(get_settings())


def _leer(engine, sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)


def cargar_k1_k2(engine) -> pd.DataFrame:
    """K1 (venta neta mensual) y K2 (ticket promedio) con la meta y el estado de la ficha."""
    df = _leer(engine, """
        SELECT d.anio_mes AS mes, SUM(f.monto_neto) AS venta_neta, COUNT(DISTINCT f.id_transaccion) AS transacciones
        FROM fact_ventas f JOIN dim_fecha d ON d.fecha_key = f.fecha_key
        WHERE f.devolucion = 0
        GROUP BY d.anio_mes ORDER BY d.anio_mes""")
    df["venta_mm"] = df["venta_neta"] / 1e6
    df["ticket"] = df["venta_neta"] / df["transacciones"]
    df["ticket_var"] = df["ticket"].pct_change() * 100                       # % vs el mes anterior
    df["meta_mm"] = df["venta_mm"].shift(1).rolling(3).mean()                # promedio de los 3 meses previos
    df["ratio"] = df["venta_mm"] / df["meta_mm"]
    df["estado"] = pd.Series("Sin base de comparación", index=df.index)
    con_meta = df["ratio"].notna()
    df.loc[con_meta & (df["ratio"] >= 1), "estado"] = "Meta"
    df.loc[con_meta & (df["ratio"] < 1), "estado"] = "En observación"
    df.loc[con_meta & (df["ratio"] < K1_ALERTA), "estado"] = "Alerta"
    return df


def cargar_k4(engine) -> pd.DataFrame:
    """K4 (quiebre de stock) por semana y categoría: fotos producto × sucursal × día y cuántas con stock 0."""
    df = _leer(engine, """
        SELECT d.anio_semana AS semana, p.categoria AS categoria, MIN(d.fecha) AS desde,
               SUM(f.quiebre) AS quiebres, COUNT(*) AS fotos
        FROM fact_inventario f
        JOIN dim_fecha d    ON d.fecha_key = f.fecha_key
        JOIN dim_producto p ON p.producto_key = f.producto_key
        GROUP BY d.anio_semana, p.categoria
        ORDER BY d.anio_semana""")
    df["desde"] = pd.to_datetime(df["desde"])
    return df


def k4_serie(k4: pd.DataFrame, categorias: list[str] | None = None) -> pd.DataFrame:
    """% de quiebre por semana (todas las categorías o solo las indicadas)."""
    base = k4 if not categorias else k4[k4["categoria"].isin(categorias)]
    s = base.groupby("semana", as_index=False).agg(desde=("desde", "min"), quiebres=("quiebres", "sum"), fotos=("fotos", "sum"))
    s["pct"] = 100 * s["quiebres"] / s["fotos"]
    return s


def cargar_k5(engine) -> pd.DataFrame:
    """K5 (ROAS) por campaña, con respuesta y conversión."""
    df = _leer(engine, """
        SELECT c.codigo_campana AS codigo, c.nombre_campana AS campana,
               SUM(f.contactado) AS contactados, SUM(f.respondio) AS respondieron, SUM(f.compro) AS compraron,
               SUM(f.monto_venta_atribuida) AS ingreso, SUM(f.costo_asignado) AS inversion
        FROM fact_campanas f JOIN dim_campana c ON c.campana_key = f.campana_key
        GROUP BY c.codigo_campana, c.nombre_campana
        ORDER BY c.codigo_campana""")
    df["respuesta_pct"] = 100 * df["respondieron"] / df["contactados"]
    df["conversion_pct"] = 100 * df["compraron"] / df["contactados"]
    df["roas"] = df["ingreso"] / df["inversion"]
    df["estado"] = "En observación"
    df.loc[df["roas"] >= K5_META, "estado"] = "Meta"
    df.loc[df["roas"] < K5_ALERTA, "estado"] = "Alerta"
    return df


# ------------------------------------------------------------------------------ Hechos de la historia
def hechos(k1: pd.DataFrame, k4: pd.DataFrame, k5: pd.DataFrame) -> dict:
    """Las cifras que usan los títulos y la narrativa, calculadas desde los datos."""
    alertas = k1[k1["estado"] == "Alerta"]
    mes_alerta = alertas.iloc[-1] if len(alertas) else None
    h = {"mes_alerta": mes_alerta}
    if mes_alerta is not None:
        previos = k1[k1["mes"] < mes_alerta["mes"]]
        h["previos"] = previos
        h["mes_anterior"] = previos.iloc[-1]["mes"]
        h["en_meta"] = previos.loc[previos["estado"] == "Meta", "mes"].tolist()
    tec = k4_serie(k4, ["Tecnología"])
    pico = tec.loc[tec["pct"].idxmax()]
    h["tec_pico"], h["tec_pico_desde"] = float(pico["pct"]), pico["desde"]
    total = k4_serie(k4)
    h["quiebre_normal_max"] = float(total.loc[total["pct"] <= K4_ALERTA, "pct"].max())
    h["mas_respondio"] = k5.loc[k5["respuesta_pct"].idxmax()]
    h["peor_roas"] = k5.loc[k5["roas"].idxmin()]
    h["mejor_roas"] = k5.loc[k5["roas"].idxmax()]
    return h


def verificar_historia(k1, k4, k5) -> list[str]:
    """Comprueba que lo que afirma la narrativa SÍ está en los datos. Falla con un mensaje claro si no."""
    h = hechos(k1, k4, k5)
    assert h["mes_alerta"] is not None, "ningún mes quedó en alerta: la complicación de la narrativa no existe en estos datos"
    assert h["tec_pico"] > K4_ALERTA, "el quiebre de Tecnología no supera el umbral de alerta"
    assert h["mas_respondio"]["codigo"] == h["peor_roas"]["codigo"], "la campaña que más respondió no es la de peor ROAS"
    assert h["peor_roas"]["roas"] < K5_ALERTA, "la campaña de peor ROAS no está bajo el umbral de alerta"
    assert h["mejor_roas"]["roas"] >= K5_META, "ninguna campaña alcanza la meta de ROAS"
    return [
        f"K1 · {mes_largo(h['mes_alerta']['mes'])} en alerta ({n(h['mes_alerta']['ratio'], 2)} de la meta)",
        f"K4 · quiebre de Tecnología con pico de {n(h['tec_pico'], 1)} % (alerta > {n(K4_ALERTA)} %)",
        f"K5 · {h['peor_roas']['campana']} respondió más y retornó menos (ROAS {n(h['peor_roas']['roas'], 2)}x)",
        f"K5 · {h['mejor_roas']['campana']} supera la meta (ROAS {n(h['mejor_roas']['roas'], 2)}x)",
    ]


# ------------------------------------------------------------------------------ Gráfico 1 · K1
def fig_k1(k1: pd.DataFrame) -> go.Figure:
    x = [mes_corto(m) for m in k1["mes"]]
    en_alerta = k1["estado"] == "Alerta"
    etiquetas = [f"{n(v, 0)}{' ▼' if a else ''}" for v, a in zip(k1["venta_mm"], en_alerta)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=k1["venta_mm"], name="Venta neta", mode="lines+markers+text",
                             line=dict(color=NAVY, width=3), marker=dict(size=9, color=NAVY),
                             text=etiquetas, textposition="top center", textfont=dict(size=12, color=NAVY),
                             hovertemplate="%{x}<br>Venta neta: %{y:,.1f} MM<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=k1["meta_mm"], name="Meta: promedio de los 3 meses previos", mode="lines",
                             line=dict(color=TEAL, width=2, dash="dash"),
                             hovertemplate="Meta: %{y:,.1f} MM<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=k1["meta_mm"] * K1_ALERTA, name=f"Alerta: < {n(K1_ALERTA * 100)} % de la meta", mode="lines",
                             line=dict(color=NARANJA, width=2, dash="dot"),
                             hovertemplate="Umbral de alerta: %{y:,.1f} MM<extra></extra>"))
    if en_alerta.any():
        fig.add_trace(go.Scatter(x=[xi for xi, a in zip(x, en_alerta) if a], y=k1.loc[en_alerta, "venta_mm"],
                                 name="Mes en alerta", mode="markers",
                                 marker=dict(symbol="x", size=15, color=NARANJA, line=dict(width=3, color=NARANJA)),
                                 hoverinfo="skip"))

    alertas = k1[en_alerta]
    if len(alertas):
        a = alertas.iloc[-1]
        titulo = f"En {mes_largo(a['mes'])} la venta neta quedó {n((1 - a['ratio']) * 100)} % bajo el promedio de los 3 meses previos"
    else:
        titulo = "La venta neta se mantiene sobre el umbral de alerta en todos los meses"
    fig = _layout(fig, titulo)
    fig.update_yaxes(title="Venta neta (millones de CLP)", rangemode="tozero", gridcolor="#E6EBF0")
    fig.update_xaxes(title="")
    return fig


# ------------------------------------------------------------------------------ Gráfico 2 · K4
def fig_k4(k4: pd.DataFrame, destacar: str = "Tecnología") -> go.Figure:
    total = k4_serie(k4)
    cat = k4_serie(k4, [destacar])
    etiquetas = [dia_mes(d) for d in total["desde"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=etiquetas, y=total["pct"], name="Todas las categorías", mode="lines+markers",
                             line=dict(color=GRIS, width=3), marker=dict(symbol="circle", size=7, color=GRIS),
                             hovertemplate="Semana del %{x}<br>Total: %{y:.1f} %<extra></extra>"))
    fig.add_trace(go.Scatter(x=[dia_mes(d) for d in cat["desde"]], y=cat["pct"], name=destacar, mode="lines+markers",
                             line=dict(color=NAVY, width=3.5), marker=dict(symbol="square", size=8, color=NAVY),
                             hovertemplate="Semana del %{x}<br>" + destacar + ": %{y:.1f} %<extra></extra>"))
    fig.add_hline(y=K4_META, line=dict(color=TEAL, width=2, dash="dash"),
                  annotation_text=f"Meta ≤ {n(K4_META)} %", annotation_position="top left",
                  annotation_font=dict(color=TEAL, size=12))
    fig.add_hline(y=K4_ALERTA, line=dict(color=NARANJA, width=2, dash="dot"),
                  annotation_text=f"Alerta > {n(K4_ALERTA)} %", annotation_position="top left",
                  annotation_font=dict(color=NARANJA, size=12))
    pico = cat.loc[cat["pct"].idxmax()]
    fig.add_annotation(x=dia_mes(pico["desde"]), y=pico["pct"], text=f"<b>{n(pico['pct'], 0)} %</b> ▲<br>semana del {dia_mes(pico['desde'])}",
                       showarrow=True, arrowhead=2, arrowcolor=NAVY, ax=-70, ay=-5, font=dict(color=NAVY, size=13),
                       bgcolor="white", bordercolor=NAVY, borderwidth=1)

    fig = _layout(fig, f"El quiebre de {destacar} llegó a {n(pico['pct'], 0)} % la semana del {dia_mes(pico['desde'])}")
    fig.update_yaxes(title="Quiebre de stock (% de producto × sucursal × día sin stock)", rangemode="tozero", gridcolor="#E6EBF0")
    fig.update_xaxes(title="Semana (lunes de inicio)", type="category", tickangle=-45,
                     tickmode="array", tickvals=etiquetas[::2], ticktext=etiquetas[::2])
    return fig


# ------------------------------------------------------------------------------ Gráfico 3 · K5
def fig_k5(k5: pd.DataFrame) -> go.Figure:
    orden = k5.sort_values("roas", ascending=False)["campana"].tolist()           # mejor arriba, peor abajo
    d = k5.set_index("campana").loc[orden]
    color_estado = {"Meta": TEAL, "En observación": DORADO, "Alerta": NARANJA}

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, column_widths=[0.52, 0.48],
                        subplot_titles=("Respuesta y conversión (% de los contactados)", "Retorno: ROAS (veces)"))
    fig.add_trace(go.Bar(y=orden, x=d["respuesta_pct"], orientation="h", name="Respondieron", marker_color=AZUL,
                         text=[f"{n(v, 1)} %" for v in d["respuesta_pct"]], textposition="outside", cliponaxis=False,
                         hovertemplate="%{y}<br>Respondieron: %{x:.1f} %<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(y=orden, x=d["conversion_pct"], orientation="h", name="Compraron", marker_color=NARANJA,
                         text=[f"{n(v, 1)} %" for v in d["conversion_pct"]], textposition="outside", cliponaxis=False,
                         hovertemplate="%{y}<br>Compraron: %{x:.1f} %<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(y=orden, x=d["roas"], orientation="h", name="ROAS", showlegend=False,
                         marker_color=[color_estado[e] for e in d["estado"]],
                         text=[f"{n(r, 2)}x · {e}" for r, e in zip(d["roas"], d["estado"])],
                         textposition="outside", cliponaxis=False,
                         hovertemplate="%{y}<br>ROAS: %{x:.2f}x<extra></extra>"), row=1, col=2)
    fig.add_vline(x=K5_ALERTA, row=1, col=2, line=dict(color=NARANJA, width=2, dash="dot"),
                  annotation_text=f"Alerta < {n(K5_ALERTA)}x", annotation_position="top", annotation_font=dict(color=NARANJA, size=12))
    fig.add_vline(x=K5_META, row=1, col=2, line=dict(color=TEAL, width=2, dash="dash"),
                  annotation_text=f"Meta ≥ {n(K5_META)}x", annotation_position="top", annotation_font=dict(color=TEAL, size=12))

    mas = k5.loc[k5["respuesta_pct"].idxmax()]
    peor = k5.loc[k5["roas"].idxmin()]
    if mas["codigo"] == peor["codigo"]:
        titulo = (f"{peor['campana']} fue la que más respondió ({n(peor['respuesta_pct'], 1)} %) "
                  f"y la de peor retorno (ROAS {n(peor['roas'], 2)}x)")
    else:
        titulo = f"{peor['campana']} fue la campaña de peor retorno (ROAS {n(peor['roas'], 2)}x)"
    fig = _layout(fig, titulo, alto=470)
    fig.update_layout(barmode="group", margin=dict(l=150, r=60, t=110, b=50), legend=dict(x=0, y=1.13))
    fig.update_xaxes(rangemode="tozero", showgrid=False, row=1, col=1, range=[0, max(d["respuesta_pct"]) * 1.35])
    fig.update_xaxes(rangemode="tozero", showgrid=False, row=1, col=2, range=[0, max(d["roas"].max(), K5_META) * 1.5])
    fig.update_yaxes(categoryorder="array", categoryarray=orden[::-1], automargin=True)
    return fig


# ------------------------------------------------------------------------------ Narrativa SCI
def narrativa_sci(k1: pd.DataFrame, k4: pd.DataFrame, k5: pd.DataFrame) -> dict:
    """Situación – Complicación – Idea, con las cifras tomadas de los datos."""
    h = hechos(k1, k4, k5)
    a, previos = h["mes_alerta"], h["previos"]
    mas, mejor = h["mas_respondio"], h["mejor_roas"]
    en_meta = " y ".join(mes_largo(m) for m in h["en_meta"])
    return {
        "situacion": (f"Entre {mes_largo(previos.iloc[0]['mes'])} y {mes_largo(h['mes_anterior'])} la venta neta se movió entre "
                      f"{n(previos['venta_mm'].min())} y {n(previos['venta_mm'].max())} millones de CLP al mes"
                      + (f" y K1 cumplió la meta en {en_meta}." if en_meta else ".")),
        "complicacion": (f"En {mes_largo(a['mes'])} la venta neta cayó a {n(a['venta_mm'])} millones "
                         f"({n(a['ratio'], 2)} del promedio previo: alerta) y el ticket promedio bajó {n(abs(a['ticket_var']))} % "
                         f"respecto de {mes_largo(h['mes_anterior'])}. Al mismo tiempo el quiebre de stock de Tecnología subió a "
                         f"{n(h['tec_pico'])} % la semana del {dia_mes(h['tec_pico_desde'])} (meta ≤ {n(K4_META)} %), y la campaña "
                         f"{mas['campana']}, la que más respondió ({n(mas['respuesta_pct'], 1)} %), convirtió solo "
                         f"{n(mas['conversion_pct'], 1)} % y rindió {n(mas['roas'], 2)}x."),
        "idea": (f"Reponer el stock de Tecnología antes de lanzar campañas y condicionar cada campaña a que haya inventario "
                 f"disponible. Mover presupuesto desde {mas['campana']} hacia campañas que sí convierten, como {mejor['campana']} "
                 f"(ROAS {n(mejor['roas'], 2)}x). Acción medible: K4 ≤ {n(K4_META)} % antes de la próxima campaña y K5 ≥ "
                 f"{n(K5_ALERTA)}x en todas."),
    }
