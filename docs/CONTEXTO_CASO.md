# Contexto del caso DataRetail 360 — IDY1102 (Estructuras y Visualización de Datos)

> Documento de contexto para el equipo y para asistentes de IA. Resume el caso, lo ya entregado (EP1), lo que se vio en clase en la
> Experiencia 2, las reglas de la evaluación actual (EP3) y el estado del repositorio. Última actualización: 24-10-2026.
> Si algo de aquí contradice un documento oficial del curso, **manda el documento oficial**.

---

## 0. Cómo usar este documento

**Equipo:** léanlo antes de repartirse el trabajo; las secciones 6 y 7 son las que más cambian.

**Asistentes de IA — instrucciones:**
- Responde en **español**, con tono técnico y formal (así lo pide la pauta).
- Usa solo lo que está aquí o en los archivos que te entregue el equipo. Si un dato no aparece, **pregunta o dilo**; no lo inventes.
- **Nunca** pidas ni escribas datos personales reales (RUT, correos, nombres de clientes) ni credenciales. Los datos de ejemplo son sintéticos.
- Es un trabajo **evaluado y grupal**: ayuda a entender, diseñar y revisar; no reemplaces el razonamiento del equipo en lo que se evalúa.
- Mantén la **coherencia** con las decisiones de las secciones 4 y 7 (modelo, convenciones, KPIs). Si propones cambiarlas, dilo explícitamente.
- Lo marcado con ⚠️ son incertidumbres conocidas.

---

## 1. La asignatura y las evaluaciones

| Dato | Valor |
|---|---|
| Asignatura | IDY1102 · Estructuras y Visualización de Datos · Duoc UC (Escuela de Informática y Telecomunicaciones) |
| Docente (según portada del EP1) | José Zúñiga Gallardo · sección 003D |
| Caso transversal | **DataRetail 360** (retail chileno ficticio) |
| Evaluación del curso (diapositivas) | 60 % parciales (informes técnicos y defensas) · 40 % transversal (examen práctico con presentación) |

| Evaluación | Peso | Plazos | Estado |
|---|---|---|---|
| **EP1** — Encargo: plan inicial del proyecto analítico (Kimball) | 7 % | instrucciones semana 2, entrega semana 5 (4 semanas) | **Entregado** (informe + presentación de 10 diapositivas) |
| **EP3** — Entregable (informe) de la etapa técnica | 9 % | instrucciones semana 7, entrega **semana 13** (6 semanas) | **En curso** |
| **EP4** — Presentación de ese trabajo | ⚠️ peso y fecha por confirmar | junto con la entrega | Pendiente |

- Ambos son **grupales, máximo 3 estudiantes**. Equipo del EP1 (portada): Mara Cantillana, Victor Navarrete y Cristobal Cárdenas. ⚠️ Confirmar integrantes del EP3.
- **Numeración (aclarada por el equipo):** **EP3 = el entregable con su informe** y **EP4 = la presentación**; las dos juntas forman la **segunda nota** de la asignatura (el equipo la llama "evaluación 2"). Los materiales de clase hablan de "EP2/EA2" para lo mismo.

---

## 2. El caso de negocio: DataRetail 360

**Empresa:** retail con presencia nacional (tecnología, hogar y accesorios) que vende en **tiendas físicas y e-commerce**. Creció rápido en sucursales, comercio electrónico y campañas segmentadas, pero **sin estrategia de datos integrada**.

**Problemática central:** no existe una solución analítica integrada que transforme datos *dispersos, inconsistentes y poco trazables* en información confiable, reutilizable y comprensible para decidir.

**Los tres dolores (formulación del informe EP1):**
1. **Cifras oficiales discrepantes.** La venta neta del mes es **$820.000.000 (Comercial), $790.000.000 (Finanzas) y $835.000.000 (Marketing)**, por filtros distintos, fechas de corte desalineadas y falta de consenso sobre impuestos, anulaciones y notas de crédito.
2. **Baja calidad e interoperabilidad.** Clientes duplicados (correos/nombres), SKU sin homologar entre tiendas y web, ventas sin sucursal, inventario incompleto o desactualizado, formatos de fecha/monto distintos.
3. **Dependencia de procesos manuales.** Excel y CSV consolidados a mano, errores de digitación, sin trazabilidad ni auditoría.

