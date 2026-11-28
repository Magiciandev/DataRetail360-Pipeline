"""Pruebas de las vistas de KPIs (src/vistas.py) sobre un DW mínimo en memoria."""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from src import schema, vistas

MESES = ["2025-03", "2025-04", "2025-05", "2025-06", "2025-07"]
VENTAS_MM = [100, 100, 100, 96, 50]          # millones de CLP netos por mes (una transacción por mes)


@pytest.fixture()
def dw():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    schema.crear_esquema(engine)
    dias = [date(2025, 3, 1) + timedelta(days=i) for i in range(153)]               # 1-mar a 31-jul
    fechas = []
    for d in dias:
        iso = d.isocalendar()
        fechas.append({"fecha_key": int(d.strftime("%Y%m%d")), "fecha": d, "dia": d.day, "mes": d.month,
                       "nombre_mes": "x", "trimestre": (d.month - 1) // 3 + 1, "anio": d.year,
                       "dia_semana": vistas.DIAS_SEMANA[d.weekday()], "es_fin_de_semana": int(d.weekday() >= 5),
                       "anio_mes": d.strftime("%Y-%m"), "anio_semana": f"{iso[0]}-W{iso[1]:02d}"})
    clave = lambda d: int(d.strftime("%Y%m%d"))                                      # noqa: E731
    with engine.begin() as conn:
        conn.execute(schema.dim_fecha.insert(), fechas)
        conn.execute(schema.dim_producto.insert(), [
            {"producto_key": 1, "sku": "T-1", "categoria": "Tecnología", "valido_desde": date(1900, 1, 1),
             "valido_hasta": date(9999, 12, 31), "es_actual": 1},
            {"producto_key": 2, "sku": "H-1", "categoria": "Hogar", "valido_desde": date(1900, 1, 1),
             "valido_hasta": date(9999, 12, 31), "es_actual": 1}])
        # Ventas: una transacción por mes (día 10) + una DEVOLUCIÓN gigante que no debe contar
        filas = [{"id_transaccion": f"T{i}", "linea": 1, "fecha_key": clave(date(2025, 3 + i, 10)), "producto_key": 1,
                  "cliente_key": 1, "sucursal_key": 1, "canal_key": 1, "monto_neto": mm * 1e6, "devolucion": 0}
                 for i, mm in enumerate(VENTAS_MM)]
        filas.append({"id_transaccion": "DEV", "linea": 1, "fecha_key": clave(date(2025, 3, 11)), "producto_key": 1,
                      "cliente_key": 1, "sucursal_key": 1, "canal_key": 1, "monto_neto": 999e6, "devolucion": 1})
        conn.execute(schema.fact_ventas.insert(), filas)
        # Inventario: semana del 3-mar (lun 3 a dom 9): Tecnología 1 de 10 fotos en quiebre; semana del 10-mar: 2 de 10
        inv = []
        for sem, quiebres_tec in [(date(2025, 3, 3), 1), (date(2025, 3, 10), 2)]:
            for i in range(7):
                d = sem + timedelta(days=i)
                inv.append({"fecha_key": clave(d), "producto_key": 1, "sucursal_key": 1, "stock_unidades": 0 if i < quiebres_tec else 5,
                            "unidades_merma": 0, "quiebre": int(i < quiebres_tec)})
                inv.append({"fecha_key": clave(d), "producto_key": 2, "sucursal_key": 1, "stock_unidades": 5,
                            "unidades_merma": 0, "quiebre": 0})
        conn.execute(schema.fact_inventario.insert(), inv)
        # Campañas: ROAS 3,0 (meta), 0,5 (alerta) y 1,5 (observación)
        conn.execute(schema.dim_campana.insert(), [
            {"campana_key": k, "codigo_campana": f"C{k}", "nombre_campana": f"Campaña {k}"} for k in (1, 2, 3)])
        camp = []
        for k, ingreso in [(1, 300.0), (2, 50.0), (3, 150.0)]:
            for c in range(10):
                camp.append({"campana_key": k, "cliente_key": c + 1, "producto_key": 1, "canal_key": 1, "fecha_key": 20250310,
                             "contactado": 1, "respondio": int(c < 3), "compro": int(c == 0),
                             "monto_venta_atribuida": ingreso if c == 0 else 0.0, "costo_asignado": 10.0})
        conn.execute(schema.fact_campanas.insert(), camp)
    vistas.crear_vistas(engine)
    return engine


def _leer(engine, sql):
    with engine.connect() as conn:
        return conn.execute(text(sql)).mappings().all()


