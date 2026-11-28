"""Capa semántica de KPIs: vistas SQL sobre el Data Warehouse.

Por qué existen:
  * **Power BI en DirectQuery** consulta la base en cada visual. Los cálculos con ventanas (la meta de K1 es el promedio de los
    3 meses previos) son más seguros y fáciles de auditar en SQL que en DAX.
  * **NLQ / Text-to-SQL (IL 3.5):** una IA acierta mucho más sobre vistas con nombres claros que sobre un esquema en estrella con
    SCD2, claves sustitutas y miembros «No informado». Estas vistas son el objetivo recomendado de las consultas en lenguaje natural.
  * **Una sola verdad:** los umbrales de la ficha de KPI (3.1.3) viven en `UMBRALES` y los usan estas vistas y `storytelling/kpis.py`.

Las vistas son portables entre SQL Server (destino) y SQLite (pruebas): solo usan funciones ventana (`LAG`, `AVG ... OVER`),
`CASE` y `CAST`. En SQL Server los textos con tildes llevan el prefijo `N'...'`.

Vistas:
    vw_dim_fecha                 dim_fecha + `mes_indice` (año*12+mes, para DAX sin inteligencia de tiempo) y `dia_semana_num`
    vw_kpi_k1_k2_mensual         K1 venta neta mensual con su meta y estado · K2 ticket promedio con su variación y estado
    vw_kpi_k4_quiebre_semanal    K4 % de quiebre por semana y categoría, con estado
    vw_kpi_k5_campanas           K5 respuesta, conversión, ROAS por campaña, con estado
"""
from __future__ import annotations

from sqlalchemy import text

from src import schema

# Umbrales de la ficha de KPI 3.1.3 (provisionales: se calibraron con los datos sintéticos del proyecto)
UMBRALES = {
    "k1_alerta": 0.90,     # K1: alerta si la venta del mes es < 90 % del promedio de los 3 meses previos; meta si es >= 100 %
    "k2_alerta": -0.05,    # K2: alerta si el ticket cae más de 5 % respecto del mes anterior; meta si no baja
    "k4_meta": 5.0,        # K4: meta si el % de quiebre es <= 5
    "k4_alerta": 10.0,     # K4: alerta si el % de quiebre es > 10
    "k5_meta": 3.0,        # K5: meta si el ROAS es >= 3x
    "k5_alerta": 1.0,      # K5: alerta si el ROAS es < 1x
}

