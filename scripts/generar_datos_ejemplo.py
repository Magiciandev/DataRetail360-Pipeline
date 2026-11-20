"""Genera los datos de ejemplo SINTÉTICOS de DataRetail 360 en data/sample/.

Son datos ficticios con problemas de calidad plantados a propósito (los mismos que
describió el caso: clientes duplicados, SKU sin homologar, ventas sin sucursal,
formatos de fecha dispares, montos inválidos). Los RUT son sintéticos (cuerpo > 30
millones, fuera del rango de personas reales) con dígito verificador válido.

Para la Experiencia 3 (KPIs y dashboard) el generador SIMULA el negocio día a día, de modo
que ventas, inventario y campañas sean coherentes entre sí (mismos SKU, sucursales, clientes
y fechas; el stock nunca es negativo y no se vende lo que no hay):

    ventas_pos.csv / ventas_ecommerce.json   transacciones (POS y e-commerce)
    inventario_wms.csv                       foto diaria producto x sucursal (WMS)
    productos_snapshot_*.csv                 catálogo con `costo_unitario` neto (ERP)
    campanas.csv / campanas_contactos.csv    planillas de Marketing (sin ventas: la atribución
                                             se calcula en el pipeline con las ventas del DW)

HISTORIA (narrativa Situación-Complicación-Idea que sostienen los datos; es SINTÉTICA y debe
declararse así en el informe):
  Situación    marzo-julio: la venta neta es estable y el quiebre de stock es bajo.
  Complicación del 4 al 24 de agosto el proveedor retrasa la reposición de Tecnología: hay
               quiebre de stock, cae la venta de Tecnología y la campaña «Semana Tech»
               (11-17 de agosto) tiene muchas respuestas pero casi no logra compras (ROAS < 1x).
  Idea         reponer stock ANTES de lanzar campañas y mover presupuesto desde la campaña de
               bajo ROAS hacia las que sí convierten (Hogar Fest, ROAS alto).

Si el curso entrega archivos CSV/JSON oficiales, basta con reemplazarlos en
`data/sample/` (o apuntar `DATA_DIR` a otra carpeta) y adaptar las transformaciones.

Uso:  python scripts/generar_datos_ejemplo.py
"""
import csv
import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.quality import calcular_dv  # noqa: E402

DESTINO = Path(__file__).resolve().parent.parent / "data" / "sample"
SEMILLA = 42
random.seed(SEMILLA)
rng = np.random.default_rng(SEMILLA)

# ------------------------------------------------------------------ Parámetros
INICIO, FIN = date(2025, 3, 3), date(2025, 8, 31)       # lunes 3 de marzo -> 31 de agosto
N_CLIENTES = 1500
LANZAMIENTO_MN010 = date(2025, 6, 1)                    # el Monitor entra al catálogo en el snapshot 2
QUIEBRE_INICIO, QUIEBRE_FIN = date(2025, 8, 4), date(2025, 8, 24)   # sin reposición de Tecnología
SKUS_QUIEBRE = ["NB-001", "NB-002", "TV-004", "CL-006", "MN-010"]
PROB_MERMA = 0.003                                      # probabilidad diaria de perder 1 unidad