**Otros puntos del caso:** sin arquitectura analítica formal (no separa sistemas transaccionales de estructuras para análisis); baja trazabilidad del origen y transformación de cada cifra; la gerencia quiere **cultura orientada a datos** y explora **IA generativa** (consultas en lenguaje natural) pero con validación, calidad, seguridad y ética.

**Necesidad del negocio:** consolidar fuentes, mejorar calidad/consistencia/trazabilidad, estructurar datos para análisis reutilizable, **definir indicadores comunes**, construir dashboards, dar acceso autónomo a usuarios de negocio e incorporar IA generativa de forma responsable.

**Preguntas de negocio del caso:** ¿qué sucursales/canales/categorías explican mejor o peor desempeño? · ¿qué productos tienen baja rotación o riesgo de quiebre? · ¿qué campañas rinden mejor? · ¿cómo se comportan los clientes por recurrencia, canal o segmento? · ¿qué indicadores deben seguir las áreas? · ¿cómo asegurar que dashboards sean confiables? · ¿cómo incorporar IA generativa sin comprometer calidad?

---

## 3. Contenido visto en clase

### Experiencia 1 — Planificar (semanas 1–6)
- **Kimball:** enfoque bottom-up centrado en procesos de negocio; ciclo requerimientos → modelo dimensional → diseño físico → ETL → BI. **Grano primero**; hechos se miden, dimensiones se filtran.
- **Dimensiones conformadas:** compartidas por varios procesos; evitan que cada área defina "Producto" a su manera. **Bus Matrix:** filas = procesos, columnas = dimensiones conformadas.
- **Normalizado vs desnormalizado:** se normaliza el sistema transaccional (integridad de escritura) y se desnormaliza el DW (velocidad de lectura y comprensión del negocio).
- **Plan de Proyecto Analítico (plantilla 1.4.2, 11 secciones):** identificación, problema, objetivos, alcance, preguntas y nivel de analítica, KPIs, fuentes, procesos priorizados, stack, resguardo y riesgos, cronograma.
- Actividad 1.1 (preguntas y niveles de analítica), 1.2 (gobernanza: Ley 19.628 vs 21.719), 1.3 (comparación BI/IA con matriz ponderada), 1.4 (Bus Matrix).

### Experiencia 2 — Construir (semanas 7–12)
- **2.1 Modelado dimensional** (IL 2.1, 2.2): esquema estrella vs copo de nieve (estrella por defecto), hechos transaccional/snapshot/acumulado, claves sustitutas, jerarquías (drill-down), dimensiones conformadas y espaciales, **SCD tipos 1, 2 y 3**, capa semántica para IA.
  - **SCD:** Tipo 1 sobrescribe (sin historia); Tipo 2 crea fila nueva con vigencia (historia completa); Tipo 3 guarda el valor anterior en otra columna (historia parcial).
  - 🗣️ **El profesor** comentó que en su experiencia el **Tipo 3** es el más usado y pidió **evaluar costo-beneficio** para elegir la opción que mejor calce con el caso (ver §7.4).
  - Materiales: plantilla Bus Matrix **2.1.3**, plantilla Diccionario de Datos para IA **2.1.5**, Notebook **2.1.4**.
- **2.2 ETL/ELT** (IL 2.3): Extract–Transform–Load; ETL si el destino es un DWH estructurado, ELT en lake/nube; extracción de CSV/JSON/BD/APIs; transformaciones = calidad de datos hecha código; **cargar dimensiones antes que hechos**; SCD al cargar; carga incremental; Pandas vs SSIS. Notebook **2.2.3** (pipeline Pandas). Buenas prácticas: idempotencia, logging, manejo de errores, validar conteos.
- **2.3 Pipelines robustos:** no tuvo notebook; solo **README plantilla 2.3.3** y **checklist de code review 2.3.4** (secciones: funcionalidad, manejo de errores, logging, idempotencia, validación, seguridad y secretos, legibilidad, documentación/versionado, veredicto; ítems bloqueantes: secretos en el código, sin manejo de errores, pipeline no idempotente). ⚠️ Lo que usa el repo como plantilla de PR es una **adaptación** de la checklist, no el texto original.
- **2.4.4 Parquet y Delta Lake:** capas Bronce/Plata/Oro (Medallion) en Pandas; Parquet pesa una fracción del CSV; Delta Lake visto de forma conceptual.

