"""Funciones de calidad de datos compartidas por los notebooks.

Cada función corresponde a una dimensión de calidad de la Unidad 1:
unicidad, consistencia, validez, completitud, precisión, oportunidad.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

import pandas as pd

FORMATOS_FECHA = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]
ZONA_CHILE = "America/Santiago"


# ------------------------------------------------------------------------- Texto
def _quitar_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar_texto(serie: pd.Series, mayusculas: bool = False, sin_tildes: bool = False) -> pd.Series:
    """Quita espacios sobrantes y, opcionalmente, pasa a mayúsculas / sin tildes (consistencia)."""
    out = serie.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    if sin_tildes:
        out = out.map(_quitar_tildes, na_action="ignore")
    if mayusculas:
        out = out.str.upper()
    return out


def normalizar_sku(serie: pd.Series) -> pd.Series:
    """SKU en mayúsculas y sin espacios, para homologar entre sistemas (consistencia)."""
    return normalizar_texto(serie, mayusculas=True).str.replace(" ", "", regex=False)


# ------------------------------------------------------------------------ Fechas
def parsear_fechas(serie: pd.Series) -> pd.Series:
    """Convierte fechas en varios formatos a datetime (validez).

    Soporta AAAA-MM-DD, DD/MM/AAAA, AAAA/MM/DD, DD-MM-AAAA y marcas ISO con hora
    (se interpretan como UTC y se pasan a la fecha de Chile). Lo inválido queda NaT.
    """
    texto = serie.astype("string").str.strip()
    resultado = pd.Series(pd.NaT, index=serie.index, dtype="datetime64[ns]")

    es_iso_hora = texto.str.contains("T", na=False)
    if es_iso_hora.any():
        parsed = pd.to_datetime(texto[es_iso_hora], utc=True, errors="coerce")
        parsed = parsed.dt.tz_convert(ZONA_CHILE).dt.tz_localize(None).dt.normalize()
        resultado.loc[es_iso_hora] = parsed.astype("datetime64[ns]")

    for formato in FORMATOS_FECHA:
        pendientes = resultado.isna() & ~es_iso_hora & texto.notna()
        if not pendientes.any():
            break
        parsed = pd.to_datetime(texto[pendientes], format=formato, errors="coerce")
        resultado.loc[parsed.index[parsed.notna()]] = parsed[parsed.notna()].astype("datetime64[ns]")

    return resultado.astype("datetime64[ns]")


# --------------------------------------------------------------------------- RUT
def _digito_verificador(cuerpo: int) -> str:
    suma, multiplicador = 0, 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    resto = 11 - (suma % 11)
    return "0" if resto == 11 else "K" if resto == 10 else str(resto)


def calcular_dv(cuerpo: int) -> str:
    """Dígito verificador (módulo 11) de un RUT sin DV."""
    return _digito_verificador(cuerpo)


def normalizar_rut(rut) -> str | None:
    """Devuelve el RUT como 'cuerpo-DV' sin puntos ni ceros a la izquierda, o None."""
    if rut is None or pd.isna(rut):
        return None
    limpio = re.sub(r"[^0-9kK]", "", str(rut)).upper()
    if len(limpio) < 2:
        return None
    try:
        return f"{int(limpio[:-1])}-{limpio[-1]}"
    except ValueError:
        return None


def rut_valido(rut) -> bool:
    """True si el RUT tiene formato correcto y su dígito verificador coincide (validez)."""
    normalizado = normalizar_rut(rut)
    if not normalizado:
        return False
    cuerpo, dv = normalizado.split("-")
    return _digito_verificador(int(cuerpo)) == dv


def validar_ruts(serie: pd.Series) -> pd.Series:
    return serie.map(rut_valido).astype(bool)


def anonimizar_rut(rut_normalizado: str, sal: str) -> str:
    """Hash SHA-256 con sal del RUT normalizado (seudonimización, Ley 21.719)."""
    return hashlib.sha256(f"{sal}:{rut_normalizado}".encode("utf-8")).hexdigest()[:32]


def anonimizar_serie(serie: pd.Series, sal: str) -> pd.Series:
    """Aplica `normalizar_rut` + `anonimizar_rut`; los RUT inválidos quedan como NA."""
    def _una(valor):
        n = normalizar_rut(valor)
        return anonimizar_rut(n, sal) if n and rut_valido(n) else pd.NA
    return serie.map(_una).astype("string")


# ----------------------------------------------------------------------- Derivados
def tramo_etario(fecha_nacimiento: pd.Series, fecha_referencia) -> pd.Series:
    """Tramo de edad a partir de la fecha de nacimiento (no se guarda la fecha: minimización)."""
    ref = pd.Timestamp(fecha_referencia)
    edad = (ref - fecha_nacimiento).dt.days // 365
    tramos = pd.cut(edad, bins=[-1, 24, 34, 44, 54, 200],
                    labels=["<25", "25-34", "35-44", "45-54", "55+"])
    return tramos.astype("string").fillna("NO INFORMADO")


# ----------------------------------------------------------------------- Rechazos
COLUMNAS_RECHAZO = ["origen_archivo", "fila_origen", "motivo_rechazo", "detalle"]


def construir_rechazos(df: pd.DataFrame, mascara: pd.Series, motivo: str,
                       detalle: str | None = None) -> pd.DataFrame:
    """Arma el DataFrame de rechazos para las filas marcadas por `mascara`.

    `df` debe traer `origen_archivo` y `fila_origen` (los agrega `extract.leer_csv`).
    El `detalle` NO debe contener datos personales.
    """
    mascara = mascara.fillna(False).astype(bool)
    r = df.loc[mascara, ["origen_archivo", "fila_origen"]].copy()
    r["motivo_rechazo"] = motivo
    r["detalle"] = detalle
    return r.reset_index(drop=True)[COLUMNAS_RECHAZO]


def separar_rechazos(df: pd.DataFrame, mascara_invalida: pd.Series, motivo: str,
                     detalle: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide `df` en (filas válidas, rechazos) según `mascara_invalida`."""
    mascara_invalida = mascara_invalida.fillna(False).astype(bool)
    rechazos = construir_rechazos(df, mascara_invalida, motivo, detalle)
    return df.loc[~mascara_invalida].copy(), rechazos


