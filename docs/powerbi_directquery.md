# Power BI en DirectQuery: conexión, modelo y medidas

Guía para conectar Power BI Desktop al Data Warehouse y construir el tablero del wireframe. Antes de empezar: el pipeline debe haber corrido
(`python run_pipeline.py`), lo que crea las tablas y las vistas de KPIs (`python run_pipeline.py --solo vistas` las recrea).

> Las medidas y los pasos de este documento **no se ejecutaron en Power BI** al prepararlos. La hoja de validación (sección 8) es el control:
> compara cada medida con las vistas SQL, que sí están probadas. No den por buena una medida hasta que su diferencia dé 0.

## 1. Qué se conecta
| Objeto | Para qué | Nota |
|---|---|---|
| `fact_ventas`, `fact_inventario`, `fact_campanas` | Hechos | Las medidas viven en `fact_ventas` |
| `dim_producto`, `dim_cliente`, `dim_sucursal`, `dim_geografia`, `dim_canal`, `dim_campana` | Dimensiones | |
| `vw_dim_fecha` | Tabla de fechas | **Renombrar a `dim_fecha`**. No cargar la tabla `dim_fecha` original: la vista agrega `mes_indice` y `dia_semana_num` |
| `vw_kpi_k1_k2_mensual`, `vw_kpi_k4_quiebre_semanal`, `vw_kpi_k5_campanas` | Solo hoja de validación | Sin relaciones |

No cargar `auditoria_*`.

## 2. Conectar
1. Power BI Desktop → Inicio → **Obtener datos** → **SQL Server**.
2. Servidor y base de datos: los mismos de su `.env` (`DB_HOST` y `DB_NAME`, normalmente `localhost` y `DataRetail360_DW`; si usan una instancia con nombre, la misma que ven en SSMS).
3. **Modo de conectividad de datos: DirectQuery.** No escribir instrucción SQL.
4. Credenciales: Windows si `DB_TRUSTED_CONNECTION=yes`, o el usuario SQL del `.env`. Si aparece un aviso de cifrado en el equipo local, aceptarlo.
5. En el navegador marcar los 12 objetos de la sección 1 y **Cargar**. Power BI usa su propio conector: no necesita el driver ODBC del pipeline.

## 3. Relaciones (vista Modelo)
Todas **muchos a uno** (`*:1`), con el filtro en una sola dirección (de la dimensión hacia el hecho). Power BI detecta la mayoría por el nombre de la columna; revisen que queden estas 15:

| Desde (muchos) | Hacia (uno) | Estado |
|---|---|---|
| `fact_ventas[fecha_key]` | `dim_fecha[fecha_key]` | activa |
| `fact_ventas[producto_key]` | `dim_producto[producto_key]` | activa |
| `fact_ventas[cliente_key]` | `dim_cliente[cliente_key]` | activa |
| `fact_ventas[sucursal_key]` | `dim_sucursal[sucursal_key]` | activa |
| `fact_ventas[canal_key]` | `dim_canal[canal_key]` | activa |
| `fact_inventario[fecha_key]` | `dim_fecha[fecha_key]` | activa |
| `fact_inventario[producto_key]` | `dim_producto[producto_key]` | activa |
| `fact_inventario[sucursal_key]` | `dim_sucursal[sucursal_key]` | activa |
| `fact_campanas[campana_key]` | `dim_campana[campana_key]` | activa |
| `fact_campanas[cliente_key]` | `dim_cliente[cliente_key]` | activa |
| `fact_campanas[producto_key]` | `dim_producto[producto_key]` | activa |
| `fact_campanas[canal_key]` | `dim_canal[canal_key]` | activa |
| `fact_campanas[fecha_key]` (fecha de envío) | `dim_fecha[fecha_key]` | activa |
| `dim_sucursal[geografia_key]` | `dim_geografia[geografia_key]` | **activa** |
| `dim_cliente[geografia_key]` | `dim_geografia[geografia_key]` | **inactiva** (evita la ruta ambigua) |