**Nuevo en la plantilla Bus Matrix 2.1.3:** agrega **Geografía como dimensión conformada propia** (7 columnas) y sugiere SCD por dimensión: Fecha = no aplica; Producto = Tipo 2; Sucursal = Tipo 1; **Geografía = Tipo 2** (re-zonificación); Canal = Tipo 1; **Cliente = Tipo 2**; Campaña = Tipo 1 (marcada "Específica", aunque aparece en 2 procesos y la fórmula de la plantilla la calificaría "Conformada" ⚠️).

**Diccionario de datos 2.1.5 (10 columnas):** Tabla · Columna · Tipo de dato · Descripción de negocio · Sinónimos · ¿Métrica? · Agregación · Jerarquía · Ejemplo · Nota para NLQ. Trae filas de ejemplo (p. ej. `fact_ventas.monto_neto` con la regla "excluir `devolucion = 1`").

---

## 4. Lo ya decidido y entregado en el EP1

**Proceso priorizado:** **Ventas omnicanal** (tiendas físicas + e-commerce): mayor impacto, articula las dimensiones conformadas y sus datos llegan con buen detalle estructurado.

**Cinco fuentes:** POS (SQL OLTP) · plataforma e-commerce (NoSQL, JSON anidado, fechas UTC/ISO) · ERP (notas de crédito, facturación) · WMS (inventario, batch desfasado) · planillas Excel/CSV de Marketing y Operaciones.

**Calidad de datos (6 dimensiones):** unicidad (dedupe por RUT validado), consistencia (tabla puente SKU/EAN, cuarentena), completitud (sucursal faltante → `id_sucursal = -1`), validez (fechas ISO-8601, montos numéricos, negativos solo en notas de crédito), oportunidad (ingesta diaria nocturna), precisión (recalcular `monto_neto = cantidad × precio − descuento`).

**Seguridad y ética:** Ley **19.628** (consentimiento, finalidad) y Ley **21.719** (Agencia de Protección de Datos, licitud, finalidad, proporcionalidad, minimización, responsabilidad demostrada, multas); tríada **CIA** (anonimización de PII + seguridad por fila, auditoría/linaje, tolerancia a fallos); IA generativa con **validación humana obligatoria** y prohibición de enviar datos transaccionales o de clientes a modelos externos.

**Arquitectura:** comparó Data Warehouse / Data Lake / Lakehouse y eligió **Data Warehouse dimensional (Kimball) sobre base Lakehouse con arquitectura Medallion** (gobernanza del DW + flexibilidad para datos no estructurados como logs de navegación; el Data Lake puro se descartó por riesgo de *Data Swamp*).

**Herramienta BI/IA:** **Power BI (+ Copilot)** — 4,70/5 contra Looker Studio + Gemini 4,00 y Vanna.ai 3,25 (pesos 15/15/15/15/15/10/10/5 sobre costo, facilidad, integración, IA/NLQ, gobernanza, escalabilidad, visualización, soporte). ⚠️ Existe además la plantilla 1.3.2 recalibrada con 5 herramientas (Power BI 4,40 · Looker 4,35 · Qlik 4,15 · Vanna 3,80 · Tableau 3,65); **el informe entregado usa la de 3 herramientas.**

**Plan Kimball (4 pasos):**
1. Proceso: Ventas omnicanal.
2. **Grano:** una fila = una línea de producto dentro de una boleta física u orden digital.
3. Dimensiones conformadas: Fecha, Producto, Sucursal, Canal, Cliente (y Campaña a futuro).
4. Hechos (`Fact_Ventas`): cantidad, monto bruto, descuento, neto, IVA (19 %), total, costo de venta, margen bruto; `ID_Transaccion_Natural` como clave degenerada.

**Bus Matrix EP1:** 5 procesos (Ventas, Inventario, Campañas, Devoluciones, Navegación web) × 6 dimensiones; Fecha y Producto en los 5.

**Catálogo de KPIs oficiales:** venta neta oficial (neto de IVA menos devoluciones) · ticket promedio · margen comercial % · cliente activo (≥1 compra en 90 días) · tasa de devolución · rotación de inventario · efectividad de campaña.

