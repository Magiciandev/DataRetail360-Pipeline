# DataRetail 360 — Pipeline ETL a Data Warehouse (esquema estrella)

> IDY1102 · Estructuras y Visualización de Datos · Unidad 2 · Experiencia 2 · EP3 · RA2 · IL 2.1–2.4

## 1. Descripción

Pipeline en Python (Pandas + SQLAlchemy) que integra las fuentes dispersas de DataRetail 360 (ventas de tiendas en CSV,
ventas de e-commerce en JSON anidado, clientes, productos y geografía), las limpia y valida, y las carga en un **Data Warehouse
dimensional** (esquema estrella) con arquitectura **Medallion**. El resultado alimenta los KPIs y dashboards de la Experiencia 3
y resuelve el problema central del caso: cifras distintas entre áreas, datos sin calidad y sin trazabilidad.

> **Estado:** esqueleto del proyecto. La infraestructura compartida (`src/`) está implementada y probada; en los notebooks
> quedan marcadas con **✏️ TODO** las reglas de calidad y las búsquedas de claves que debe escribir cada integrante.

## 2. Arquitectura

```
 Fuentes                      Bronze                  Silver                    Gold (Data Warehouse)
 ventas_pos.csv        ─►  Parquet crudo     ─►   Parquet limpio      ─►   dim_fecha   dim_geografia (SCD2)
 ventas_ecommerce.json      (sin cambios)         + auditoria_rechazos       dim_producto (SCD2)  dim_cliente (SCD2)
 clientes / productos /                                                      dim_sucursal  dim_canal
 geografia (snapshots)                                                       fact_ventas  ◄── claves vigentes a la fecha de cada venta
```

- **Fuentes:** CSV (POS, maestros) y JSON anidado (e-commerce). Ver sección 7.
- **Transformaciones:** deduplicación, homologación de SKU y canal, normalización de fechas (4 formatos + UTC), validación de RUT,
  anonimización, validación de montos, imputación al miembro «No informado» (`-1`).
- **Destino:** SQL Server (SSMS) o SQLite, a elección en `.env`. Tablas `dim_*`, `fact_ventas` y dos de auditoría
  (`auditoria_rechazos`, `auditoria_ejecuciones`).
- **Organización del trabajo:** un notebook por dimensión (01 Geografía, 02 Producto, 03 Cliente) y uno de integración (04) que
  carga `dim_fecha`, `dim_canal`, `dim_sucursal` y `fact_ventas`.

## 3. Requisitos

- Python 3.10+
- Librerías: ver `requirements.txt` (`pandas`, `sqlalchemy`, `pyarrow`, `python-dotenv`, `nbclient`, `pytest`…)
- SQL Server + SSMS con *ODBC Driver 17/18 for SQL Server* (ver Guía 2.2.2) — **opcional**: con `DB_ENGINE=sqlite` no se necesita nada más.

## 4. Instalación

