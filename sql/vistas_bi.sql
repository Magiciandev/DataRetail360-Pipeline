-- Vistas de la capa semántica de KPIs (generado desde src/vistas.py; no editar a mano:
-- ejecutar scripts/exportar_schema_sql.py). Requiere SQL Server 2016 o superior.

DROP VIEW IF EXISTS vw_dim_fecha;
GO
CREATE VIEW vw_dim_fecha AS
SELECT d.fecha_key, d.fecha, d.dia, d.mes, d.nombre_mes, d.trimestre, d.anio, d.dia_semana, d.es_fin_de_semana, d.anio_mes, d.anio_semana,
       (d.anio * 12 + d.mes) AS mes_indice,
       CASE d.dia_semana
         WHEN N'Lunes' THEN 1
         WHEN N'Martes' THEN 2
         WHEN N'Miércoles' THEN 3
         WHEN N'Jueves' THEN 4
         WHEN N'Viernes' THEN 5
         WHEN N'Sábado' THEN 6
         WHEN N'Domingo' THEN 7
       END AS dia_semana_num
FROM dim_fecha d;
GO

DROP VIEW IF EXISTS vw_kpi_k1_k2_mensual;
GO
CREATE VIEW vw_kpi_k1_k2_mensual AS
SELECT m.anio_mes,
       m.venta_neta,
       m.transacciones,
       m.ticket_promedio,
       m.meta_venta,
       CASE WHEN m.meta_venta IS NULL THEN NULL ELSE m.venta_neta / m.meta_venta END AS ratio_meta,
       CASE WHEN m.meta_venta IS NULL THEN N'Sin base de comparación'
            WHEN m.venta_neta / m.meta_venta < 0.9 THEN N'Alerta'
            WHEN m.venta_neta / m.meta_venta >= 1 THEN N'Meta'
            ELSE N'En observación' END AS estado_k1,
       m.ticket_mes_anterior,
       CASE WHEN m.ticket_mes_anterior IS NULL THEN NULL
            ELSE (m.ticket_promedio / m.ticket_mes_anterior - 1) * 100 END AS variacion_ticket_pct,
       CASE WHEN m.ticket_mes_anterior IS NULL THEN N'Sin mes anterior'
            WHEN m.ticket_promedio / m.ticket_mes_anterior - 1 < -0.05 THEN N'Alerta'
            WHEN m.ticket_promedio >= m.ticket_mes_anterior THEN N'Meta'
            ELSE N'En observación' END AS estado_k2
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
) m;
GO

DROP VIEW IF EXISTS vw_kpi_k4_quiebre_semanal;
GO
CREATE VIEW vw_kpi_k4_quiebre_semanal AS
SELECT x.anio_semana,
       x.semana_desde,
       x.categoria,
       x.fotos,
       x.fotos_en_quiebre,
       x.pct_quiebre,
       CASE WHEN x.pct_quiebre <= 5.0 THEN N'Meta'
            WHEN x.pct_quiebre > 10.0 THEN N'Alerta'
            ELSE N'En observación' END AS estado_k4
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
) x;
GO

DROP VIEW IF EXISTS vw_kpi_k5_campanas;
GO
CREATE VIEW vw_kpi_k5_campanas AS
SELECT y.codigo_campana,
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
       CASE WHEN y.roas >= 3.0 THEN N'Meta'
            WHEN y.roas < 1.0 THEN N'Alerta'
            ELSE N'En observación' END AS estado_k5
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
) y;
GO
