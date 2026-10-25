from datetime import date

import pandas as pd

from src import db, schema


def _producto(sku, categoria, nombre="X"):
    return pd.DataFrame({"sku": [sku], "categoria": [categoria], "nombre_producto": [nombre]})


def _cargar(engine, df, efectiva):
    return db.aplicar_scd2(engine, schema.dim_producto, df, "sku", ["categoria"],
                           efectiva, "producto_key", atributos_scd1=["nombre_producto"])


def test_primera_carga_parte_en_fecha_inicio_defecto(engine):
    r = _cargar(engine, _producto("A-1", "Accesorios"), date(2025, 1, 1))
    assert r["nuevos"] == 1
    d = db.leer_tabla(engine, "dim_producto")
    fila = d[d.sku == "A-1"].iloc[0]
    assert str(fila.valido_desde) == "1900-01-01" and str(fila.valido_hasta) == "9999-12-31" and fila.es_actual == 1


def test_cambio_scd2_crea_nueva_version_y_cierra_la_anterior(engine):
    _cargar(engine, _producto("A-1", "Accesorios"), date(2025, 1, 1))
    r = _cargar(engine, _producto("A-1", "Audio"), date(2025, 6, 1))
    assert r["versiones_nuevas"] == 1
    d = db.leer_tabla(engine, "dim_producto")
    d = d[d.sku == "A-1"].sort_values("valido_desde")
    assert d.es_actual.tolist() == [0, 1]
    assert d.categoria.tolist() == ["Accesorios", "Audio"]
    assert str(d.iloc[0].valido_hasta) == "2025-05-31" and str(d.iloc[1].valido_desde) == "2025-06-01"


def test_scd2_es_idempotente(engine):
    _cargar(engine, _producto("A-1", "Accesorios"), date(2025, 1, 1))
    _cargar(engine, _producto("A-1", "Audio"), date(2025, 6, 1))
    antes = len(db.leer_tabla(engine, "dim_producto"))
    r1 = _cargar(engine, _producto("A-1", "Audio"), date(2025, 6, 1))
    r2 = _cargar(engine, _producto("A-1", "Audio"), date(2025, 6, 1))
    assert r1["versiones_nuevas"] == 0 and r2["sin_cambio"] == 1
    assert len(db.leer_tabla(engine, "dim_producto")) == antes


def test_cambio_solo_scd1_no_crea_version(engine):
    _cargar(engine, _producto("A-1", "Audio", "Nombre viejo"), date(2025, 1, 1))
    r = _cargar(engine, _producto("A-1", "Audio", "Nombre nuevo"), date(2025, 6, 1))
    assert r["actualizados_scd1"] == 1 and r["versiones_nuevas"] == 0
    d = db.leer_tabla(engine, "dim_producto")
    assert d[d.sku == "A-1"].nombre_producto.tolist() == ["Nombre nuevo"]


def test_clave_nueva_en_snapshot_posterior_parte_en_fecha_efectiva(engine):
    _cargar(engine, _producto("A-1", "Audio"), date(2025, 1, 1))
    _cargar(engine, _producto("B-2", "Hogar"), date(2025, 6, 1))
    d = db.leer_tabla(engine, "dim_producto")
    assert str(d[d.sku == "B-2"].iloc[0].valido_desde) == "2025-06-01"


def test_reprocesar_snapshots_antiguos_es_idempotente_en_cualquier_orden(engine):
    _cargar(engine, _producto("A-1", "Accesorios"), date(2025, 1, 1))
    _cargar(engine, _producto("A-1", "Audio"), date(2025, 6, 1))
    antes = db.leer_tabla(engine, "dim_producto")
    r_viejo = _cargar(engine, _producto("A-1", "Accesorios"), date(2025, 1, 1))   # snapshot 1 otra vez
    r_nuevo = _cargar(engine, _producto("A-1", "Audio"), date(2025, 6, 1))        # snapshot 2 otra vez
    assert r_viejo["sin_cambio"] == 1 and r_nuevo["sin_cambio"] == 1
    assert len(db.leer_tabla(engine, "dim_producto")) == len(antes)


def test_dato_retroactivo_que_contradice_la_historia_falla(engine):
    import pytest
    from src.errores import ErrorFatal
    _cargar(engine, _producto("A-1", "Accesorios"), date(2025, 1, 1))
    _cargar(engine, _producto("A-1", "Audio"), date(2025, 6, 1))
    with pytest.raises(ErrorFatal):
        _cargar(engine, _producto("A-1", "Hogar"), date(2025, 3, 1))   # en marzo era "Accesorios"


def test_cambio_con_la_misma_fecha_efectiva_falla(engine):
    import pytest
    from src.errores import ErrorFatal
    _cargar(engine, _producto("A-1", "Accesorios"), date(2025, 1, 1))
    _cargar(engine, _producto("A-1", "Audio"), date(2025, 6, 1))
    with pytest.raises(ErrorFatal):
        _cargar(engine, _producto("A-1", "Hogar"), date(2025, 6, 1))   # otro valor el mismo día


def test_asignar_clave_scd2_usa_la_version_vigente_a_la_fecha_de_la_venta(engine):
    _cargar(engine, _producto("A-1", "Accesorios"), date(2025, 1, 1))
    _cargar(engine, _producto("A-1", "Audio"), date(2025, 6, 1))
    dim = db.leer_tabla(engine, "dim_producto")
    ventas = pd.DataFrame({"sku": ["A-1", "A-1", "A-1", "ZZZ"],
                           "fecha": pd.to_datetime(["2025-03-10", "2025-05-31", "2025-06-01", "2025-06-01"])})
    keys = db.asignar_clave_scd2(ventas, dim, "sku", "fecha", "producto_key")
    cat = dim.set_index("producto_key").categoria
    assert cat[keys.iloc[0]] == "Accesorios"   # antes del cambio
    assert cat[keys.iloc[1]] == "Accesorios"   # último día de la versión vieja
    assert cat[keys.iloc[2]] == "Audio"        # primer día de la versión nueva
    assert keys.iloc[3] == -1                  # SKU inexistente -> No informado


def test_scd1_inserta_actualiza_y_es_idempotente(engine):
    df = pd.DataFrame({"canal": ["E-commerce", "Tienda física"], "tipo_canal": ["Digital", "Físico"]})
    a = db.aplicar_scd1(engine, "dim_canal", df, "canal", ["tipo_canal"], "canal_key")
    b = db.aplicar_scd1(engine, "dim_canal", df, "canal", ["tipo_canal"], "canal_key")
    df.loc[0, "tipo_canal"] = "Online"
    c = db.aplicar_scd1(engine, "dim_canal", df, "canal", ["tipo_canal"], "canal_key")
    assert a["nuevos"] == 2 and b["sin_cambio"] == 2 and c["actualizados"] == 1


def test_chequear_scd2_detecta_dimension_sana_y_corrupta(engine):
    from src import quality as q
    _cargar(engine, _producto("A-1", "Accesorios"), date(2025, 1, 1))
    _cargar(engine, _producto("A-1", "Audio"), date(2025, 6, 1))
    dim = db.leer_tabla(engine, "dim_producto")
    assert q.chequear_scd2(dim, "sku", "producto_key") == []
    mala = dim.copy()
    mala.loc[mala.es_actual == 0, "es_actual"] = 1          # dos versiones vigentes
    assert any("más de una versión vigente" in p for p in q.chequear_scd2(mala, "sku", "producto_key"))
