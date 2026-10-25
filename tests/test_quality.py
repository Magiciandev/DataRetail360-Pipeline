import pandas as pd

from src import quality as q


def test_rut_valido_e_invalido():
    assert q.rut_valido("12.345.678-5")
    assert q.rut_valido("12345678-5")
    assert not q.rut_valido("12345678-9")
    assert not q.rut_valido("abc")
    assert not q.rut_valido(None)


def test_normalizar_rut_quita_puntos_y_ceros():
    assert q.normalizar_rut("012.345.678-5") == "12345678-5"
    assert q.normalizar_rut("12345678-k") is None or q.normalizar_rut("12345678-k").endswith("-K")


def test_anonimizar_es_estable_y_depende_de_la_sal():
    a = q.anonimizar_rut("12345678-5", "sal1")
    assert a == q.anonimizar_rut("12345678-5", "sal1")
    assert a != q.anonimizar_rut("12345678-5", "sal2")
    assert "12345678" not in a


def test_parsear_fechas_formatos_mixtos():
    s = pd.Series(["2025-03-28", "12/05/2025", "2025/06/01", "2025-05-12T14:03:22Z", "basura", None])
    r = q.parsear_fechas(s)
    assert r.iloc[0] == pd.Timestamp("2025-03-28")
    assert r.iloc[1] == pd.Timestamp("2025-05-12")
    assert r.iloc[2] == pd.Timestamp("2025-06-01")
    assert r.iloc[3] == pd.Timestamp("2025-05-12")
    assert r.iloc[4:].isna().all()


def test_parsear_fechas_utc_pasa_a_fecha_de_chile():
    # 02:30 UTC del 13 de mayo es la noche del 12 de mayo en Chile
    r = q.parsear_fechas(pd.Series(["2025-05-13T02:30:00Z"]))
    assert r.iloc[0] == pd.Timestamp("2025-05-12")


def test_normalizar_sku():
    r = q.normalizar_sku(pd.Series([" nb-001 ", "au 002"]))
    assert r.tolist() == ["NB-001", "AU002"]


def test_separar_rechazos_conserva_origen():
    df = pd.DataFrame({"x": [1, -2, 3], "origen_archivo": "a.csv", "fila_origen": [2, 3, 4]})
    ok, rech = q.separar_rechazos(df, df["x"] < 0, "monto_negativo")
    assert len(ok) == 2 and len(rech) == 1
    assert rech.iloc[0]["fila_origen"] == 3 and rech.iloc[0]["motivo_rechazo"] == "monto_negativo"