**Cronograma:** Fase 1 semanas 1–5 (planificación) · Fase 2 semanas 6–11 (modelo dimensional y ETL) · Fase 3 semanas 12–16 (capa semántica, dashboards, NLQ). **Riesgos:** resistencia cultural a las métricas, homologación de SKU, alucinaciones de IA, fuga de datos personales.

**Otros entregables ya producidos:** presentación de 10 diapositivas (la 8 es el esquema estrella), guion de exposición (.docx), diagrama del esquema estrella (XML de draw.io), matriz 1.3.2 recalibrada.

---

## 5. La evaluación actual: EP3 (informe) y EP4 (presentación)

**Qué es:** la etapa técnica del caso — diseñar el modelo dimensional, aplicar SCD, **implementar un pipeline ETL/ELT funcional** y una **arquitectura de almacenamiento analítico** con datos limpios, validados y trazables.

**Indicadores de logro:** IL 2.1 modelo dimensional (estrella/copo de nieve, hechos, dimensiones, grano, jerarquías, espaciales, capa semántica para IA) · IL 2.2 SCD 1/2/3 · IL 2.3 pipeline ETL/ELT con Python/Pandas (y/o SSIS/ADF) con **manejo de errores, logging y control de versiones** · IL 2.4 arquitectura de almacenamiento (DWH y/o Data Lake **Medallion**).

**Rúbrica — 5 indicadores de 20 % cada uno** (niveles 100/80/60/30/0 %):
1. Modelo dimensional diseñado **en Draw.io / Lucidchart** (hechos, dimensiones, grano, jerarquías, atributos).
2. SCD aplicado y **justificado** según la evolución temporal de los datos.
3. **Pipeline ETL/ELT funcional** (Python, Jupyter, Pandas, SQLAlchemy, motor de BD) con validaciones, manejo de errores y logging.
4. **Arquitectura de almacenamiento** (SQLite y/o SQL Server + SSMS) con datos limpios, validados y trazables.
5. **Documentación técnica** con evidencia verificable, control de versiones y trazabilidad.

⚠️ El texto de los indicadores 2, 4 y 5 salió desordenado al convertir el PDF; se interpretó por intención.

**Informe — 12 apartados obligatorios:** portada · introducción · modelo dimensional · aplicación de SCD y justificación · descripción del pipeline · evidencia de E/T/L · validaciones, errores y logging · arquitectura de almacenamiento · evidencia de datos limpios, validados y trazables · justificación técnica de decisiones · conclusiones · bibliografía.

**Stack permitido:** Python, Jupyter, Pandas, SQLAlchemy, SQLite y/o SQL Server + SSMS, SSIS/Azure Data Factory (si corresponde), PyArrow/fastparquet (si corresponde), Git/GitHub, VS Code, Draw.io/Lucidchart.

**Aspectos formales:** entrega digital en el formato que defina el docente, redacción formal y técnica, coherencia entre caso–modelo–pipeline–arquitectura–conclusiones, evidencias verificables y pertinentes. ⚠️ La pauta de la presentación (EP4) no se ha revisado: conseguirla del docente.

---

## 6. Organización del trabajo y repositorio

**Decisión del equipo:** 3 notebooks, cada uno con un pipeline por dimensión, más un **cuarto notebook de integración**.

| Notebook | Contenido | Responsable |
|---|---|---|
| `01_dim_geografia` | SCD2 · alimenta a Sucursal y Cliente | Cristóbal Cárdenas o Mara Cantillana (según elijan) |
| `02_dim_producto` | SCD2 · homologación de SKU | **Victor Navarrete** |
| `03_dim_cliente` | SCD2 · RUT anonimizado · datos personales · depende de 01 | La otra persona entre Cristóbal y Mara |
| `04_fact_ventas_integracion` | `dim_fecha` (ejemplo resuelto), `dim_canal`, `dim_sucursal` y `fact_ventas` | los tres (trabajo en conjunto) |

(Las dimensiones elegidas son Cliente, Producto y Geografía; el número de notebook sigue el orden de dependencia, no el de preferencia.)

