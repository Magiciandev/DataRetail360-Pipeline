"""Genera los datos de ejemplo SINTÉTICOS de DataRetail 360 en data/sample/.

Son datos ficticios con problemas de calidad plantados a propósito (los mismos que
describió el caso: clientes duplicados, SKU sin homologar, ventas sin sucursal,
formatos de fecha dispares, montos inválidos). Los RUT son sintéticos (cuerpo > 30
millones, fuera del rango de personas reales) con dígito verificador válido.

Si el curso entrega archivos CSV/JSON oficiales, basta con reemplazarlos en
`data/sample/` (o apuntar `DATA_DIR` a otra carpeta) y adaptar las transformaciones.

Uso:  python scripts/generar_datos_ejemplo.py
"""
import csv
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.quality import calcular_dv  # noqa: E402

DESTINO = Path(__file__).resolve().parent.parent / "data" / "sample"
random.seed(42)


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
COLS_PROD = ["sku", "nombre_producto", "marca", "categoria", "subcategoria", "linea_negocio"]
PRECIOS = {p[0]: p[6] for p in PRODUCTOS + [NUEVO_PRODUCTO]}


def fila_prod(p, **cambios):
    f = dict(zip(COLS_PROD, p[:6]))
    f.update(cambios)
    return [f[c] for c in COLS_PROD]


prod1 = [fila_prod(p) for p in PRODUCTOS]
prod1[4][0] = " tv-004 "                              # SKU sin homologar
prod1.append(fila_prod(PRODUCTOS[5], sku="cf-005"))   # duplicado con otro formato
prod1.append(["", "Producto sin SKU", "Acme", "Tecnología", "", "Tecnología"])  # SKU vacío
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
for i in range(24):
    cuerpo = 31_000_000 + i * 13
    BASE.append({
        "cuerpo": cuerpo,
        "nombre": f"{NOMBRES[i % 10]} {APELLIDOS[(i * 3) % 10]}",
        "email": f"cliente{i:02d}@example.com",
        "comuna": COMUNAS[i % len(COMUNAS)],
        "segmento": SEGMENTOS[i % 3],
        "registro": date(2022, 1, 1) + timedelta(days=i * 37),
        "nacimiento": date(1960, 1, 1) + timedelta(days=i * 520),
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

# --------------------------------------------------------------------------- Ventas
INICIO, FIN = date(2025, 3, 3), date(2025, 7, 30)
DIAS = (FIN - INICIO).days
SKUS = [p[0] for p in PRODUCTOS] + ["MN-010"]
RUTS_VENTA = [rut(c["cuerpo"], con_puntos=(i % 3 == 0)) for i, c in enumerate(BASE)]


def fmt_fecha(d):
    r = random.random()
    if r < 0.70:
        return d.strftime("%d/%m/%Y")
    return d.strftime("%Y-%m-%d") if r < 0.90 else d.strftime("%Y/%m/%d")


def variante_sku(sku):
    r = random.random()
    return sku.lower() if r < 0.15 else f" {sku} " if r < 0.25 else sku


CANALES_POS = ["Tienda física"] * 6 + ["Tienda fisica", "TIENDA FÍSICA", "tienda física "]
ventas_pos = []
n_tx = 0
for t in range(1, 41):
    n_tx += 1
    d = INICIO + timedelta(days=random.randint(0, DIAS))
    id_tx = f"POS-{t:04d}"
    suc = random.choice(["S01", "S02", "S03", "S04", "S05", "S06"])
    cliente = random.choice(RUTS_VENTA) if random.random() > 0.15 else ""
    canal = random.choice(CANALES_POS)
    for linea in range(1, random.randint(1, 3) + 1):
        sku = random.choice(SKUS if d >= date(2025, 6, 1) else SKUS[:-1])
        qty = random.randint(1, 3)
        ventas_pos.append([id_tx, linea, fmt_fecha(d), variante_sku(sku), cliente, suc, canal,
                           qty, PRECIOS[sku] * qty, "OK"])
# ventas para ver el SCD2 de producto a ambos lados del 1 de junio
for k, (sku, d) in enumerate([("AU-002", date(2025, 4, 10)), ("AU-002", date(2025, 6, 20)),
                              ("CL-006", date(2025, 5, 5)), ("CL-006", date(2025, 6, 25))]):
    ventas_pos.append([f"POS-{41 + k:04d}", 1, fmt_fecha(d), sku, RUTS_VENTA[k], "S01", "Tienda física",
                       1, PRECIOS[sku], "OK"])
n_base = len(ventas_pos)
# --- problemas plantados
ventas_pos[3][5] = ""                                                  # sucursal vacía (índice 5 = id_sucursal)
ventas_pos[10][5] = ""                              # otra sucursal vacía
ventas_pos[7][8] = -abs(int(ventas_pos[7][8]))      # monto negativo con estado OK
ventas_pos[15][8] = -abs(int(ventas_pos[15][8]))
ventas_pos[20][9] = "DEVUELTA"                      # devolución
ventas_pos[25][9] = "DEVUELTA"
ventas_pos[30][9] = "ANULADA"                       # venta anulada
ventas_pos[12][3] = "ZZ-999"                        # SKU que no existe en el catálogo
ventas_pos[18][2] = "31-02-2025"                    # fecha imposible
ventas_pos.append(list(ventas_pos[5]))              # fila duplicada exacta
ventas_pos.append(list(ventas_pos[22]))             # otra duplicada exacta
COLS_POS = ["id_transaccion", "linea", "fecha", "sku", "rut", "id_sucursal", "canal", "cantidad", "monto", "estado"]

ordenes = []
for e in range(1, 13):
    d = INICIO + timedelta(days=random.randint(0, DIAS))
    hora = f"{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"
    items = []
    for _ in range(random.randint(1, 3)):
        sku = random.choice(SKUS if d >= date(2025, 6, 1) else SKUS[:-1])
        qty = random.randint(1, 2)
        items.append({"sku": variante_sku(sku), "qty": qty, "line_total": PRECIOS[sku] * qty})
    ordenes.append({
        "order_id": f"EC-{1000 + e}", "created_at": f"{d.isoformat()}T{hora}Z",
        "channel": random.choice(["E-commerce", "E-commerce", "ecommerce", "Web"]),
        "status": "RETURNED" if e == 4 else "CANCELLED" if e == 8 else "PAID",
        "customer": {"rut": random.choice(RUTS_VENTA), "email": f"web{e}@example.com"},
        "items": items,
    })
ordenes.append(json.loads(json.dumps(ordenes[1])))  # orden repetida (duplicado)

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