Opcional: en cada relación de hecho a dimensión, activar «Suponer integridad referencial» (consultas más rápidas). Es válido porque toda clave existe en su dimensión, incluido el miembro «No informado» (`-1`).

## 4. Columnas
- **Ocultar** las claves (`*_key`) y las columnas técnicas (`valido_desde`, `valido_hasta`, `es_actual`) y las columnas numéricas de los hechos: se usan las medidas.
- **Ordenar por columna:** `dim_fecha[nombre_mes]` por `mes`; `dim_fecha[dia_semana]` por `dia_semana_num`.
- Columnas numéricas de los hechos: resumen «No resumir».

## 5. Medidas
1. Vista **Consulta DAX** (DAX query view) → pegar todo `powerbi/medidas_dax.dax` → botón **Actualizar el modelo con los cambios**. Agrega las medidas a `fact_ventas`.
2. En la vista Modelo, mover cada medida a su carpeta (el nombre está en el comentario de cada bloque): Parámetros, K1 y K2 · Base, K1 y K2 · Gráficos, K1 y K2 · Tarjetas, K4, K5, Venta por categoría y Validación.
3. Formatos: `K1 · Venta del mes (MM)` → `#,0" MM"` · `K2 · Ticket del mes (miles)` → `$#,0" mil"` · `% Quiebre`, `K4 · % Quiebre del mes`, `% Quiebre Tecnología`, `% Respuesta`, `% Conversión` → `0.0" %"` · `ROAS`, `K5 · Peor ROAS` → `0.00"x"` · `% de la venta neta` → `0 %`.

Cómo calcula: los meses previos se buscan con `mes_indice` (año×12+mes), sin funciones de inteligencia de tiempo. La meta de K1 queda vacía si falta alguno de los 3 meses previos. El mes de referencia de las tarjetas es el último mes con ventas dentro de los filtros.

## 6. Qué afecta cada filtro
| Filtro | K1 y K2 | K4 | K5 | Venta por categoría | Motivo |
|---|---|---|---|---|---|
| Mes (`dim_fecha[anio_mes]`) | sí | sí | sí | sí | todos los hechos tienen fecha |
| Región (`dim_geografia[region]`) | sí | sí | **no** | sí | las campañas no tienen sucursal |
| Canal (`dim_canal[canal]`) | sí | **no** | sí | sí | el inventario no tiene canal |

Pongan una nota pequeña en el tablero («Región no aplica a campañas; Canal no aplica a inventario»). Para que los segmentadores valgan en todas las hojas: Vista → Sincronizar segmentadores. En DirectQuery conviene Archivo → Opciones → **Reducción de consultas** → botón «Aplicar» en los segmentadores.

## 7. Visuales (wireframe → campos)
| Visual | Tipo | Campos |
|---|---|---|
| Tarjetas K1, K2, K4, K5 | Tarjeta | valor: `K1 · Venta del mes (MM)`, `K2 · Ticket del mes (miles)`, `K4 · % Quiebre del mes`, `K5 · Peor ROAS` · texto: `K1 · Detalle`, `K2 · Detalle`, `K4 · Detalle`, `K5 · Detalle` · franja o acento con color por campo: `K1 · Color`, `K2 · Color`, `K4 · Color`, `K5 · Color` (si su versión no lo permite, el texto de Detalle ya dice el estado) |
| V1 · K1 | Líneas | eje `dim_fecha[anio_mes]`; valores `Venta neta (MM)`, `Meta K1 (MM)`, `Alerta K1 (MM)` · título dinámico: `K1 · Título del gráfico` |
| V2 · K4 | Líneas | eje `dim_fecha[anio_semana]`; valores `% Quiebre`, `% Quiebre Tecnología` · líneas constantes en 5 y 10 (panel Analítica) · título: `K4 · Título del gráfico` |
| V3 · K5 | Barras horizontales | eje `dim_campana[nombre_campana]`; valor `ROAS`; color por campo `K5 · Color de barra`; etiqueta de datos `K5 · Etiqueta de barra`; líneas constantes en 1 y 3 · título: `K5 · Título del gráfico` |
| V4 · categorías | Barras horizontales | eje `dim_producto[categoria]` (filtro del visual: distinta de «NO INFORMADO»); valor `Venta neta (MM)`; etiqueta `% de la venta neta` · título: `V4 · Título del gráfico` |
| Segmentadores | Lista desplegable | `dim_fecha[anio_mes]`, `dim_geografia[region]`, `dim_canal[canal]` |