ESTADO_META, ESTADO_ALERTA = "Meta", "Alerta"
ESTADO_OBSERVACION = "En observación"
SIN_BASE, SIN_MES_ANTERIOR = "Sin base de comparación", "Sin mes anterior"

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _construir(dialecto: str) -> dict[str, str]:
    """SQL de cada vista para el dialecto indicado ('mssql' o cualquier otro, p. ej. 'sqlite')."""
    prefijo = "N" if dialecto == "mssql" else ""

    def lit(valor: str) -> str:
        return f"{prefijo}'{valor}'"

    u = UMBRALES
    columnas_fecha = ", ".join(f"d.{c.name}" for c in schema.dim_fecha.columns)
    casos_dia = "\n         ".join(f"WHEN {lit(n)} THEN {i}" for i, n in enumerate(DIAS_SEMANA, start=1))

    vw_dim_fecha = f"""SELECT {columnas_fecha},
       (d.anio * 12 + d.mes) AS mes_indice,
       CASE d.dia_semana
         {casos_dia}
       END AS dia_semana_num
FROM dim_fecha d"""

    vw_k1_k2 = f"""SELECT m.anio_mes,
       m.venta_neta,
       m.transacciones,
       m.ticket_promedio,
       m.meta_venta,
       CASE WHEN m.meta_venta IS NULL THEN NULL ELSE m.venta_neta / m.meta_venta END AS ratio_meta,
       CASE WHEN m.meta_venta IS NULL THEN {lit(SIN_BASE)}
            WHEN m.venta_neta / m.meta_venta < {u['k1_alerta']} THEN {lit(ESTADO_ALERTA)}
            WHEN m.venta_neta / m.meta_venta >= 1 THEN {lit(ESTADO_META)}
            ELSE {lit(ESTADO_OBSERVACION)} END AS estado_k1,
       m.ticket_mes_anterior,
       CASE WHEN m.ticket_mes_anterior IS NULL THEN NULL
            ELSE (m.ticket_promedio / m.ticket_mes_anterior - 1) * 100 END AS variacion_ticket_pct,
       CASE WHEN m.ticket_mes_anterior IS NULL THEN {lit(SIN_MES_ANTERIOR)}
            WHEN m.ticket_promedio / m.ticket_mes_anterior - 1 < {u['k2_alerta']} THEN {lit(ESTADO_ALERTA)}
            WHEN m.ticket_promedio >= m.ticket_mes_anterior THEN {lit(ESTADO_META)}
            ELSE {lit(ESTADO_OBSERVACION)} END AS estado_k2
FROM (
  SELECT b.anio_mes, b.venta_neta, b.transacciones, b.ticket_promedio,
         CASE WHEN COUNT(b.venta_neta) OVER (ORDER BY b.anio_mes ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) = 3
              THEN AVG(b.venta_neta) OVER (ORDER BY b.anio_mes ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING)
         END AS meta_venta,
         LAG(b.ticket_promedio) OVER (ORDER BY b.anio_mes) AS ticket_mes_anterior
  FROM (
    SELECT d.anio_mes AS anio_mes,
           CAST(SUM(f.monto_neto) AS FLOAT) AS venta_neta,
           COUNT(DISTINCT f.id_transaccion) AS transacciones,
           CAST(SUM(f.monto_neto) AS FLOAT) / COUNT(DISTINCT f.id_transaccion) AS ticket_promedio
    FROM fact_ventas f
    JOIN dim_fecha d ON d.fecha_key = f.fecha_key
    WHERE f.devolucion = 0
    GROUP BY d.anio_mes
  ) b
) m"""

    vw_k4 = f"""SELECT x.anio_semana,
       x.semana_desde,
       x.categoria,
       x.fotos,
       x.fotos_en_quiebre,
       x.pct_quiebre,
       CASE WHEN x.pct_quiebre <= {u['k4_meta']} THEN {lit(ESTADO_META)}
            WHEN x.pct_quiebre > {u['k4_alerta']} THEN {lit(ESTADO_ALERTA)}
            ELSE {lit(ESTADO_OBSERVACION)} END AS estado_k4
FROM (
  SELECT d.anio_semana AS anio_semana,
         MIN(d.fecha) AS semana_desde,
         p.categoria AS categoria,
         COUNT(*) AS fotos,
         SUM(f.quiebre) AS fotos_en_quiebre,
         100.0 * SUM(f.quiebre) / COUNT(*) AS pct_quiebre
  FROM fact_inventario f
  JOIN dim_fecha d ON d.fecha_key = f.fecha_key
  JOIN dim_producto p ON p.producto_key = f.producto_key
  GROUP BY d.anio_semana, p.categoria
) x"""

    vw_k5 = f"""SELECT y.codigo_campana,
       y.nombre_campana,
       y.tipo_campana,
       y.fecha_inicio,
       y.fecha_fin,
       y.contactados,
       y.respondieron,
       y.compraron,
       y.respuesta_pct,
       y.conversion_pct,
       y.ingreso_atribuido,
       y.inversion,
       y.roas,
       CASE WHEN y.roas >= {u['k5_meta']} THEN {lit(ESTADO_META)}
            WHEN y.roas < {u['k5_alerta']} THEN {lit(ESTADO_ALERTA)}
            ELSE {lit(ESTADO_OBSERVACION)} END AS estado_k5
FROM (
  SELECT c.codigo_campana AS codigo_campana,
         c.nombre_campana AS nombre_campana,
         c.tipo_campana AS tipo_campana,
         c.fecha_inicio AS fecha_inicio,
         c.fecha_fin AS fecha_fin,
         SUM(f.contactado) AS contactados,
         SUM(f.respondio) AS respondieron,
         SUM(f.compro) AS compraron,
         100.0 * SUM(f.respondio) / SUM(f.contactado) AS respuesta_pct,
         100.0 * SUM(f.compro) / SUM(f.contactado) AS conversion_pct,
         SUM(f.monto_venta_atribuida) AS ingreso_atribuido,
         SUM(f.costo_asignado) AS inversion,
         CAST(SUM(f.monto_venta_atribuida) AS FLOAT) / NULLIF(SUM(f.costo_asignado), 0) AS roas
  FROM fact_campanas f
  JOIN dim_campana c ON c.campana_key = f.campana_key
  GROUP BY c.codigo_campana, c.nombre_campana, c.tipo_campana, c.fecha_inicio, c.fecha_fin
) y"""

    return {
        "vw_dim_fecha": vw_dim_fecha,
        "vw_kpi_k1_k2_mensual": vw_k1_k2,
        "vw_kpi_k4_quiebre_semanal": vw_k4,
        "vw_kpi_k5_campanas": vw_k5,
    }


def construir_vistas(dialecto: str) -> dict[str, str]:
    return _construir(dialecto)


def crear_vistas(engine) -> list[str]:
    """(Re)crea las vistas en la base conectada. Idempotente: cada vista se borra y se vuelve a crear."""
    vistas = _construir(engine.dialect.name)
    with engine.begin() as conn:
        for nombre, sql in vistas.items():
            conn.execute(text(f"DROP VIEW IF EXISTS {nombre}"))
            conn.execute(text(f"CREATE VIEW {nombre} AS\n{sql}"))   # en SQL Server CREATE VIEW va solo en su lote
    return list(vistas)


def exportar_sql_server() -> str:
    """Script T-SQL para crear las vistas a mano desde SSMS (mismo SQL que usa el pipeline)."""
    partes = ["-- Vistas de la capa semántica de KPIs (generado desde src/vistas.py; no editar a mano:",
              "-- ejecutar scripts/exportar_schema_sql.py). Requiere SQL Server 2016 o superior.", ""]
    for nombre, sql in _construir("mssql").items():
        partes += [f"DROP VIEW IF EXISTS {nombre};", "GO", f"CREATE VIEW {nombre} AS", sql + ";", "GO", ""]
    return "\n".join(partes)