**Repositorio `datarretail360-pipeline` (esqueleto entregado):** `src/` listo y probado (pruebas opcionales en `tests/`; el equipo decidió no escribir nuevas); notebooks con plantilla común donde cada integrante escribe su `transformar()` (✏️ TODO); `run_pipeline.py`; datos sintéticos; `docs/acuerdos_tecnicos.md`; plantilla de PR con checklist; README.

**Módulos de `src/`:**
| Módulo | Qué ofrece |
|---|---|
| `config.py` | Lee `.env`; constantes `FECHA_INICIO_DEFECTO = 1900-01-01`, `FECHA_FIN_VIGENTE = 9999-12-31`, `CLAVE_DESCONOCIDA = -1`; `exigir_rut_salt()` |
| `logger.py` | `get_logger`; log en consola y `logs/`; redacta RUT y correos |
| `schema.py` | Definición única de las tablas (SQLite y SQL Server), `crear_esquema`, `sembrar_miembros_desconocidos` |
| `db.py` | `get_engine`, `aplicar_scd1`, `aplicar_scd2`, `asignar_clave_scd2`, `mapa_claves`, `insertar_si_no_existe`, `registrar_rechazos`, `Ejecucion` (auditoría), `reintentar` |
| `quality.py` | `normalizar_texto/sku`, `parsear_fechas`, `rut_valido`, `anonimizar_serie`, `tramo_etario`, `separar_rechazos`, `consolidar_rechazos`, `chequear_scd2` |
| `extract.py` / `medallion.py` | `leer_csv`, `leer_json` (con `origen_archivo` y `fila_origen`); `guardar_capa`/`leer_capa` (Parquet Bronze/Silver) |

**Cómo se ejecuta:** `python run_pipeline.py` (snapshots 1 y 2 de las dimensiones, luego integración; se detiene con código 1 si falla; deja notebooks ejecutados en `logs/ejecutados/`). Motor por `.env`: **SQL Server** (decisión del equipo; la mayoría aún no lo tiene instalado) o `sqlite` para desarrollar sin instalar nada. En SQL Server hay que crear antes la base vacía `DataRetail360_DW` en SSMS.

**Flujo en Git:** una rama por tarea (`feature/dim-cliente`, …), commits pequeños, PR revisado por otro integrante con la checklist, *Restart & Run All* sin errores antes del PR; los notebooks se suben con salidas pero sin datos personales visibles.

---

## 7. Diseño técnico vigente

### 7.1 Modelo físico (esquema estrella)

| Tabla | Clave sustituta | Clave natural | SCD | Atributos |
|---|---|---|---|---|
| `dim_fecha` | `fecha_key` (AAAAMMDD) | `fecha` | — | día, mes, nombre_mes, trimestre, año, día_semana, es_fin_de_semana |
| `dim_geografia` | `geografia_key` | `codigo_comuna` (CUT) | **Tipo 2**: provincia, región, zona_comercial · Tipo 1: comuna, país, lat/long | jerarquía comuna → provincia → región → país |
| `dim_sucursal` | `sucursal_key` | `id_sucursal` | Tipo 1 | nombre, tipo_tienda, `geografia_key` |
| `dim_canal` | `canal_key` | `canal` | Tipo 1 | tipo_canal |
| `dim_producto` | `producto_key` | `sku` | **Tipo 2**: marca, categoría, subcategoría, línea · Tipo 1: nombre | jerarquía SKU → subcategoría → categoría → línea |
| `dim_cliente` | `cliente_key` | `rut_anonimizado` | **Tipo 2**: `codigo_comuna`, segmento · Tipo 1: tramo_etario, fecha_primer_registro, `geografia_key` | sin nombre, correo ni fecha de nacimiento |
| `fact_ventas` | PK `(id_transaccion, linea)` | — | — | fecha_key, producto_key, cliente_key, sucursal_key, canal_key, cantidad, monto_neto, monto_iva, monto_total, `devolucion` (0/1) |
| `auditoria_rechazos` | autonumérica | único `(proceso, origen_archivo, fila_origen, motivo)` | — | detalle sin PII |
| `auditoria_ejecuciones` | autonumérica | — | — | proceso, inicio, fin, estado OK/ERROR, filas leídas/cargadas/rechazadas, mensaje |

Cada dimensión tiene un miembro **«No informado» con clave `-1`**. Las claves sustitutas las asigna el pipeline (no IDENTITY).