Título dinámico: Formato del visual → Título → Texto → botón fx → «Valor de campo» → la medida.

## 8. Hoja de validación (ocultarla en la defensa)
Tres tablas, con campos de las vistas `vw_kpi_*` (sin relaciones) y las medidas `Val · …`:
| Tabla | Filas | Medidas | Esperado |
|---|---|---|---|
| K1 y K2 | `vw_kpi_k1_k2_mensual[anio_mes]` | `Val · Dif venta neta`, `Val · Dif meta K1`, `Val · Estado K1`, `Val · Estado K2` | diferencias 0 y estados «OK» |
| K4 | `vw_kpi_k4_quiebre_semanal[anio_semana]` y `[categoria]` | `Val · Dif % quiebre` | 0 |
| K5 | `vw_kpi_k5_campanas[codigo_campana]` | `Val · Dif ROAS`, `Val · Estado K5` | 0 y «OK» |

Con los datos de ejemplo y sin filtros, las tarjetas deben mostrar: **K1** 185 MM, 20 % bajo la meta, Alerta · **K2** $345 mil, −13 % vs mes anterior, Alerta · **K4** 12,5 % (agosto), Alerta · **K5** peor ROAS 0,81x, Semana Tech, Alerta. Los títulos: «En agosto la venta neta quedó 20 % bajo el promedio de los 3 meses previos» y «Semana Tech respondió más (35,5 %) y rindió menos (ROAS 0,81x)».

## 9. Problemas frecuentes
| Síntoma | Qué revisar |
|---|---|
| No conecta | Servidor y base iguales a los del `.env` y a los de SSMS; autenticación (Windows o usuario SQL); que el servicio de SQL Server esté activo |
| «Función no admitida en DirectQuery» | Anoten qué medida falla y el mensaje; las medidas no usan funciones de inteligencia de tiempo |
| Una medida sale vacía | El filtro de Mes no tiene ventas; la relación `fecha_key` entre el hecho y `dim_fecha`; que `dim_fecha` sea la vista `vw_dim_fecha` |
| Las tarjetas muestran otro mes o nada | Reemplazar `Mes de referencia` por `MAX ( dim_fecha[mes_indice] )` y seleccionar un solo mes en el segmentador |
| Validación en «DIFIERE» solo en estados | Vistas creadas sin el prefijo `N` de texto Unicode: recrearlas con `python run_pipeline.py --solo vistas` o ejecutar `sql/vistas_bi.sql` |
| La región no cambia K5 | Es lo esperado (sección 6) |
| Lento | Reducción de consultas (sección 6) y «Suponer integridad referencial» (sección 3) |

## 10. Antes de la defensa
- SQL Server activo y pipeline corrido hoy (revisar `auditoria_ejecuciones`); `python run_pipeline.py --solo vistas`.
- Abrir el `.pbix`: hoja de validación en 0 y «OK», y las tarjetas con los valores esperados.
- Guardar una **copia de respaldo en modo Importar** (cambiar el modo de almacenamiento de las tablas a Importar; por lo que recuerdo de la documentación, el cambio no se puede revertir, por eso es una copia) y un PDF del tablero.
- Ocultar la hoja de validación en la copia de la defensa y probar los tres filtros en vivo.
