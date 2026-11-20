# Decisiones de la Experiencia 3 (KPIs, dashboard y storytelling)

Documento único de referencia para la capa de datos y la capa BI. Si algo del repo o de un informe lo contradice, manda este documento.

## 1. Dónde vive cada cosa
Todo está en **este repositorio** (`DataRetail360-Pipeline`): los notebooks 05 y 06 y `storytelling/` importan `src/` (esquema, carga, calidad)
y leen el mismo Data Warehouse. No se duplica código en otro repositorio. Para separar lo entregado en la evaluación anterior de lo nuevo se
usan etiquetas y ramas de git (ver sección 6), no copias de archivos.

## 2. Modelo: constelación de 3 hechos
| Tabla de hechos | Grano | Medidas |
|---|---|---|
| `fact_ventas` | línea de transacción | `cantidad`, `monto_neto`, `monto_iva`, `monto_total`, **`costo_venta`**, **`margen_bruto`**, `devolucion` |
| `fact_inventario` | día × producto × sucursal (foto al cierre) | `stock_unidades`, `valor_stock`, `unidades_merma`, `quiebre` (semiaditivas: no se suman en el tiempo) |
| `fact_campanas` | cliente contactado × campaña × canal × fecha de envío × producto promocionado | `contactado`, `respondio`, `compro`, `monto_venta_atribuida`, `costo_asignado` |

Dimensiones nuevas o ampliadas: `dim_campana` (SCD1), `dim_producto.costo_unitario` (SCD1, CLP **neto** sin IVA, viene del ERP),
`dim_fecha.anio_mes` y `anio_semana` (ISO), con los nombres de mes y día **en español**.

## 3. Reglas de negocio
| Tema | Regla |
|---|---|
| Costo | `costo_venta = cantidad × costo_unitario` de la versión de producto vigente ese día; queda NULL si no hay costo. El costo no versiona la dimensión (se sobrescribe). |
| Devoluciones | K1, K2 y la atribución usan solo `devolucion = 0`. El margen y K6 deben hacer lo mismo. |
| Quiebre (K4) | `quiebre = 1` si `stock_unidades = 0`. El % de quiebre es el promedio de `quiebre` (producto × sucursal × día) y se mide por semana. El centro de distribución online (S00) tiene stock propio. |
| Atribución (K5) | Una venta se atribuye al contacto cuando el **mismo cliente compra el mismo producto promocionado dentro de 14 días** del envío (`VENTANA_ATRIBUCION_DIAS`). Si cae en la ventana de varias campañas, gana el envío más reciente: una venta cuenta como máximo una vez. |
| Costo asignado | Presupuesto de la campaña ÷ clientes contactados, en partes iguales; la suma por campaña cierra exacto con el presupuesto. |
| ROAS | Ingreso atribuido (neto) ÷ inversión. No es ROI: no descuenta el costo de lo vendido. |
| Fecha de corte | Es la última fecha con ventas (31-08-2025), **no** la fecha de hoy: con la fecha de hoy K3 daría 0. |
| K3 | La ventana de 90 días recién está completa desde junio; marzo a mayo arrancan inflados. |
| Cargas | Idempotentes. Si cambia `fact_ventas`, borrar y recargar `fact_campanas` (la venta atribuida depende de ella). |

Umbrales de la ficha 3.1.3 (provisionales, calibrados con los datos sintéticos): K1 alerta < 90 % del promedio de los 3 meses previos;
K4 meta ≤ 5 % y alerta > 10 %; K5 meta ≥ 3x y alerta < 1x.

## 4. Capa BI (Power BI Desktop sobre SQL Server)
Reglas de modelado para que el dashboard y el notebook den las mismas cifras:
- **Relaciones muchos-a-uno** desde cada hecho hacia sus dimensiones por la clave sustituta (`*_key`). Ocultar las claves en la vista de informe.
- **`dim_fecha` como tabla de fechas** (columna `fecha`). Ordenar `nombre_mes` por `mes`. `dia_semana` no trae número: crear una columna de orden o ordenar con una columna calculada.
- **Ruta ambigua a `dim_geografia`:** se llega por `dim_sucursal` y por `dim_cliente`. Dejar **activa la de sucursal** (la que responde «venta por región») y la de cliente inactiva, o duplicar la dimensión como `dim_geografia_cliente`.
- **Clientes:** contar con `rut_anonimizado` (no con `cliente_key`, que cambia con el SCD2). Excluir el miembro `-1` («No informado») en K3.
- **Devoluciones:** todas las medidas de venta filtran `devolucion = 0`.
- **Datos:** el DW vive en SQL Server de una sola máquina. Para trabajar en equipo, usar modo **Importar** y compartir el `.pbix`, o exportar vistas.
- **Colores:** paleta de la infografía 3.1.4 (navy `#0F2C4C`, teal `#0E8C84`, azul `#1F77B4`, naranja `#FF7F0E`, dorado `#C8860D`, gris `#9AA7B2`). Los estados llevan texto o ▲▼, nunca solo color.

## 5. Historia de los datos (sintética)
Marzo a julio estables; del 4 al 24 de agosto se retrasa la reposición de Tecnología: sube el quiebre (K4), cae la venta (K1, K2) y la campaña
«Semana Tech» tiene muchas respuestas pero pocas compras (ROAS < 1x). Cualquier informe debe declarar que los datos son sintéticos y que la relación
entre esos hechos está construida en el generador (`scripts/generar_datos_ejemplo.py`); con datos reales habría que probarla, no solo mostrarla.

## 6. Cómo incorporar estos cambios sin perder la entrega anterior
```bash
git tag eval-previa            # congela el estado entregado antes de la Experiencia 3
git switch -c experiencia-3    # rama de trabajo
git apply --check experiencia3_capa_bi.patch && git apply experiencia3_capa_bi.patch
```
Después: borrar la base de SQL Server (el esquema cambió y `crear_esquema` no agrega columnas a tablas existentes) y correr `python run_pipeline.py`.
