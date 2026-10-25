"""Acceso a la base de datos y patrones de carga reutilizables.

Funciona con SQLite (desarrollo / evaluación) y SQL Server (SSMS). Contiene:

- `get_engine`           conexión desde `.env`, con reintentos.
- `aplicar_scd1`         dimensión Tipo 1 (sobrescribe), idempotente.
- `aplicar_scd2`         dimensión Tipo 2 (versiona), idempotente.
- `asignar_clave_scd2`   busca la versión de la dimensión vigente A LA FECHA del hecho.
- `insertar_si_no_existe` carga idempotente (hechos y tablas de auditoría).
- `registrar_rechazos`   deja las filas inválidas con su motivo.
- `Ejecucion`            contexto que registra inicio/fin/estado/conteos de cada proceso.
"""
from __future__ import annotations

import functools
import time
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import Date, DateTime, Float, Integer, Numeric, String, create_engine, event, func, select, text, update
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import InterfaceError, OperationalError

from . import schema
from .config import CLAVE_DESCONOCIDA, FECHA_FIN_VIGENTE, FECHA_INICIO_DEFECTO, Settings, get_settings
from .errores import ErrorFatal
from .logger import get_logger, redactar_pii

log = get_logger("db")


# ------------------------------------------------------------------------- Conexión
def reintentar(intentos: int = 3, espera: float = 2.0,
               excepciones: tuple = (OperationalError, InterfaceError)):
    """Reintenta una función ante errores transitorios; si se agotan, lanza ErrorFatal."""
    def decorador(fn):
        @functools.wraps(fn)
        def envoltura(*args, **kwargs):
            for intento in range(1, intentos + 1):
                try:
                    return fn(*args, **kwargs)
                except excepciones as exc:
                    if intento == intentos:
                        log.error("%s falló tras %s intentos (%s)", fn.__name__, intentos, type(exc).__name__)
                        raise ErrorFatal(f"{fn.__name__} falló tras {intentos} intentos") from exc
                    log.warning("Intento %s/%s de %s falló (%s). Reintentando…",
                                intento, intentos, fn.__name__, type(exc).__name__)
                    time.sleep(espera * intento)
        return envoltura
    return decorador


def construir_url(s: Settings) -> URL | str:
    if s.db_engine == "sqlite":
        return f"sqlite:///{s.sqlite_path}"
    if s.db_engine == "sqlserver":
        consulta = {"driver": s.db_driver, "TrustServerCertificate": "yes"}
        if s.db_trusted:
            consulta["trusted_connection"] = "yes"
        return URL.create("mssql+pyodbc", username=None if s.db_trusted else s.db_user,
                          password=None if s.db_trusted else s.db_password,
                          host=s.db_host, database=s.db_name, query=consulta)
    raise ErrorFatal(f"DB_ENGINE inválido: '{s.db_engine}' (usa 'sqlite' o 'sqlserver')")


@reintentar()
def verificar_conexion(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def get_engine(settings: Settings | None = None) -> Engine:
    """Crea el engine según `.env` y verifica que la base responda."""
    s = settings or get_settings()
    url = construir_url(s)
    if s.db_engine == "sqlite":
        s.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url)

        @event.listens_for(engine, "connect")
        def _activar_fk(conexion, _):
            conexion.execute("PRAGMA foreign_keys=ON")
    else:
        engine = create_engine(url, fast_executemany=True)
    verificar_conexion(engine)
    log.info("Conectado a %s (%s)", s.db_engine, s.db_name if s.db_engine == "sqlserver" else s.sqlite_path.name)
    return engine


# --------------------------------------------------------------------- Conversiones

def _a_ordinal(valor) -> float:
    """Fecha -> número ordinal (sirve incluso para 9999-12-31, que datetime64[ns] no soporta)."""
    try:
        if valor is None or pd.isna(valor):
            return np.nan
    except (TypeError, ValueError):
        pass
    if isinstance(valor, date):          # incluye datetime y pd.Timestamp
        return float(valor.toordinal())
    return float(date.fromisoformat(str(valor)[:10]).toordinal())