def escribir_csv(nombre, columnas, filas):
    with open(DESTINO / nombre, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        w.writerows(filas)
    print(f"  {nombre}: {len(filas)} filas")


def rut(cuerpo, con_puntos=False, dv_mal=False):
    dv = calcular_dv(cuerpo)
    if dv_mal:
        dv = "0" if dv != "0" else "1"
    if con_puntos:
        return f"{cuerpo:,}".replace(",", ".") + f"-{dv}"
    return f"{cuerpo}-{dv}"


# ----------------------------------------------------------------------- Geografía
GEO = [  # codigo, comuna, provincia, region, zona_comercial, lat, lon
    ("13101", "Santiago", "Santiago", "Metropolitana", "Centro", -33.4489, -70.6693),
    ("13123", "Providencia", "Santiago", "Metropolitana", "Centro", -33.4314, -70.6093),
    ("13114", "Las Condes", "Santiago", "Metropolitana", "Centro", -33.4081, -70.5675),
    ("13119", "Maipú", "Santiago", "Metropolitana", "Centro", -33.5106, -70.7575),
    ("13201", "Puente Alto", "Cordillera", "Metropolitana", "Centro", -33.6117, -70.5758),
    ("5101", "Valparaíso", "Valparaíso", "Valparaíso", "Centro", -33.0472, -71.6127),
    ("5109", "Viña del Mar", "Valparaíso", "Valparaíso", "Centro", -33.0245, -71.5518),
    ("8101", "Concepción", "Concepción", "Biobío", "Sur", -36.8270, -73.0503),
    ("8110", "Talcahuano", "Concepción", "Biobío", "Sur", -36.7249, -73.1168),
    ("16101", "Chillán", "Diguillín", "Ñuble", "Centro", -36.6066, -72.1034),
    ("2101", "Antofagasta", "Antofagasta", "Antofagasta", "Norte", -23.6509, -70.3975),
    ("9101", "Temuco", "Cautín", "Araucanía", "Sur", -38.7359, -72.5904),
    ("10101", "Puerto Montt", "Llanquihue", "Los Lagos", "Sur", -41.4693, -72.9424),
    ("4101", "La Serena", "Elqui", "Coquimbo", "Norte", -29.9027, -71.2519),
]
COLS_GEO = ["codigo_comuna", "comuna", "provincia", "region", "pais", "zona_comercial", "latitud", "longitud"]


def fila_geo(g, zona=None):
    return [g[0], g[1], g[2], g[3], "Chile", zona or g[4], g[5], g[6]]


geo1 = [fila_geo(g) for g in GEO]
geo1.append(["13101", "santiago ", "Santiago", "Metropolitana", "Chile", "Centro", -33.4489, -70.6693])  # duplicado
geo1.append(["99998", "Sin nombre", "", "", "Chile", "", 999.0, 999.0])                                    # coordenadas inválidas
# snapshot 2: re-zonificación comercial ilustrativa de Chillán (Centro -> Sur)
geo2 = [fila_geo(g, zona="Sur" if g[0] == "16101" else None) for g in GEO]

# ---------------------------------------------------------------------- Sucursales
SUCURSALES = [
    ("S00", "Centro de Distribución Online", "Bodega/Online", "13119"),
    ("S01", "Providencia", "Mall", "13123"), ("S02", "Maipú", "Tienda calle", "13119"),
    ("S03", "Concepción", "Mall", "8101"), ("S04", "Antofagasta", "Tienda calle", "2101"),
    ("S05", "Viña del Mar", "Mall", "5109"), ("S06", "Temuco", "Tienda calle", "9101"),
]
ONLINE = "S00"
TIENDAS = ["S01", "S02", "S03", "S04", "S05", "S06"]

# ----------------------------------------------------------------------- Productos
PRODUCTOS = [  # sku, nombre, marca, categoria, subcategoria, linea, precio (CLP con IVA)
    ("NB-001", 'Notebook 15"', "Acme", "Tecnología", "Computación", "Tecnología", 799000),
    ("NB-002", 'Notebook Pro 14"', "Acme", "Tecnología", "Computación", "Tecnología", 1199000),
    ("AU-002", "Audífonos Bluetooth", "Sonora", "Accesorios", "Audio", "Tecnología", 49990),
    ("AS-003", "Aspiradora Robot", "HogarPlus", "Hogar", "Electrohogar", "Hogar", 129990),
    ("TV-004", 'Televisor 50"', "Visionix", "Tecnología", "Imagen", "Tecnología", 349990),
    ("CF-005", "Cafetera Espresso", "Cafetto", "Hogar", "Cocina", "Hogar", 59990),
    ("CL-006", "Smartphone 128GB", "Movix", "Tecnología", "Telefonía", "Tecnología", 449990),
    ("MS-007", "Mouse Inalámbrico", "Clickr", "Accesorios", "Periféricos", "Tecnología", 15990),
    ("TC-008", "Teclado Mecánico", "Clickr", "Accesorios", "Periféricos", "Tecnología", 24990),
    ("RF-009", "Refrigerador No Frost", "FrioMax", "Hogar", "Línea blanca", "Hogar", 549990),
]
NUEVO_PRODUCTO = ("MN-010", 'Monitor 27"', "Visionix", "Tecnología", "Imagen", "Tecnología", 189990)
COLS_PROD = ["sku", "nombre_producto", "marca", "categoria", "subcategoria", "linea_negocio", "costo_unitario"]
PRECIOS = {p[0]: p[6] for p in PRODUCTOS + [NUEVO_PRODUCTO]}
RATIO_COSTO = {"Tecnología": 0.78, "Hogar": 0.70, "Accesorios": 0.55}   # costo / precio neto, por categoría
# Costo unitario NETO (sin IVA), como lo informa el ERP.
COSTOS = {p[0]: round(p[6] / 1.19 * RATIO_COSTO[p[3]]) for p in PRODUCTOS + [NUEVO_PRODUCTO]}


def fila_prod(p, **cambios):
    f = dict(zip(COLS_PROD[:6], p[:6]))
    f["costo_unitario"] = COSTOS[p[0]]
    f.update(cambios)
    return [f[c] for c in COLS_PROD]


prod1 = [fila_prod(p) for p in PRODUCTOS]
prod1[4][0] = " tv-004 "                              # SKU sin homologar
prod1.append(fila_prod(PRODUCTOS[5], sku="cf-005"))   # duplicado con otro formato
prod1.append(["", "Producto sin SKU", "Acme", "Tecnología", "", "Tecnología", 450000])  # SKU vacío
prod2 = [fila_prod(p) for p in PRODUCTOS]
prod2[2] = fila_prod(PRODUCTOS[2], categoria="Audio", subcategoria="Audífonos")     # cambia de categoría
prod2[6] = fila_prod(PRODUCTOS[6], linea_negocio="Telefonía")                       # cambia de línea
prod2.append(fila_prod(NUEVO_PRODUCTO))                                              # producto nuevo

# ------------------------------------------------------------------------ Clientes
NOMBRES = ["Ana", "Luis", "Camila", "Diego", "Valentina", "Matías", "Sofía", "Javier", "Fernanda", "Pablo"]
APELLIDOS = ["Rojas", "Soto", "Muñoz", "Pérez", "Silva", "Núñez", "Vega", "Reyes", "Castro", "Mora"]
COMUNAS = [g[0] for g in GEO]
SEGMENTOS = ["Nuevo", "Recurrente", "VIP"]
BASE = []
for i in range(N_CLIENTES):
    cuerpo = 31_000_000 + i * 13
    BASE.append({
        "cuerpo": cuerpo,
        "nombre": f"{NOMBRES[i % 10]} {APELLIDOS[(i * 3) % 10]}",
        "email": f"cliente{i:03d}@example.com",
        "comuna": COMUNAS[i % len(COMUNAS)],
        "segmento": SEGMENTOS[i % 3],
        "registro": date(2022, 1, 1) + timedelta(days=(i * 37) % 1100),       # siempre antes de marzo de 2025
        "nacimiento": date(1960, 1, 1) + timedelta(days=(i * 520) % 16000),   # entre 1960 y 2003
    })
COLS_CLI = ["rut", "nombre", "email", "codigo_comuna", "segmento", "fecha_registro", "fecha_nacimiento"]


def fila_cli(c, **cambios):
    f = {"rut": rut(c["cuerpo"]), "nombre": c["nombre"], "email": c["email"],
         "codigo_comuna": c["comuna"], "segmento": c["segmento"],
         "fecha_registro": c["registro"].isoformat(), "fecha_nacimiento": c["nacimiento"].isoformat()}
    f.update(cambios)
    return [f[k] for k in COLS_CLI]


cli1 = [fila_cli(c) for c in BASE]
cli1.append(fila_cli(BASE[3], rut=rut(BASE[3]["cuerpo"], con_puntos=True),
                     nombre=BASE[3]["nombre"].upper(), email="otro.correo03@example.com"))   # duplicado por RUT
cli1.append(fila_cli(BASE[7], rut=rut(BASE[7]["cuerpo"], con_puntos=True),
                     email="otro.correo07@example.com"))                                    # duplicado por RUT
cli1.append(fila_cli(BASE[0], rut=rut(32_000_001, dv_mal=True), email="malrut1@example.com"))  # RUT inválido
cli1.append(fila_cli(BASE[1], rut="no-es-un-rut", email="malrut2@example.com"))                # RUT inválido
cli1.append(fila_cli(BASE[2], rut=rut(32_000_010), email="sincomuna@example.com", codigo_comuna=""))  # sin comuna
cli1.append(fila_cli(BASE[4], rut=rut(32_000_020), email="comunadesconocida@example.com", codigo_comuna="99999"))

cli2 = [fila_cli(c) for c in BASE]
for idx, nueva_comuna in [(2, "8101"), (9, "5101"), (15, "9101")]:        # 3 clientes se cambian de comuna
    cli2[idx][COLS_CLI.index("codigo_comuna")] = nueva_comuna
cli2[5][COLS_CLI.index("segmento")] = "VIP"                              # cambia de segmento
cli2[11][COLS_CLI.index("segmento")] = "Recurrente"
for j in range(2):                                                       # 2 clientes nuevos
    cuerpo = 31_500_000 + j * 13
    cli2.append(fila_cli({"cuerpo": cuerpo, "nombre": f"Nuevo Cliente{j}", "email": f"nuevo{j}@example.com",
                          "comuna": COMUNAS[j + 1], "segmento": "Nuevo",
                          "registro": date(2025, 6, 10), "nacimiento": date(1990, 5, 5)}))

# ======================================================================= Simulación
# Los clientes compran con distinta frecuencia (los VIP más). Solo compran los clientes de BASE.
FACTOR_SEGMENTO = {"Nuevo": 1.0, "Recurrente": 1.6, "VIP": 2.8}
pesos = np.array([FACTOR_SEGMENTO[c["segmento"]] * rng.lognormal(0, 0.8) for c in BASE])
PESOS_CLIENTE = pesos / pesos.sum()
RUTS_VENTA = [rut(c["cuerpo"], con_puntos=(i % 3 == 0)) for i, c in enumerate(BASE)]

POPULARIDAD = {"NB-001": .10, "NB-002": .05, "AU-002": .16, "AS-003": .08, "TV-004": .08, "CF-005": .12,
               "CL-006": .12, "MS-007": .13, "TC-008": .10, "RF-009": .04, "MN-010": .07}
TOTAL_POP = sum(POPULARIDAD.values())
LAMBDA = {"S01": 3.0, "S02": 2.4, "S03": 2.0, "S04": 1.4, "S05": 2.0, "S06": 1.4, ONLINE: 5.0}   # ventas/día
FACTOR_DOW_TIENDA = [0.85, 0.85, 0.90, 0.95, 1.15, 1.35, 1.20]    # lunes..domingo
FACTOR_DOW_ONLINE = [1.00, 1.00, 1.00, 1.00, 1.05, 1.05, 1.10]
FACTOR_MES = {3: 1.00, 4: 0.98, 5: 1.04, 6: 1.08, 7: 1.06, 8: 1.08}
LINEAS_POR_TX = ([1, 2, 3], [0.55, 0.30, 0.15])
MEDIA_LINEAS = 1.6


def qty_aleatoria(sku):
    if PRECIOS[sku] > 300_000:
        return int(rng.choice([1, 2], p=[0.95, 0.05]))
    return int(rng.choice([1, 2, 3], p=[0.60, 0.28, 0.12]))


def qty_media(sku):
    return 1.05 if PRECIOS[sku] > 300_000 else 1.52


# Nivel objetivo de stock por sucursal y SKU: ~1,9 semanas de demanda esperada (reposición semanal).
OBJETIVO = {(s, k): max(3, math.ceil(1.9 * 7 * LAMBDA[s] * MEDIA_LINEAS * (POPULARIDAD[k] / TOTAL_POP)
                                     * qty_media(k) * 1.1) + 2)
            for s in LAMBDA for k in POPULARIDAD}

# ------------------------------------------------------------------ Campañas (Marketing)
# presupuesto: inversión TOTAL de la campaña (CLP). Calibrados para la historia (ver docstring).
CAMPANAS = [
    dict(cod="CMP-001", nombre="Accesorios de Otoño", tipo="Email", objetivo="Venta cruzada de accesorios",
         canal="E-commerce", envio=date(2025, 3, 24), fin=date(2025, 3, 30), skus=["MS-007", "TC-008", "AU-002"],
         n=220, p_resp=0.24, p_compra=0.30, presupuesto=640_000),
    dict(cod="CMP-002", nombre="Hogar Fest", tipo="Email + SMS", objetivo="Impulsar la categoría Hogar",
         canal="E-commerce", envio=date(2025, 5, 12), fin=date(2025, 5, 18), skus=["AS-003", "CF-005", "RF-009"],
         n=260, p_resp=0.30, p_compra=0.35, presupuesto=2_000_000),
    dict(cod="CMP-003", nombre="Gamer Junio", tipo="SMS", objetivo="Periféricos y monitores",
         canal="Tienda física", envio=date(2025, 6, 16), fin=date(2025, 6, 22), skus=["MS-007", "TC-008", "MN-010"],
         n=240, p_resp=0.22, p_compra=0.28, presupuesto=1_250_000),
    dict(cod="CMP-004", nombre="Semana Tech", tipo="Email", objetivo="Liquidar inventario de Tecnología",
         canal="E-commerce", envio=date(2025, 8, 11), fin=date(2025, 8, 17),
         skus=["NB-001", "TV-004", "CL-006", "MN-010"],
         n=300, p_resp=0.32, p_compra=0.40, presupuesto=3_500_000),
]
CONTACTOS = []          # (campana, indice_cliente, sku, respondio)
COMPRAS_CAMPANA = {}    # fecha -> [(tienda, indice_cliente, sku, qty)]
for c in CAMPANAS:
    elegidos = rng.choice(N_CLIENTES, size=c["n"], replace=False, p=PESOS_CLIENTE)
    for ic in elegidos:
        sku = str(rng.choice(c["skus"]))
        respondio = rng.random() < c["p_resp"]
        CONTACTOS.append((c, int(ic), sku, bool(respondio)))
        if respondio and rng.random() < c["p_compra"]:
            d = c["envio"] + timedelta(days=int(rng.integers(0, 11)))
            tienda = ONLINE if c["canal"] == "E-commerce" else str(rng.choice(TIENDAS))
            qty = 1 if PRECIOS[sku] > 300_000 else int(rng.integers(1, 3))
            COMPRAS_CAMPANA.setdefault(d, []).append((tienda, int(ic), sku, qty))

# ------------------------------------------------------------- Simulación día a día
stock = {}
ventas_sim = []          # {fecha, tienda, ic (índice de cliente o None), lineas: [(sku, qty)]}
inventario = []          # (fecha, tienda, sku, stock al cierre, merma del día)
fechas = [INICIO + timedelta(days=i) for i in range((FIN - INICIO).days + 1)]
for d in fechas:
    disponibles = [k for k in POPULARIDAD if k != "MN-010" or d >= LANZAMIENTO_MN010]
    # 1) Reposición semanal (lunes) hasta el nivel objetivo; el proveedor de Tecnología se retrasa en agosto.
    for s in LAMBDA:
        for k in disponibles:
            if (s, k) not in stock:                       # primer día del SKU en esa sucursal
                stock[(s, k)] = OBJETIVO[(s, k)]
            elif d.weekday() == 0 and not (k in SKUS_QUIEBRE and QUIEBRE_INICIO <= d <= QUIEBRE_FIN):
                stock[(s, k)] = max(stock[(s, k)], OBJETIVO[(s, k)])

    def vender(tienda, ic, lineas_pedidas, dia=d):
        lineas = []
        for sku, qty in lineas_pedidas:
            real = min(qty, stock.get((tienda, sku), 0))
            if real > 0:                                  # sin stock no hay venta (venta perdida)
                stock[(tienda, sku)] -= real
                lineas.append((sku, real))
        if lineas:
            ventas_sim.append({"fecha": dia, "tienda": tienda, "ic": ic, "lineas": lineas})

    # 2) Compras que responden a una campaña (el cliente ya decidió comprar ese producto)
    for tienda, ic, sku, qty in COMPRAS_CAMPANA.get(d, []):
        vender(tienda, ic, [(sku, qty)])
    # 3) Ventas habituales de cada sucursal y del canal online
    probs = np.array([POPULARIDAD[k] for k in disponibles])
    probs = probs / probs.sum()
    for s, lam in LAMBDA.items():
        factor_dow = (FACTOR_DOW_ONLINE if s == ONLINE else FACTOR_DOW_TIENDA)[d.weekday()]
        n_tx = int(rng.poisson(lam * factor_dow * FACTOR_MES[d.month]))
        for _ in range(n_tx):
            n_lineas = int(rng.choice(LINEAS_POR_TX[0], p=LINEAS_POR_TX[1]))
            skus = rng.choice(disponibles, size=n_lineas, replace=True, p=probs)
            ic = None if (s != ONLINE and rng.random() < 0.08) else int(rng.choice(N_CLIENTES, p=PESOS_CLIENTE))
            vender(s, ic, [(str(k), qty_aleatoria(str(k))) for k in skus])
    # 4) Mermas y foto de cierre del día
    for s in LAMBDA:
        for k in disponibles:
            merma = 0
            if stock[(s, k)] > 0 and rng.random() < PROB_MERMA:
                stock[(s, k)] -= 1
                merma = 1
            inventario.append((d, s, k, stock[(s, k)], merma))

# ======================================================================= Ventas


def fmt_fecha(d):
    r = random.random()
    if r < 0.70:
        return d.strftime("%d/%m/%Y")
    return d.strftime("%Y-%m-%d") if r < 0.90 else d.strftime("%Y/%m/%d")


def variante_sku(sku):
    r = random.random()
    return sku.lower() if r < 0.15 else f" {sku} " if r < 0.25 else sku


CANALES_POS = ["Tienda física"] * 6 + ["Tienda fisica", "TIENDA FÍSICA", "tienda física "]
ventas_pos, n_pos = [], 0
ordenes, n_ec = [], 0
for v in sorted(ventas_sim, key=lambda x: x["fecha"]):
    if v["tienda"] == ONLINE:
        n_ec += 1
        hora = f"{random.randint(12, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"
        ordenes.append({
            "order_id": f"EC-{1000 + n_ec}", "created_at": f"{v['fecha'].isoformat()}T{hora}Z",
            "channel": random.choice(["E-commerce", "E-commerce", "ecommerce", "Web"]),
            "status": "PAID",
            "customer": {"rut": RUTS_VENTA[v["ic"]], "email": f"web{n_ec}@example.com"},
            "items": [{"sku": variante_sku(sku), "qty": qty, "line_total": PRECIOS[sku] * qty}
                      for sku, qty in v["lineas"]],
        })
    else:
        n_pos += 1
        id_tx = f"POS-{n_pos:04d}"
        canal = random.choice(CANALES_POS)
        fecha_txt = fmt_fecha(v["fecha"])
        rut_txt = "" if v["ic"] is None else RUTS_VENTA[v["ic"]]
        for linea, (sku, qty) in enumerate(v["lineas"], start=1):
            ventas_pos.append([id_tx, linea, fecha_txt, variante_sku(sku), rut_txt, v["tienda"], canal,
                               qty, PRECIOS[sku] * qty, "OK"])
COLS_POS = ["id_transaccion", "linea", "fecha", "sku", "rut", "id_sucursal", "canal", "cantidad", "monto", "estado"]

# --- problemas plantados (los mismos del caso; en cantidades proporcionales al volumen)
n_base = len(ventas_pos)
orden = [int(i) for i in rng.permutation(n_base)]


def tomar(n):
    return [orden.pop() for _ in range(n)]


for i in tomar(max(1, round(n_base * 0.012))):
    ventas_pos[i][5] = ""                                           # sucursal vacía
for i in tomar(6):
    ventas_pos[i][8] = -abs(int(ventas_pos[i][8]))                  # monto negativo con estado OK
for i in tomar(round(n_base * 0.03)):
    ventas_pos[i][9] = "DEVUELTA"                                   # devolución
for i in tomar(round(n_base * 0.02)):
    ventas_pos[i][9] = "ANULADA"                                    # venta anulada
for i in tomar(5):
    ventas_pos[i][3] = "ZZ-999"                                     # SKU que no existe en el catálogo
for i in tomar(3):
    ventas_pos[i][2] = "31-02-2025"                                 # fecha imposible
for i in rng.choice(n_base, size=25, replace=False):
    ventas_pos.append(list(ventas_pos[int(i)]))                     # filas duplicadas exactas

for k in rng.choice(len(ordenes), size=round(len(ordenes) * 0.03), replace=False):
    ordenes[int(k)]["status"] = "RETURNED"
for k in rng.choice(len(ordenes), size=round(len(ordenes) * 0.02), replace=False):
    if ordenes[int(k)]["status"] == "PAID":
        ordenes[int(k)]["status"] = "CANCELLED"
for k in rng.choice(len(ordenes), size=3, replace=False):
    ordenes.append(json.loads(json.dumps(ordenes[int(k)])))        # órdenes repetidas (duplicado)

# ===================================================================== Inventario


def fecha_wms(d):
    return d.strftime("%d/%m/%Y") if random.random() < 0.02 else d.strftime("%Y-%m-%d")


COLS_INV = ["fecha", "id_sucursal", "sku", "stock_unidades", "unidades_merma"]
inv_filas = [[fecha_wms(d), s, k, st, m] for d, s, k, st, m in inventario]
n_inv = len(inv_filas)
orden_inv = [int(i) for i in rng.permutation(n_inv)]
for i in [orden_inv.pop() for _ in range(12)]:
    inv_filas[i][3] = -abs(inv_filas[i][3]) - 1                     # stock negativo (error del WMS)
for i in [orden_inv.pop() for _ in range(8)]:
    inv_filas[i][2] = inv_filas[i][2].lower()                       # SKU sin homologar
for i in [orden_inv.pop() for _ in range(5)]:
    inv_filas[i][1] = "S99"                                         # sucursal que no existe
for i in [orden_inv.pop() for _ in range(5)]:
    inv_filas[i][3] = ""                                            # stock vacío
for i in rng.choice(n_inv, size=6, replace=False):
    inv_filas.append(list(inv_filas[int(i)]))                       # fotos duplicadas (batch repetido)
# datos incompletos: el WMS no entregó 3 días de una sucursal
dias_perdidos = {(d.strftime("%Y-%m-%d"), "S04") for d in fechas[40:43]}
inv_filas = [f for f in inv_filas if (f[0], f[1]) not in dias_perdidos]

# ===================================================================== Campañas
COLS_CAMP = ["codigo_campana", "nombre_campana", "tipo_campana", "objetivo", "fecha_inicio", "fecha_fin",
             "presupuesto"]
camp_filas = [[c["cod"], c["nombre"], c["tipo"], c["objetivo"], c["envio"].isoformat(), c["fin"].isoformat(),
               c["presupuesto"]] for c in CAMPANAS]
camp_filas.append(list(camp_filas[1]))                                              # campaña repetida
camp_filas.append(["CMP-900", "Campaña de prueba", "Email", "Prueba", "2025-04-01", "2025-04-02", -1])  # inválida

COLS_CONT = ["codigo_campana", "rut", "canal", "fecha_envio", "sku_promocionado", "respondio"]
VARIANTES_CANAL = {"E-commerce": ["E-commerce", "E-commerce", "ecommerce", "Web"],
                   "Tienda física": ["Tienda física", "Tienda fisica", "TIENDA FÍSICA"]}
cont_filas = [[c["cod"], RUTS_VENTA[ic], random.choice(VARIANTES_CANAL[c["canal"]]), fmt_fecha(c["envio"]),
               variante_sku(sku), "SI" if resp else "NO"] for c, ic, sku, resp in CONTACTOS]
n_cont = len(cont_filas)
orden_c = [int(i) for i in rng.permutation(n_cont)]
for i in rng.choice(n_cont, size=8, replace=False):
    cont_filas.append(list(cont_filas[int(i)]))                                     # contacto repetido
for i in [orden_c.pop() for _ in range(5)]:
    cont_filas[i][1] = rut(31_000_000 + int(i) * 13, dv_mal=True)                   # RUT inválido
for j, i in enumerate([orden_c.pop() for _ in range(4)]):
    cont_filas[i][1] = rut(33_000_000 + j * 13)                                     # RUT válido sin ficha de cliente
for i in [orden_c.pop() for _ in range(3)]:
    cont_filas[i][0] = "CMP-999"                                                    # campaña que no existe
for i in [orden_c.pop() for _ in range(3)]:
    cont_filas[i][4] = "ZZ-999"                                                     # SKU que no existe

# ===================================================================== Escritura
print("Generando datos de ejemplo en", DESTINO)
DESTINO.mkdir(parents=True, exist_ok=True)
escribir_csv("geografia_snapshot_1.csv", COLS_GEO, geo1)
escribir_csv("geografia_snapshot_2.csv", COLS_GEO, geo2)
escribir_csv("sucursales.csv", ["id_sucursal", "nombre_sucursal", "tipo_tienda", "codigo_comuna"], SUCURSALES)
escribir_csv("productos_snapshot_1.csv", COLS_PROD, prod1)
escribir_csv("productos_snapshot_2.csv", COLS_PROD, prod2)
escribir_csv("clientes_snapshot_1.csv", COLS_CLI, cli1)
escribir_csv("clientes_snapshot_2.csv", COLS_CLI, cli2)
escribir_csv("ventas_pos.csv", COLS_POS, ventas_pos)
with open(DESTINO / "ventas_ecommerce.json", "w", encoding="utf-8") as f:
    json.dump(ordenes, f, ensure_ascii=False, indent=2)
print(f"  ventas_ecommerce.json: {len(ordenes)} órdenes")
escribir_csv("inventario_wms.csv", COLS_INV, inv_filas)
escribir_csv("campanas.csv", COLS_CAMP, camp_filas)
escribir_csv("campanas_contactos.csv", COLS_CONT, cont_filas)