### 7.2 Convenciones implementadas
- SCD2: columnas `valido_desde`, `valido_hasta` (`9999-12-31` si vigente), `es_actual`; la primera versión parte en `1900-01-01`; al cambiar, la versión anterior cierra el día anterior a la fecha efectiva (no se solapan).
- **SCD2 a prueba de reprocesos:** cada fila se compara con la versión vigente *a la fecha efectiva* del snapshot. Reprocesar snapshots antiguos no cambia nada; un dato retroactivo que contradice la historia falla con `ErrorFatal`.
- **Hechos con versión histórica:** cada venta toma la versión de producto y cliente vigente **a su fecha** (`asignar_clave_scd2`), no la actual.
- Cargas idempotentes por clave natural / `(id_transaccion, linea)`.
- Datos personales: el RUT solo existe como hash con sal (`RUT_SALT` en `.env`); nombre, correo y fecha de nacimiento no llegan al DW; logs y rechazos redactan RUT y correos.
- Medallion: Bronze = crudo en Parquet, Silver = limpio + rechazos, Gold = esquema estrella en la base.

### 7.3 Decisiones (aprobadas por el equipo el 24-10-2026; ver `docs/acuerdos_tecnicos.md`)
1. `monto_neto = monto_total / 1.19` (los archivos traen monto con IVA).
2. Devoluciones como columna `devolucion` (como el Diccionario 2.1.5) vs. tabla `Fact_Devoluciones` separada (EP1).
3. Ventas anuladas: rechazar vs. cargar marcadas.
4. Sucursal faltante: clave `-1` (EP1) vs. texto `SIN_ASIGNAR` (notebook de clase).
5. Venta sin RUT: cliente `-1` vs. rechazar.
6. Deduplicar ventas por `(id_transaccion, linea)` (en clase se usaba fecha + sku + sucursal + canal, que descarta ventas legítimas).
7. SCD por dimensión (según plantilla 2.1.3) y evaluar Tipo 3 donde convenga.
8. `geografia_key` en `dim_cliente` como atributo SCD1 vs. dentro del SCD2.
9. Bronce con RUT crudo (carpeta `data/` no versionada) vs. anonimizar antes de Bronce.
10. SQL Server como principal y SQLite para reproducir sin instalar nada.

### 7.4 Análisis costo-beneficio de SCD (requerido por el docente)
- **Cliente → Tipo 2.** El problema central del caso es perder trazabilidad de cifras históricas: con Tipo 1 o 3, si un cliente cambia de región varias veces, las ventas pasadas se reasignan o se pierde todo salvo el último cambio. Además la Ley 21.719 pide trazabilidad demostrable y los KPIs (venta por región, cliente activo) pierden sentido retrospectivo.
- **Costo del Tipo 2:** más filas, ETL más complejo (fechas de vigencia, bandera actual), capa semántica más delicada (la IA debe filtrar `es_actual = 1`). Con el volumen de clientes y la baja frecuencia esperada de cambios de comuna, el costo es acotado.
- **Dónde el Tipo 3 podría bastar:** atributos que cambian poco y donde solo importa "antes vs. ahora". Candidatos a evaluar: `linea_negocio` de producto o `zona_comercial`. Documentar la comparación en cada notebook (sección 7 «Decisiones de diseño»).

### 7.5 Hallazgos sobre los notebooks de clase (para no repetir los errores)
- `monto_neto` estaba definido de **tres formas** distintas (2.2.3: monto o 0 si devuelta; 2.4.4: monto/1,19; EP1: bruto − descuento sin IVA).
- El SCD2 del 2.2.3 cruzaba los hechos con la versión **actual** del producto y ponía `fecha_inicio` = fecha de ejecución: se pierde el sentido del SCD2.
- El pipeline cargaba solo fecha, producto y sucursal (faltaban Canal y Cliente) y no tenía `dim_geografia`.
- Sin `logging` ni `try/except`; celdas duplicadas y variables heredadas (`con`) que rompen *Run All*.
- El 2.4.4 no persistía plata/oro ni conectaba con el DW.

---

## 8. Datos de ejemplo (sintéticos, `data/sample/`)