```bash
git clone [url-del-repositorio]
cd datarretail360-pipeline
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 5. Configuración

> ⚠️ **Nunca** subas credenciales al repositorio. Todo valor sensible va en variables de entorno.

```bash
cp .env.example .env             # En Windows: copy .env.example .env
```

**SQL Server:** antes de la primera ejecución crea la base vacía en SSMS (`CREATE DATABASE DataRetail360_DW;`): el pipeline crea las tablas, no la base. `DB_DRIVER` debe coincidir con el *ODBC Driver* instalado (17 o 18) y, con instancia nombrada, `DB_HOST` va como `localhost\SQLEXPRESS`.
**Si aún no tienes SQL Server**, desarrolla tu notebook con `DB_ENGINE=sqlite` (no requiere instalar nada); la corrida final y la evidencia se hacen en SQL Server.

Edita `.env`: motor de base de datos (`DB_ENGINE=sqlserver` o `sqlite`), servidor y base, y **`RUT_SALT`** (obligatoria: sal con la que se
anonimiza el RUT; usa un texto largo y aleatorio). Con autenticación de Windows deja `DB_TRUSTED_CONNECTION=yes` y sin usuario/contraseña.

## 6. Uso

```bash
python run_pipeline.py                 # snapshots 1 y 2 de las dimensiones y luego la integración
python run_pipeline.py --snapshots 1   # solo el primer snapshot
python run_pipeline.py --solo 03       # un solo notebook, mientras lo desarrollas
pytest                                 # (opcional) pruebas de los módulos compartidos y de la estructura de los notebooks
python scripts/exportar_schema_sql.py  # regenera sql/schema_sqlserver.sql (DDL para revisar en SSMS)
```

`run_pipeline.py` ejecuta los notebooks en el orden de sus dependencias y **se detiene con código 1 si uno falla**. Cada notebook ya
ejecutado (con sus salidas) queda en `logs/ejecutados/` como evidencia; el log de texto, en `logs/pipeline_AAAAMMDD.log`.
Para trabajar un notebook a mano: ábrelo en VS Code/Jupyter y usa *Restart & Run All*.

**Orden de ejecución y por qué importa:** Geografía → Producto → Cliente (necesita Geografía) → Integración (necesita todo).
Cada dimensión se procesa por *snapshots* (1 = carga inicial, 2 = cambios posteriores) para poder demostrar el SCD Tipo 2.

## 7. Estructura del proyecto

```
.
├── notebooks/
│   ├── 01_dim_geografia.ipynb            # SCD2 · alimenta a Sucursal y Cliente
│   ├── 02_dim_producto.ipynb             # SCD2 · homologación de SKU
│   ├── 03_dim_cliente.ipynb              # SCD2 · RUT anonimizado, datos personales
│   └── 04_fact_ventas_integracion.ipynb  # dim_fecha, dim_canal, dim_sucursal y fact_ventas
├── src/
│   ├── config.py      # lee .env (nunca secretos en el código)
│   ├── logger.py      # logging a consola y archivo; redacta RUT y correos
│   ├── schema.py      # definición única de las tablas (SQLite y SQL Server)
│   ├── db.py          # engine, SCD1/SCD2, carga idempotente, rechazos, auditoría, reintentos
│   ├── quality.py     # reglas de calidad reutilizables (RUT, fechas, SKU, rechazos, chequeo SCD2)
│   ├── extract.py     # lectura de CSV/JSON con trazabilidad de origen
│   ├── medallion.py   # capas Bronze/Silver en Parquet
│   └── errores.py     # errores recuperables vs. fatales
├── sql/schema_sqlserver.sql   # DDL generado desde schema.py
├── data/sample/       # datos de ejemplo SINTÉTICOS (se versionan); el resto de data/ no
├── tests/             # pruebas opcionales de src/ y de la plantilla de los notebooks
├── docs/acuerdos_tecnicos.md  # convenciones y decisiones del equipo (aprobadas)
├── docs/CONTEXTO_CASO.md      # contexto completo del caso, para el equipo y para asistentes de IA
├── scripts/           # generar_datos_ejemplo.py, exportar_schema_sql.py
├── logs/              # registros y notebooks ejecutados (NO se versiona)
├── .github/pull_request_template.md   # checklist de code review
├── .env.example · .gitignore · requirements.txt · run_pipeline.py
└── README.md
```

## 8. Datos de ejemplo

Son **sintéticos** (`scripts/generar_datos_ejemplo.py`); los RUT tienen dígito verificador válido pero cuerpo fuera del rango de personas reales.
Traen los problemas de calidad que describe el caso, plantados a propósito:

| Archivo | Problemas plantados |
|---|---|
| `geografia_snapshot_1/2.csv` | `codigo_comuna` repetido, coordenadas imposibles; en el snapshot 2 Chillán cambia de zona comercial |
| `productos_snapshot_1/2.csv` | SKU con minúsculas/espacios, producto duplicado con SKU escrito distinto, fila sin SKU; en el snapshot 2 dos productos cambian de categoría/línea y aparece uno nuevo |
| `clientes_snapshot_1/2.csv` | RUT inválidos, mismo cliente con RUT escrito distinto, comuna vacía o inexistente; en el snapshot 2 hay clientes que cambian de comuna o segmento y clientes nuevos |
| `ventas_pos.csv` | fechas en 3 formatos y una imposible, líneas duplicadas, montos negativos, ventas anuladas y devueltas, SKU inexistente, sucursal vacía, venta sin cliente |
| `ventas_ecommerce.json` | JSON anidado (`items` por orden), fechas UTC, una orden repetida, órdenes anuladas/devueltas, canal escrito de 3 formas |

Si el curso entrega los CSV/JSON oficiales, basta reemplazar los archivos de `data/sample/` (o apuntar `DATA_DIR` a otra carpeta) y ajustar las reglas.

## 9. Calidad de datos

| Regla | Dimensión de calidad | Acción |
|---|---|---|
| Sin claves naturales duplicadas (comuna, SKU, RUT, línea de venta) | Unicidad | Se conserva la primera aparición; el resto va a `auditoria_rechazos` |
| SKU y canal homologados; textos sin espacios sobrantes | Consistencia | Normalización en `quality.py` |
| Fechas en un único formato; coordenadas dentro de Chile; montos ≥ 0; RUT con DV correcto | Validez | Lo inválido va a rechazos con su motivo |
| Comuna, sucursal o cliente faltante | Completitud | Se asigna al miembro «No informado» (`-1`), no se pierde la venta |
| Monto con IVA → neto e IVA recalculados | Precisión | `monto_neto = monto_total / 1.19` |
| Atributos que cambian en el tiempo (zona, categoría, comuna, segmento) | Trazabilidad histórica | SCD Tipo 2 con `valido_desde`, `valido_hasta`, `es_actual` |

Las convenciones y las decisiones por confirmar están en [`docs/acuerdos_tecnicos.md`](docs/acuerdos_tecnicos.md).

## 10. Logging y manejo de errores

- Los registros se guardan en `logs/` con niveles INFO/WARNING/ERROR y **redactan RUT y correos** (Ley 21.719).
- Cada proceso queda en `auditoria_ejecuciones` (inicio, fin, estado OK/ERROR, filas leídas/cargadas/rechazadas): trazabilidad dentro del propio DW.
- Las filas inválidas se guardan en `auditoria_rechazos` con su archivo de origen, número de fila y motivo (sin datos personales).
- Los errores transitorios de conexión se **reintentan**; los fatales detienen el pipeline y se registran. Nunca se falla en silencio.
- El pipeline es **idempotente**: re-ejecutarlo (incluso reprocesando snapshots antiguos) no duplica datos ni crea versiones de más; un dato retroactivo que contradice la historia falla con un error claro.

## 11. Pruebas (opcionales)

El equipo decidió no escribir pruebas nuevas por ahora (no es contenido visto en clase). Las que vienen en `tests/` son del esqueleto: se pueden ignorar o correr con `pytest` si alguien toca `src/`.

```bash
pytest
```

Cubren la lógica compartida (RUT, fechas, SCD1/SCD2 y búsqueda de la versión vigente a una fecha, idempotencia, rechazos sin datos personales, auditoría, reintentos) y que los
notebooks mantengan la plantilla común y no incluyan credenciales.

## 12. Equipo

| Integrante | Notebook |
|---|---|
| Cristóbal Cárdenas o Mara Cantillana (según elijan) | 01 Dim_Geografía |
| Victor Navarrete | 02 Dim_Producto |
| La otra persona entre Cristóbal y Mara | 03 Dim_Cliente |
| Los tres | 04 Integración |

## 13. Licencia / uso académico

Proyecto académico para el curso IDY1102 (Duoc UC). Datos de ejemplo del caso ficticio DataRetail 360.
