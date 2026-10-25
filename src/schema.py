"""Esquema del Data Warehouse DataRetail 360 (esquema estrella).

Es la ÚNICA definición de las tablas: sirve para SQLite y SQL Server.
Para obtener el DDL de SQL Server (y abrirlo en SSMS):

    python scripts/exportar_schema_sql.py

Convenciones (ver docs/acuerdos_tecnicos.md):
- Claves sustitutas (`*_key`) asignadas por el pipeline (no IDENTITY), para poder
  insertar el miembro desconocido con clave -1.
- Dimensiones SCD Tipo 2: `valido_desde`, `valido_hasta` (9999-12-31 si vigente), `es_actual`.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Column, Date, DateTime, Float, ForeignKey, Index, Integer, MetaData,
    Numeric, String, Table, UniqueConstraint, func, insert, select,
)
from sqlalchemy.engine import Engine

from .config import CLAVE_DESCONOCIDA, FECHA_FIN_VIGENTE, FECHA_INICIO_DEFECTO

metadata = MetaData()


def _pk(nombre: str) -> Column:
    return Column(nombre, Integer, primary_key=True, autoincrement=False)


def _columnas_scd2() -> list[Column]:
    return [
        Column("valido_desde", Date, nullable=False),
        Column("valido_hasta", Date, nullable=False),
        Column("es_actual", Integer, nullable=False),
    ]


# --------------------------------------------------------------------- Dimensiones
dim_fecha = Table(
    "dim_fecha", metadata,
    Column("fecha_key", Integer, primary_key=True, autoincrement=False),  # AAAAMMDD
    Column("fecha", Date, nullable=False, unique=True),
    Column("dia", Integer), Column("mes", Integer), Column("nombre_mes", String(20)),
    Column("trimestre", Integer), Column("anio", Integer),
    Column("dia_semana", String(15)), Column("es_fin_de_semana", Integer),
)

dim_geografia = Table(
    "dim_geografia", metadata,
    _pk("geografia_key"),
    Column("codigo_comuna", String(10), nullable=False),     # clave natural (código CUT)
    Column("comuna", String(80)), Column("provincia", String(80)),
    Column("region", String(80)), Column("pais", String(40)),
    Column("zona_comercial", String(30)),
    Column("latitud", Float), Column("longitud", Float),
    *_columnas_scd2(),
    UniqueConstraint("codigo_comuna", "valido_desde", name="uq_geografia_version"),
)
Index("ix_geografia_actual", dim_geografia.c.codigo_comuna, dim_geografia.c.es_actual)

dim_sucursal = Table(
    "dim_sucursal", metadata,
    _pk("sucursal_key"),
    Column("id_sucursal", String(10), nullable=False, unique=True),  # clave natural
    Column("nombre_sucursal", String(100)), Column("tipo_tienda", String(40)),
    Column("geografia_key", Integer, ForeignKey("dim_geografia.geografia_key")),
)

dim_canal = Table(
    "dim_canal", metadata,
    _pk("canal_key"),
    Column("canal", String(40), nullable=False, unique=True),         # clave natural
    Column("tipo_canal", String(20)),
)

dim_producto = Table(
    "dim_producto", metadata,
    _pk("producto_key"),
    Column("sku", String(30), nullable=False),                        # clave natural
    Column("nombre_producto", String(150)), Column("marca", String(60)),
    Column("categoria", String(60)), Column("subcategoria", String(60)),
    Column("linea_negocio", String(60)),
    *_columnas_scd2(),
    UniqueConstraint("sku", "valido_desde", name="uq_producto_version"),
)
Index("ix_producto_actual", dim_producto.c.sku, dim_producto.c.es_actual)

dim_cliente = Table(
    "dim_cliente", metadata,
    _pk("cliente_key"),
    Column("rut_anonimizado", String(64), nullable=False),            # clave natural (hash, sin PII)
    Column("tramo_etario", String(20)), Column("segmento", String(30)),
    Column("codigo_comuna", String(10)),
    Column("geografia_key", Integer, ForeignKey("dim_geografia.geografia_key")),
    Column("fecha_primer_registro", Date),
    *_columnas_scd2(),
    UniqueConstraint("rut_anonimizado", "valido_desde", name="uq_cliente_version"),
)
Index("ix_cliente_actual", dim_cliente.c.rut_anonimizado, dim_cliente.c.es_actual)

# --------------------------------------------------------------------------- Hechos
fact_ventas = Table(
    "fact_ventas", metadata,
    Column("id_transaccion", String(40), primary_key=True, autoincrement=False),  # clave degenerada
    Column("linea", Integer, primary_key=True, autoincrement=False),
    Column("fecha_key", Integer, ForeignKey("dim_fecha.fecha_key"), nullable=False),
    Column("producto_key", Integer, ForeignKey("dim_producto.producto_key"), nullable=False),
    Column("cliente_key", Integer, ForeignKey("dim_cliente.cliente_key"), nullable=False),
    Column("sucursal_key", Integer, ForeignKey("dim_sucursal.sucursal_key"), nullable=False),
    Column("canal_key", Integer, ForeignKey("dim_canal.canal_key"), nullable=False),
    Column("cantidad", Integer),
    Column("monto_neto", Numeric(14, 2, asdecimal=False)),   # sin IVA
    Column("monto_iva", Numeric(14, 2, asdecimal=False)),
    Column("monto_total", Numeric(14, 2, asdecimal=False)),  # con IVA
    Column("devolucion", Integer, nullable=False),           # 0 = venta, 1 = devolución
)

# ------------------------------------------------------------------------ Auditoría
auditoria_rechazos = Table(
    "auditoria_rechazos", metadata,
    Column("rechazo_id", Integer, primary_key=True, autoincrement=True),
    Column("proceso", String(50), nullable=False),
    Column("origen_archivo", String(150), nullable=False),
    Column("fila_origen", Integer, nullable=False),
    Column("motivo_rechazo", String(100), nullable=False),
    Column("detalle", String(250)),
    Column("registrado_en", DateTime, nullable=False),
    UniqueConstraint("proceso", "origen_archivo", "fila_origen", "motivo_rechazo",
                     name="uq_rechazo"),
)

auditoria_ejecuciones = Table(
    "auditoria_ejecuciones", metadata,
    Column("ejecucion_id", Integer, primary_key=True, autoincrement=True),
    Column("proceso", String(50), nullable=False),
    Column("inicio", DateTime, nullable=False),
    Column("fin", DateTime),
    Column("estado", String(15), nullable=False),            # OK | ERROR
    Column("filas_leidas", Integer), Column("filas_cargadas", Integer),
    Column("filas_rechazadas", Integer),
    Column("mensaje", String(500)),
)

# ------------------------------------------------- Miembro "No informado" (clave -1)
_NI = "NO INFORMADO"
_VIGENCIA = {
    "valido_desde": FECHA_INICIO_DEFECTO,
    "valido_hasta": FECHA_FIN_VIGENTE,
    "es_actual": 1,
}
MIEMBROS_DESCONOCIDOS: dict[str, dict] = {
    "dim_geografia": {
        "geografia_key": CLAVE_DESCONOCIDA, "codigo_comuna": "-1", "comuna": _NI,
        "provincia": _NI, "region": _NI, "pais": _NI, "zona_comercial": _NI,
        "latitud": None, "longitud": None, **_VIGENCIA,
    },
    "dim_sucursal": {
        "sucursal_key": CLAVE_DESCONOCIDA, "id_sucursal": "-1",
        "nombre_sucursal": "SUCURSAL NO INFORMADA", "tipo_tienda": _NI,
        "geografia_key": CLAVE_DESCONOCIDA,
    },
    "dim_canal": {"canal_key": CLAVE_DESCONOCIDA, "canal": _NI, "tipo_canal": _NI},
    "dim_producto": {
        "producto_key": CLAVE_DESCONOCIDA, "sku": "-1", "nombre_producto": "PRODUCTO NO INFORMADO",
        "marca": _NI, "categoria": _NI, "subcategoria": _NI, "linea_negocio": _NI, **_VIGENCIA,
    },
    "dim_cliente": {
        "cliente_key": CLAVE_DESCONOCIDA, "rut_anonimizado": "-1", "tramo_etario": _NI,
        "segmento": _NI, "codigo_comuna": "-1", "geografia_key": CLAVE_DESCONOCIDA,
        "fecha_primer_registro": None, **_VIGENCIA,
    },
}
# Orden respetando las claves foráneas
ORDEN_CREACION = ["dim_geografia", "dim_sucursal", "dim_canal", "dim_producto", "dim_cliente"]


def crear_esquema(engine: Engine) -> None:
    """Crea las tablas que falten. Idempotente."""
    metadata.create_all(engine, checkfirst=True)


def eliminar_esquema(engine: Engine) -> None:
    """Borra todas las tablas (solo para desarrollo y pruebas)."""
    metadata.drop_all(engine)


def sembrar_miembros_desconocidos(engine: Engine) -> int:
    """Inserta la fila de clave -1 en cada dimensión si no existe. Retorna cuántas insertó."""
    insertadas = 0
    with engine.begin() as conn:
        for nombre in ORDEN_CREACION:
            tabla = metadata.tables[nombre]
            clave = list(tabla.primary_key.columns)[0]
            existe = conn.execute(
                select(func.count()).select_from(tabla).where(clave == CLAVE_DESCONOCIDA)
            ).scalar()
            if not existe:
                conn.execute(insert(tabla).values(**MIEMBROS_DESCONOCIDOS[nombre]))
                insertadas += 1
    return insertadas
