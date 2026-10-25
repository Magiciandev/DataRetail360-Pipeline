import pandas as pd
import pytest

from src import db, schema
from src.errores import ErrorFatal


def test_insertar_si_no_existe_es_idempotente(engine):
    df = pd.DataFrame({"canal": ["A", "B", "B"], "tipo_canal": ["x", "y", "y"], "canal_key": [10, 11, 12]})
    r1 = db.insertar_si_no_existe(engine, schema.dim_canal, df, ["canal"])
    r2 = db.insertar_si_no_existe(engine, schema.dim_canal, df, ["canal"])
    assert r1["insertadas"] == 2 and r1["duplicadas_en_lote"] == 1
    assert r2["insertadas"] == 0 and r2["ya_existian"] == 2


def test_rechazos_se_registran_una_sola_vez_y_sin_pii(engine):
    rech = pd.DataFrame({"origen_archivo": ["c.csv"], "fila_origen": [5],
                         "motivo_rechazo": ["rut_invalido"],
                         "detalle": ["RUT 12.345.678-5 de ana@example.com no valida"]})
    db.registrar_rechazos(engine, "dim_cliente", rech)
    db.registrar_rechazos(engine, "dim_cliente", rech)
    t = db.leer_tabla(engine, "auditoria_rechazos")
    assert len(t) == 1
    assert "12.345.678" not in t.iloc[0].detalle and "@" not in t.iloc[0].detalle


def test_ejecucion_ok_deja_registro(engine):
    with db.Ejecucion(engine, "proceso_ok") as run:
        run.leidas, run.cargadas, run.rechazadas = 10, 8, 2
    t = db.leer_tabla(engine, "auditoria_ejecuciones")
    fila = t.iloc[0]
    assert fila.estado == "OK" and fila.filas_leidas == 10 and fila.filas_rechazadas == 2


def test_ejecucion_con_error_registra_y_relanza(engine):
    with pytest.raises(ValueError):
        with db.Ejecucion(engine, "proceso_malo"):
            raise ValueError("falló con ana@example.com")
    t = db.leer_tabla(engine, "auditoria_ejecuciones")
    assert t.iloc[0].estado == "ERROR" and "@" not in t.iloc[0].mensaje


def test_reintentar_agota_intentos_y_lanza_error_fatal():
    from sqlalchemy.exc import OperationalError
    llamadas = []

    @db.reintentar(intentos=3, espera=0)
    def falla():
        llamadas.append(1)
        raise OperationalError("x", {}, Exception("caída"))

    with pytest.raises(ErrorFatal):
        falla()
    assert len(llamadas) == 3


def test_scd_exige_clave_natural_unica(engine):
    df = pd.DataFrame({"sku": ["A", "A"], "categoria": ["x", "y"], "nombre_producto": ["n", "n"]})
    with pytest.raises(ErrorFatal):
        db.aplicar_scd2(engine, "dim_producto", df, "sku", ["categoria"],
                        pd.Timestamp("2025-01-01").date(), "producto_key", ["nombre_producto"])
