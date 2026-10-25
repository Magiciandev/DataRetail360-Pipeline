# Acuerdos técnicos del equipo

Estas convenciones evitan que los tres notebooks se contradigan (las mismas inconsistencias que aparecieron entre
los notebooks 2.1.4, 2.2.3 y 2.4.4 de clase). **Están implementadas por defecto en `src/`.** Cada fila de la
tabla de decisiones fue una *propuesta*: el equipo la **aprobó completa el 24-10-2026**. Si alguna cambia, anótenlo en la última columna.

## 1. Convenciones ya implementadas en el código

| Tema | Convención | Dónde |
|---|---|---|
| Columnas SCD Tipo 2 | `valido_desde`, `valido_hasta`, `es_actual` | `src/schema.py` |
| Fecha de inicio de la primera versión | `1900-01-01` (para que cualquier venta histórica encuentre versión) | `src/config.py` |
| `valido_hasta` de la versión vigente | `9999-12-31` (en vez de `NULL`: simplifica los cruces por fecha) | `src/config.py` |
| Cierre de una versión | `valido_hasta` = fecha efectiva del cambio − 1 día (las versiones no se solapan) | `src/db.py` |
| Claves sustitutas | `*_key` enteras asignadas por el pipeline (no IDENTITY), para poder usar `-1` | `src/db.py` |
| Miembro «No informado» | clave `-1` en cada dimensión (Sucursal, Canal, Producto, Cliente, Geografía) | `src/schema.py` |
| Carga de hechos | idempotente por `(id_transaccion, linea)` | `src/db.py` |
| Reproceso de snapshots | cada fila se compara con la versión vigente **a la fecha efectiva**; reprocesar es seguro, contradecir la historia falla | `src/db.py` |
| Datos personales | el RUT se guarda como hash con sal (`rut_anonimizado`); nombre, correo y fecha de nacimiento no llegan al DW; los logs redactan RUT y correos | `src/quality.py`, `src/logger.py` |

## 2. Decisiones por confirmar

| # | Decisión | Propuesta | Alternativa | Decisión del equipo |
|---|---|---|---|---|
| 1 | Definición de `monto_neto` | Los archivos traen el monto **con IVA**: `monto_neto = monto_total / 1.19` y `monto_iva = monto_total − monto_neto`. Coincide con el EP1 (neto sin IVA) y evita las tres definiciones distintas de los notebooks de clase | Usar el monto tal cual | ✅ Aprobada |
| 2 | Devoluciones | Columna `devolucion` (0/1) en `fact_ventas`, como en el Diccionario 2.1.5; las KPIs excluyen `devolucion = 1` | Tabla `Fact_Devoluciones` separada, como en el EP1 | ✅ Aprobada |
| 3 | Ventas anuladas | Se rechazan con motivo `venta_anulada` | Cargarlas marcadas | ✅ Aprobada |
| 4 | Sucursal faltante | Clave `-1` («Sucursal no informada»), igual que el EP1 (en el notebook de clase era el texto `SIN_ASIGNAR`) | Texto `SIN_ASIGNAR` | ✅ Aprobada |
| 5 | Venta sin RUT | Cliente `-1` (venta sin cliente identificado) | Rechazar | ✅ Aprobada |
| 6 | Clave para deduplicar ventas | `(id_transaccion, linea)` (en clase se usaba fecha + sku + sucursal + canal, que descarta ventas legítimas) | — | ✅ Aprobada |
| 7 | SCD de cada dimensión | Geografía, Producto y Cliente: Tipo 2 (según la plantilla 2.1.3). Sucursal, Canal: Tipo 1. Fecha: sin SCD | Evaluar Tipo 3 donde el costo de las filas extra no se justifique (lo pidió el profesor) | ✅ Aprobada |
| 8 | `geografia_key` en `dim_cliente` | Atributo SCD1: se actualiza si la comuna se corrige, sin versionar | Incluirlo en el SCD2 | ✅ Aprobada |
| 9 | Bronze con datos personales | `data/` no se versiona y se documenta que Bronze contiene RUT crudo | Anonimizar antes de escribir Bronze | ✅ Aprobada |
| 10 | Motor de destino | SQL Server (SSMS) como principal; SQLite para que cualquiera pueda reproducir el proyecto sin instalar nada | Solo uno de los dos | ✅ Aprobada |

## 3. Reparto

| Notebook | Responsable | Rama |
|---|---|---|
| 01 Dim_Geografía | Cristóbal Cárdenas o Mara Cantillana (según cuál elija cada uno) | `feature/dim-geografia` |
| 02 Dim_Producto | Victor Navarrete | `feature/dim-producto` |
| 03 Dim_Cliente | La otra persona entre Cristóbal Cárdenas y Mara Cantillana | `feature/dim-cliente` |
| 04 Integración (`dim_fecha`, `dim_canal`, `dim_sucursal`, `fact_ventas`) | Los tres (se trabaja en conjunto) | `feature/integracion` |

## 4. Flujo de trabajo en Git

1. Una rama por tarea (`feature/...`), nunca trabajar directo en `main`.
2. Commits pequeños con mensaje claro (`feat(dim-cliente): rechaza RUT inválidos`).
3. Pull Request revisado por **otro integrante** usando la plantilla del repositorio (checklist de code review).
4. Antes de abrir el PR: *Restart & Run All* del notebook sin errores. (Las pruebas de `tests/` son opcionales: el equipo decidió no escribir nuevas.)
5. Los notebooks se suben **con sus salidas** (son la evidencia), pero sin datos personales visibles.