def _tabla(tabla):
    return schema.metadata.tables[tabla] if isinstance(tabla, str) else tabla


def _norm(valor):
    """Valor comparable: None/NaN -> None, números -> float, fechas -> date, texto sin espacios."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(valor, pd.Timestamp):
        return valor.date()
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, str):
        return valor.strip()
    if isinstance(valor, (int, float, np.integer, np.floating)) and not isinstance(valor, bool):
        return float(valor)
    return valor


def _convertir(valor, tipo):
    """Convierte un valor de pandas/numpy al tipo nativo de Python que espera la columna."""
    try:
        if valor is None or pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(tipo, DateTime):
        return pd.Timestamp(valor).to_pydatetime()
    if isinstance(tipo, Date):
        return pd.Timestamp(valor).date()
    if isinstance(tipo, Integer):
        return int(valor)
    if isinstance(tipo, (Float, Numeric)):
        return float(valor)
    if isinstance(tipo, String):
        return str(valor)
    return valor


def _registros(df: pd.DataFrame, tabla) -> list[dict]:
    tabla = _tabla(tabla)
    columnas = [c for c in df.columns if c in tabla.c]
    return [
        {k: _convertir(v, tabla.c[k].type) for k, v in fila.items()}
        for fila in df[columnas].to_dict("records")
    ]


def leer_tabla(engine: Engine, tabla, solo_vigentes: bool = False) -> pd.DataFrame:
    """Lee una tabla completa (o solo `es_actual = 1`) como DataFrame."""
    tabla = _tabla(tabla)
    consulta = select(tabla)
    if solo_vigentes:
        consulta = consulta.where(tabla.c.es_actual == 1)
    with engine.connect() as conn:
        return pd.read_sql(consulta, conn)


def _siguiente_key(conn, tabla, key_col: str) -> int:
    maximo = conn.execute(select(func.max(tabla.c[key_col]))).scalar()
    return 1 if maximo is None or maximo < 1 else int(maximo) + 1


def _chequear_df(df: pd.DataFrame, clave_natural: str, columnas: list[str]) -> None:
    faltan = [c for c in [clave_natural, *columnas] if c not in df.columns]
    if faltan:
        raise ErrorFatal(f"Al DataFrame le faltan columnas: {faltan}")
    if df[clave_natural].isna().any():
        raise ErrorFatal(f"'{clave_natural}' tiene nulos: límpialos o recházalos antes de cargar")
    if df[clave_natural].duplicated().any():
        raise ErrorFatal(f"'{clave_natural}' tiene duplicados: deduplica antes de cargar")


def _cambia(fila, atributos: list[str], sufijo: str = "__db") -> bool:
    return any(_norm(fila[a]) != _norm(fila[a + sufijo]) for a in atributos)


# ------------------------------------------------------------------ SCD Tipo 1 y 2
def aplicar_scd1(engine: Engine, tabla, df: pd.DataFrame, clave_natural: str,
                 atributos: list[str], key_col: str) -> dict:
    """Dimensión Tipo 1: inserta lo nuevo y sobrescribe lo que cambió (sin historia).

    `df` debe tener UNA fila por `clave_natural`. Re-ejecutar con los mismos datos no
    cambia nada. Retorna {"nuevos", "actualizados", "sin_cambio"}.
    """
    tabla = _tabla(tabla)
    _chequear_df(df, clave_natural, atributos)
    df = df[[clave_natural, *atributos]].reset_index(drop=True)

    with engine.begin() as conn:
        actuales = pd.read_sql(select(tabla.c[key_col], tabla.c[clave_natural],
                                      *[tabla.c[a] for a in atributos])
                               .where(tabla.c[key_col] != CLAVE_DESCONOCIDA), conn)
        cruce = df.merge(actuales, on=clave_natural, how="left", suffixes=("", "__db"))
        es_nuevo = cruce[key_col].isna()

        nuevos = cruce.loc[es_nuevo, [clave_natural, *atributos]].copy()
        existentes = cruce.loc[~es_nuevo]
        cambiados = existentes[existentes.apply(lambda f: _cambia(f, atributos), axis=1)] if len(existentes) else existentes

        for _, fila in cambiados.iterrows():
            valores = {a: _convertir(fila[a], tabla.c[a].type) for a in atributos}
            conn.execute(update(tabla).where(tabla.c[key_col] == int(fila[key_col])).values(**valores))

        if len(nuevos):
            nuevos[key_col] = range(_siguiente_key(conn, tabla, key_col),
                                    _siguiente_key(conn, tabla, key_col) + len(nuevos))
            conn.execute(tabla.insert(), _registros(nuevos, tabla))

    resumen = {"nuevos": int(len(nuevos)), "actualizados": int(len(cambiados)),
               "sin_cambio": int(len(existentes) - len(cambiados))}
    log.info("SCD1 %s: %s", tabla.name, resumen)
    return resumen


def aplicar_scd2(engine: Engine, tabla, df: pd.DataFrame, clave_natural: str,
                 atributos_scd2: list[str], fecha_efectiva: date, key_col: str,
                 atributos_scd1: list[str] | None = None) -> dict:
    """Dimensión Tipo 2: conserva la historia versionando las filas.

    Cada fila de `df` se compara con la versión de la dimensión que estaba VIGENTE EN
    `fecha_efectiva` (no solo con la actual). Eso hace al proceso idempotente incluso si
    se re-ejecutan snapshots antiguos en cualquier orden.

    Reglas:
      * Clave nueva: si la tabla estaba vacía (primera carga) la versión parte en
        `FECHA_INICIO_DEFECTO`; si no, parte en `fecha_efectiva`.
      * Vigente y cambió un atributo SCD2: se cierra la versión (`valido_hasta` =
        `fecha_efectiva` − 1 día, `es_actual` = 0) y se inserta una versión nueva.
      * Vigente y cambió solo un atributo SCD1: se sobrescribe en la versión vigente.
      * Coincide con una versión histórica: no se hace nada (re-ejecución de un snapshot
        antiguo). Si DIFIERE de la historia, se lanza ErrorFatal: no se reescribe el pasado.
      * Sin cambios: no se hace nada.

    `df` debe tener UNA fila por `clave_natural`.
    Retorna {"nuevos", "versiones_nuevas", "actualizados_scd1", "sin_cambio", "omitidos"}.
    """
    tabla = _tabla(tabla)
    atributos_scd1 = atributos_scd1 or []
    todos = [*atributos_scd2, *atributos_scd1]
    _chequear_df(df, clave_natural, todos)
    df = df[[clave_natural, *todos]].reset_index(drop=True)
    fecha_efectiva = pd.Timestamp(fecha_efectiva).date()
    ordinal_efectiva = float(fecha_efectiva.toordinal())

    with engine.begin() as conn:
        primera_carga = conn.execute(
            select(func.count()).select_from(tabla).where(tabla.c[key_col] != CLAVE_DESCONOCIDA)
        ).scalar() == 0
        versiones = pd.read_sql(
            select(tabla.c[key_col], tabla.c[clave_natural], tabla.c.valido_desde,
                   tabla.c.valido_hasta, tabla.c.es_actual, *[tabla.c[a] for a in todos])
            .where(tabla.c[key_col] != CLAVE_DESCONOCIDA), conn)
        desde = versiones["valido_desde"].map(_a_ordinal)
        hasta = versiones["valido_hasta"].map(_a_ordinal)
        validas = versiones[(desde <= ordinal_efectiva) & (ordinal_efectiva <= hasta)]
        conocidas = set(versiones[clave_natural])

        cruce = df.merge(validas, on=clave_natural, how="left", suffixes=("", "__db"))
        sin_version = cruce[key_col].isna()
        es_nuevo = sin_version & ~cruce[clave_natural].isin(conocidas)
        omitidos = int((sin_version & ~es_nuevo).sum())   # clave conocida pero sin versión a esa fecha
        nuevos = cruce.loc[es_nuevo, [clave_natural, *todos]].copy()
        existentes = cruce.loc[~sin_version]
        historicas = existentes[existentes["es_actual"] == 0]
        actuales = existentes[existentes["es_actual"] == 1]

        # Un snapshot antiguo que contradice la historia no se puede cargar.
        if len(historicas):
            difiere = historicas.apply(lambda f: _cambia(f, atributos_scd2), axis=1)
            if difiere.any():
                raise ErrorFatal(
                    f"{tabla.name}: {int(difiere.sum())} registros con fecha efectiva {fecha_efectiva} "
                    "difieren de la versión histórica correspondiente; no se reescribe el historial.")

        if len(actuales):
            cambia2 = actuales.apply(lambda f: _cambia(f, atributos_scd2), axis=1)
            cambia1 = (actuales.apply(lambda f: _cambia(f, atributos_scd1), axis=1) & ~cambia2
                       if atributos_scd1 else pd.Series(False, index=actuales.index))
            nueva_version, solo_scd1 = actuales[cambia2], actuales[cambia1]
        else:
            nueva_version = solo_scd1 = actuales

        # 1) cerrar versiones que cambiaron
        for _, fila in nueva_version.iterrows():
            inicio_version = _norm(fila["valido_desde"])
            if fecha_efectiva <= inicio_version and inicio_version != FECHA_INICIO_DEFECTO:
                raise ErrorFatal(
                    f"{tabla.name}: la fecha efectiva {fecha_efectiva} no es posterior al inicio de la "
                    f"versión vigente ({inicio_version}); los datos cambiaron sin avanzar la fecha.")
            conn.execute(update(tabla).where(tabla.c[key_col] == int(fila[key_col])).values(
                valido_hasta=fecha_efectiva - timedelta(days=1), es_actual=0))

        # 2) sobrescribir atributos SCD1 de la versión vigente
        for _, fila in solo_scd1.iterrows():
            valores = {a: _convertir(fila[a], tabla.c[a].type) for a in atributos_scd1}
            conn.execute(update(tabla).where(tabla.c[key_col] == int(fila[key_col])).values(**valores))

        # 3) insertar claves nuevas y versiones nuevas
        a_insertar = pd.concat([
            nuevos.assign(valido_desde=FECHA_INICIO_DEFECTO if primera_carga else fecha_efectiva),
            nueva_version[[clave_natural, *todos]].assign(valido_desde=fecha_efectiva),
        ], ignore_index=True)
        if len(a_insertar):
            inicio = _siguiente_key(conn, tabla, key_col)
            a_insertar[key_col] = range(inicio, inicio + len(a_insertar))
            a_insertar["valido_hasta"] = FECHA_FIN_VIGENTE
            a_insertar["es_actual"] = 1
            conn.execute(tabla.insert(), _registros(a_insertar, tabla))

    resumen = {
        "nuevos": int(len(nuevos)),
        "versiones_nuevas": int(len(nueva_version)),
        "actualizados_scd1": int(len(solo_scd1)),
        "sin_cambio": int(len(existentes) - len(nueva_version) - len(solo_scd1)),
        "omitidos": omitidos,
    }
    log.info("SCD2 %s (efectiva %s): %s", tabla.name, fecha_efectiva, resumen)
    return resumen


def asignar_clave_scd2(hechos: pd.DataFrame, dim: pd.DataFrame, clave_natural: str,
                       col_fecha: str, key_col: str, clave_hechos: str | None = None,
                       valor_desconocido: int = CLAVE_DESCONOCIDA) -> pd.Series:
    """Clave sustituta de la versión de la dimensión VIGENTE A LA FECHA de cada hecho.

    Esto es lo que hace útil al SCD2: una venta de marzo queda asociada a la categoría
    que el producto tenía en marzo, no a la que tiene hoy. Si no hay versión válida
    (clave inexistente o fecha fuera de vigencia) retorna `valor_desconocido`.

    Parámetros:
      hechos        DataFrame de hechos (debe traer la clave natural y la fecha).
      dim           la dimensión COMPLETA, todas las versiones (`leer_tabla(engine, "dim_x")`).
      clave_natural nombre de la clave natural EN LA DIMENSIÓN (ej. "rut_anonimizado").
      clave_hechos  nombre de esa misma clave en `hechos`, si se llama distinto (ej. "rut_anon").
      col_fecha     columna de `hechos` con la fecha del hecho.
      key_col       clave sustituta de la dimensión (ej. "cliente_key").
    Retorna una Serie alineada con `hechos`.
    """
    nat_hechos = clave_hechos or clave_natural
    h = hechos[[nat_hechos, col_fecha]].copy()
    h["_fecha"] = h[col_fecha].map(_a_ordinal)
    h["_idx"] = h.index
    h = h[h["_fecha"].notna() & h[nat_hechos].notna()].sort_values("_fecha")

    d = dim[[clave_natural, key_col, "valido_desde", "valido_hasta"]].copy()
    d["valido_desde"] = d["valido_desde"].map(_a_ordinal)
    d["valido_hasta"] = d["valido_hasta"].map(_a_ordinal)
    d = d.sort_values("valido_desde")

    if h.empty or d.empty:
        return pd.Series(valor_desconocido, index=hechos.index, dtype="int64")

    h[nat_hechos] = h[nat_hechos].astype("object")
    d[clave_natural] = d[clave_natural].astype("object")
    m = pd.merge_asof(h, d, left_on="_fecha", right_on="valido_desde",
                      left_by=nat_hechos, right_by=clave_natural, direction="backward")
    vigente = m["_fecha"] <= m["valido_hasta"]
    m[key_col] = m[key_col].where(vigente)
    resultado = m.set_index("_idx")[key_col]
    resultado = resultado[~resultado.index.duplicated(keep="first")]
    return resultado.reindex(hechos.index).fillna(valor_desconocido).astype("int64")


def mapa_claves(engine: Engine, tabla, clave_natural: str, key_col: str) -> dict:
    """Diccionario clave natural -> clave sustituta para dimensiones Tipo 1 (o versión vigente)."""
    tabla = _tabla(tabla)
    consulta = select(tabla.c[clave_natural], tabla.c[key_col])
    if "es_actual" in tabla.c:
        consulta = consulta.where(tabla.c.es_actual == 1)
    with engine.connect() as conn:
        return dict(conn.execute(consulta).all())


# ------------------------------------------------------------- Carga idempotente
def insertar_si_no_existe(engine: Engine, tabla, df: pd.DataFrame, columnas_unicas: list[str],
                          lote: int = 1000) -> dict:
    """Inserta solo las filas cuya combinación `columnas_unicas` no existe aún.

    Es la base de las cargas idempotentes: ejecutarla dos veces no duplica datos.
    Retorna {"insertadas", "ya_existian", "duplicadas_en_lote"}.
    """
    tabla = _tabla(tabla)
    faltan = [c for c in columnas_unicas if c not in df.columns]
    if faltan:
        raise ErrorFatal(f"Faltan columnas únicas en el DataFrame: {faltan}")

    sin_dup = df.drop_duplicates(subset=columnas_unicas, keep="first")
    duplicadas = len(df) - len(sin_dup)
    if sin_dup.empty:
        return {"insertadas": 0, "ya_existian": 0, "duplicadas_en_lote": int(duplicadas)}

    with engine.begin() as conn:
        existentes = pd.read_sql(select(*[tabla.c[c] for c in columnas_unicas]), conn)
        if len(existentes):
            for c in columnas_unicas:      # mismo tipo para poder comparar
                existentes[c] = existentes[c].astype(str)
            clave_nueva = sin_dup[columnas_unicas].astype(str).apply(tuple, axis=1)
            clave_exist = set(existentes.apply(tuple, axis=1))
            nuevas = sin_dup[~clave_nueva.isin(clave_exist)]
        else:
            nuevas = sin_dup

        registros = _registros(nuevas, tabla)
        for i in range(0, len(registros), lote):
            conn.execute(tabla.insert(), registros[i:i + lote])

    resumen = {"insertadas": int(len(nuevas)), "ya_existian": int(len(sin_dup) - len(nuevas)),
               "duplicadas_en_lote": int(duplicadas)}
    log.info("Carga %s: %s", tabla.name, resumen)
    return resumen


def registrar_rechazos(engine: Engine, proceso: str, rechazos: pd.DataFrame) -> dict:
    """Guarda las filas rechazadas (sin datos personales) en `auditoria_rechazos`. Idempotente."""
    if rechazos is None or rechazos.empty:
        return {"insertadas": 0, "ya_existian": 0, "duplicadas_en_lote": 0}
    r = rechazos.copy()
    r["proceso"] = proceso
    r["registrado_en"] = datetime.now()
    r["detalle"] = r["detalle"].map(lambda t: redactar_pii(str(t))[:250] if pd.notna(t) else None)
    r["fila_origen"] = r["fila_origen"].astype(int)
    columnas = ["proceso", "origen_archivo", "fila_origen", "motivo_rechazo"]
    resumen = insertar_si_no_existe(engine, schema.auditoria_rechazos, r, columnas)
    log.warning("[%s] %s filas rechazadas (nuevas en auditoría: %s)", proceso, len(r), resumen["insertadas"])
    return resumen


# ------------------------------------------------------------------- Ejecuciones
class Ejecucion:
    """Contexto que deja trazabilidad de cada proceso del pipeline.

        with Ejecucion(engine, "dim_cliente") as run:
            run.leidas = len(df_crudo)
            ...
            run.cargadas = resumen["nuevos"]
            run.rechazadas = len(rechazos)

    Registra INICIO/FIN en el log y una fila en `auditoria_ejecuciones` (OK o ERROR).
    Si ocurre una excepción la registra y la vuelve a lanzar: nunca falla en silencio.
    """

    def __init__(self, engine: Engine, proceso: str):
        self.engine, self.proceso = engine, proceso
        self.leidas = self.cargadas = self.rechazadas = 0

    def __enter__(self) -> "Ejecucion":
        self.inicio = datetime.now()
        log.info("[%s] INICIO", self.proceso)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        fin = datetime.now()
        segundos = (fin - self.inicio).total_seconds()
        if exc_type is None:
            estado, mensaje = "OK", None
            log.info("[%s] FIN OK leidas=%s cargadas=%s rechazadas=%s (%.1fs)",
                     self.proceso, self.leidas, self.cargadas, self.rechazadas, segundos)
        else:
            estado = "ERROR"
            mensaje = redactar_pii(f"{exc_type.__name__}: {exc}")[:500]
            log.error("[%s] FIN ERROR tras %.1fs: %s", self.proceso, segundos, mensaje, exc_info=(exc_type, exc, tb))
        try:
            with self.engine.begin() as conn:
                conn.execute(schema.auditoria_ejecuciones.insert().values(
                    proceso=self.proceso, inicio=self.inicio, fin=fin, estado=estado,
                    filas_leidas=int(self.leidas), filas_cargadas=int(self.cargadas),
                    filas_rechazadas=int(self.rechazadas), mensaje=mensaje))
        except Exception:   # la auditoría no debe ocultar el error original
            log.exception("No se pudo registrar la ejecución de %s en auditoria_ejecuciones", self.proceso)
        return False