def consolidar_rechazos(*rechazos: pd.DataFrame) -> pd.DataFrame:
    """Une varios DataFrames de rechazos en uno solo."""
    validos = [r for r in rechazos if r is not None and len(r)]
    if not validos:
        return pd.DataFrame(columns=COLUMNAS_RECHAZO)
    return pd.concat(validos, ignore_index=True)[COLUMNAS_RECHAZO]


# ------------------------------------------------------------------ Chequeo de SCD2
def chequear_scd2(dim: pd.DataFrame, clave_natural: str, key_col: str) -> list[str]:
    """Revisa la integridad de una dimensión SCD Tipo 2. Retorna la lista de problemas (vacía = OK).

    Verifica: claves sustitutas únicas, exactamente UNA versión vigente por clave natural,
    `valido_desde` <= `valido_hasta`, coherencia entre `es_actual` y `valido_hasta` = 9999-12-31,
    y que las versiones de una misma clave no se solapen en el tiempo.
    """
    problemas: list[str] = []
    d = dim[dim[key_col] != -1].copy()
    if d[key_col].duplicated().any():
        problemas.append(f"{key_col}: hay claves sustitutas repetidas")

    vigentes = d[d["es_actual"] == 1].groupby(clave_natural).size()
    sin_vigente = set(d[clave_natural]) - set(vigentes.index)
    if sin_vigente:
        problemas.append(f"{len(sin_vigente)} claves naturales sin versión vigente")
    if (vigentes > 1).any():
        problemas.append(f"{int((vigentes > 1).sum())} claves naturales con más de una versión vigente")

    desde = pd.to_datetime(d["valido_desde"].astype(str).str[:10], errors="coerce")
    hasta_txt = d["valido_hasta"].astype(str).str[:10]
    if (desde > pd.to_datetime(hasta_txt.where(hasta_txt != "9999-12-31", "2262-04-11"), errors="coerce")).any():
        problemas.append("hay versiones con valido_desde posterior a valido_hasta")
    abierta = hasta_txt == "9999-12-31"
    if ((d["es_actual"] == 1) != abierta).any():
        problemas.append("es_actual no es coherente con valido_hasta = 9999-12-31")

    d = d.assign(_d=desde.values, _h=pd.to_datetime(hasta_txt.where(~abierta, "2262-04-11"), errors="coerce").values)
    for clave, grupo in d.sort_values("_d").groupby(clave_natural):
        if len(grupo) > 1 and (grupo["_d"].iloc[1:].values <= grupo["_h"].iloc[:-1].values).any():
            problemas.append(f"versiones solapadas en una clave natural (ej. índice {grupo.index[0]})")
            break
    return problemas