| Archivo | Contenido y problemas plantados |
|---|---|
| `geografia_snapshot_1/2.csv` | 14 comunas (códigos CUT); `codigo_comuna` repetido, coordenadas imposibles; snapshot 2: Chillán cambia de zona comercial (Centro → Sur) |
| `sucursales.csv` | 7 sucursales (S00 = centro de distribución online) |
| `productos_snapshot_1/2.csv` | 10 productos; SKU con minúsculas/espacios, duplicado con SKU distinto, fila sin SKU; snapshot 2: AU-002 pasa de Accesorios a Audio, CL-006 cambia de línea, aparece MN-010 |
| `clientes_snapshot_1/2.csv` | 24 clientes base; 2 RUT inválidos, 2 duplicados por RUT, comuna vacía y comuna inexistente; snapshot 2: 3 cambios de comuna, 2 de segmento, 2 clientes nuevos |
| `ventas_pos.csv` | 85 filas; fechas en 3 formatos y una imposible, líneas duplicadas, 2 montos negativos, anuladas y devueltas, SKU inexistente, sucursal vacía, venta sin cliente |
| `ventas_ecommerce.json` | 13 órdenes con `items` anidados; fechas UTC, una orden repetida (EC-1002), anuladas/devueltas, canal escrito de 3 formas |

**Conteos de control orientativos** (con las reglas sugeridas en los notebooks): rechazos snapshot 1 → geografía 2, producto 2, cliente 4; ventas: 111 leídas = 101 cargadas + 10 rechazadas. Varían si el equipo decide distinto en la §7.3.

---

## 9. Mapa rúbrica EP3 ↔ qué falta

| Indicador | Ya hay | Falta |
|---|---|---|
| 1. Modelo dimensional (Draw.io) | Estrella EP1 (Fact_Ventas + 5 dimensiones) y XML de draw.io | Actualizarlo con `dim_geografia`, jerarquías, atributos, SCD; completar Diccionario 2.1.5 |
| 2. SCD justificado | Análisis costo-beneficio de Cliente; plantilla 2.1.3 | Justificar Producto y Geografía; evaluar Tipo 3 |
| 3. Pipeline funcional | `src/` + notebooks cableados + runner | `transformar()` de 01–03 y reglas/claves de 04 |
| 4. Almacenamiento | Esquema, Medallion, auditoría | Cargar con reglas reales, correr en SQL Server, capturar evidencia |
| 5. Documentación | README, acuerdos, plantilla de PR, repo | Historial de commits/PR, informe de 12 apartados, evidencias |

**Orden sugerido:** (1) decisiones de §7.3 ya aprobadas · (2) crear el repo, asignar notebooks y crear ramas · (3) implementar `transformar()` · (4) correr `run_pipeline.py` y revisar validaciones · (5) probar en SQL Server/SSMS · (6) completar diccionario y diagrama · (7) redactar informe y presentación con las evidencias de `logs/ejecutados/`.

---

## 10. Pendientes y supuestos no verificados

- ⚠️ El pipeline se probó solo con **SQLite**; el DDL de SQL Server está generado pero **no se ejecutó** en SQL Server real.
- ⚠️ Falta confirmar qué dimensión toma cada una entre Cristóbal y Mara; formato de entrega y pauta de la presentación (EP4) por confirmar con el docente.
- ⚠️ **SQL Server** pendiente de instalar en la mayoría de las máquinas; el repositorio de GitHub se llamará **DataRetail360-Pipeline** (lo crea Victor).
- ⚠️ La checklist de PR es una adaptación; contrastar con la 2.3.4 original. Los datos oficiales del curso (CSV/JSON) no se han usado: los de ejemplo son sintéticos.
- No se ha trabajado aún la capa semántica/diccionario completo ni los dashboards (Experiencia 3).

---

## Glosario rápido

**Grano:** qué representa una fila de la tabla de hechos · **Dimensión conformada:** dimensión compartida por varios procesos · **Clave sustituta:** identificador propio del DW · **SCD:** dimensión de cambio lento · **Idempotente:** ejecutar dos veces no duplica · **Medallion:** capas Bronce (crudo) → Plata (limpio) → Oro (modelado) · **Bus Matrix:** matriz proceso × dimensión · **NLQ:** consulta en lenguaje natural · **Miembro «No informado»:** fila de clave −1 para datos faltantes.