def test_k1_meta_es_el_promedio_de_3_meses_previos_y_excluye_devoluciones(dw):
    f = _leer(dw, "SELECT * FROM vw_kpi_k1_k2_mensual ORDER BY anio_mes")
    assert [r["anio_mes"] for r in f] == MESES
    assert [r["venta_neta"] for r in f] == [m * 1e6 for m in VENTAS_MM]            # la devolución de 999 MM no suma
    assert [r["meta_venta"] for r in f[:3]] == [None, None, None]                    # sin 3 meses previos no hay meta
    assert f[3]["meta_venta"] == pytest.approx(100e6) and f[4]["meta_venta"] == pytest.approx((100 + 100 + 96) / 3 * 1e6)
    assert [r["estado_k1"] for r in f] == ["Sin base de comparación"] * 3 + ["En observación", "Alerta"]
    assert f[4]["ratio_meta"] == pytest.approx(50 / ((100 + 100 + 96) / 3))


def test_k2_ticket_y_su_variacion_contra_el_mes_anterior(dw):
    f = _leer(dw, "SELECT * FROM vw_kpi_k1_k2_mensual ORDER BY anio_mes")
    assert f[0]["estado_k2"] == "Sin mes anterior" and f[0]["variacion_ticket_pct"] is None
    assert f[1]["estado_k2"] == "Meta"                                              # igual que el mes anterior
    assert f[3]["variacion_ticket_pct"] == pytest.approx(-4.0) and f[3]["estado_k2"] == "En observación"   # cae 4 %: no llega a alerta
    assert f[4]["estado_k2"] == "Alerta"


def test_k4_porcentaje_y_estado_por_semana_y_categoria(dw):
    f = {(r["anio_semana"], r["categoria"]): r for r in _leer(dw, "SELECT * FROM vw_kpi_k4_quiebre_semanal")}
    s1, s2 = "2025-W10", "2025-W11"
    assert f[(s1, "Tecnología")]["fotos"] == 7 and f[(s1, "Tecnología")]["fotos_en_quiebre"] == 1
    assert f[(s1, "Tecnología")]["pct_quiebre"] == pytest.approx(100 / 7) and f[(s1, "Tecnología")]["estado_k4"] == "Alerta"
    assert f[(s2, "Tecnología")]["pct_quiebre"] == pytest.approx(200 / 7)
    assert f[(s1, "Hogar")]["pct_quiebre"] == 0 and f[(s1, "Hogar")]["estado_k4"] == "Meta"
    assert str(f[(s1, "Tecnología")]["semana_desde"]) == "2025-03-03"               # lunes de la semana


def test_k5_roas_y_estado_por_campana(dw):
    f = {r["codigo_campana"]: r for r in _leer(dw, "SELECT * FROM vw_kpi_k5_campanas")}
    assert f["C1"]["roas"] == pytest.approx(3.0) and f["C1"]["estado_k5"] == "Meta"
    assert f["C2"]["roas"] == pytest.approx(0.5) and f["C2"]["estado_k5"] == "Alerta"
    assert f["C3"]["roas"] == pytest.approx(1.5) and f["C3"]["estado_k5"] == "En observación"
    assert f["C1"]["contactados"] == 10 and f["C1"]["respuesta_pct"] == pytest.approx(30) and f["C1"]["conversion_pct"] == pytest.approx(10)


def test_vw_dim_fecha_agrega_indice_de_mes_y_numero_de_dia(dw):
    f = {str(r["fecha"]): r for r in _leer(dw, "SELECT * FROM vw_dim_fecha")}
    assert f["2025-03-03"]["mes_indice"] == 2025 * 12 + 3 and f["2025-03-03"]["dia_semana_num"] == 1   # lunes
    assert f["2025-03-09"]["dia_semana_num"] == 7                                                      # domingo
    assert f["2025-04-01"]["mes_indice"] == f["2025-03-31"]["mes_indice"] + 1


def test_crear_vistas_es_idempotente(dw):
    assert vistas.crear_vistas(dw) == list(vistas.construir_vistas("sqlite"))
    assert vistas.crear_vistas(dw)


def test_el_script_de_sql_server_usa_prefijo_unicode_y_sintaxis_valida():
    sql = vistas.exportar_sql_server()
    assert "N'Alerta'" in sql and "N'En observación'" in sql and sql.count("CREATE VIEW") == 4 and sql.count("GO") == 8
    sqlglot = pytest.importorskip("sqlglot")
    for nombre, cuerpo in vistas.construir_vistas("mssql").items():
        sqlglot.parse_one(cuerpo, read="tsql")           # lanza ParseError si el T-SQL no es válido
