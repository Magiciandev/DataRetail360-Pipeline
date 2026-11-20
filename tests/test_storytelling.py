"""Pruebas de storytelling/kpis.py (KPIs, hechos de la narrativa y gráficos). Requieren plotly."""
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

pytest.importorskip("plotly")
from storytelling import kpis as K  # noqa: E402


def test_formato_chileno_de_numeros():
    assert K.n(1234.5, 1) == "1.234,5"
    assert K.n(0.8, 2) == "0,80"
    assert K.n(185.3) == "185"


def _engine_ventas():
    """DW mínimo en memoria: 5 meses de venta (la del mes 5 a la mitad) y una devolución que NO debe contar."""
    engine = create_engine("sqlite://", poolclass=StaticPool)
    meses = ["2025-03", "2025-04", "2025-05", "2025-06", "2025-07"]
    ventas = [{"fecha_key": 20250300 + i, "monto_neto": 100e6 if m != "2025-07" else 50e6, "id_transaccion": f"T{i}", "devolucion": 0}
              for i, m in enumerate(meses, start=1)]
    ventas.append({"fecha_key": 20250301, "monto_neto": 999e6, "id_transaccion": "DEV", "devolucion": 1})
    pd.DataFrame(ventas).to_sql("fact_ventas", engine, index=False)
    pd.DataFrame({"fecha_key": [20250300 + i for i in range(1, 6)], "anio_mes": meses}).to_sql("dim_fecha", engine, index=False)
    return engine


def test_k1_excluye_devoluciones_y_calcula_meta_y_estado():
    k1 = K.cargar_k1_k2(_engine_ventas())
    assert k1["venta_mm"].tolist() == [100, 100, 100, 100, 50]               # la devolución de 999 MM no suma
    assert k1["estado"].tolist()[:3] == ["Sin base de comparación"] * 3
    assert k1.loc[3, "estado"] == "Meta" and k1.loc[3, "meta_mm"] == 100      # promedio de los 3 meses previos
    assert k1.loc[4, "estado"] == "Alerta" and k1.loc[4, "ratio"] == pytest.approx(0.5)


def _datos_con_historia():
    k1 = K.cargar_k1_k2(_engine_ventas())
    semanas = pd.date_range("2025-08-04", periods=3, freq="7D")
    k4 = pd.DataFrame([
        {"semana": f"2025-W3{i}", "categoria": c, "desde": d, "quiebres": q, "fotos": 100}
        for i, d in enumerate(semanas, start=1)
        for c, q in [("Tecnología", [2, 30, 70][i - 1]), ("Hogar", 1)]])
    k5 = pd.DataFrame({
        "codigo": ["A", "B", "C"], "campana": ["Hogar Fest", "Gamer", "Semana Tech"],
        "contactados": [100, 100, 100], "respondieron": [30, 20, 35], "compraron": [13, 9, 3],
        "ingreso": [350.0, 180.0, 80.0], "inversion": [100.0, 100.0, 100.0]})
    k5["respuesta_pct"] = 100 * k5["respondieron"] / k5["contactados"]
    k5["conversion_pct"] = 100 * k5["compraron"] / k5["contactados"]
    k5["roas"] = k5["ingreso"] / k5["inversion"]
    k5["estado"] = ["Meta", "En observación", "Alerta"]
    return k1, k4, k5


def test_k4_serie_es_porcentaje_de_fotos_con_quiebre():
    _, k4, _ = _datos_con_historia()
    tec = K.k4_serie(k4, ["Tecnología"])
    assert tec["pct"].tolist() == [2, 30, 70]
    assert K.k4_serie(k4)["pct"].tolist() == [1.5, 15.5, 35.5]               # (Tecnología + Hogar) / 200 fotos


def test_la_historia_se_verifica_y_la_narrativa_usa_cifras_de_los_datos():
    k1, k4, k5 = _datos_con_historia()
    assert len(K.verificar_historia(k1, k4, k5)) == 4
    sci = K.narrativa_sci(k1, k4, k5)
    assert "50 millones" in sci["complicacion"] and "70 %" in sci["complicacion"] and "Semana Tech" in sci["complicacion"]
    assert "Hogar Fest" in sci["idea"]


def test_si_los_datos_no_sostienen_la_historia_la_verificacion_falla():
    k1, k4, k5 = _datos_con_historia()
    k5.loc[k5["campana"] == "Semana Tech", "respuesta_pct"] = 1.0           # ya no es la que más respondió
    with pytest.raises(AssertionError, match="más respondió"):
        K.verificar_historia(k1, k4, k5)


def test_los_titulos_son_el_mensaje_con_cifras_reales():
    k1, k4, k5 = _datos_con_historia()
    assert "50 % bajo el promedio" in K.fig_k1(k1).layout.title.text
    assert "70 %" in K.fig_k4(k4).layout.title.text
    assert "Semana Tech" in K.fig_k5(k5).layout.title.text and "0,80x" in K.fig_k5(k5).layout.title.text
