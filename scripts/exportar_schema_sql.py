"""Genera sql/schema_sqlserver.sql (DDL de SQL Server) y sql/vistas_bi.sql (vistas de KPIs) a partir del código.

Sirve para revisar o crear las tablas desde SSMS. El pipeline también las crea solo
(`schema.crear_esquema`), así que este archivo es documentación verificable del modelo físico.

Uso:  python scripts/exportar_schema_sql.py
"""
import sys
from pathlib import Path

from sqlalchemy.dialects import mssql
from sqlalchemy.schema import CreateIndex, CreateTable

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import schema, vistas  # noqa: E402

dialecto = mssql.dialect()
dialecto.server_version_info = (15, 0, 0)   # SQL Server 2019: usa tipos DATE y DATETIME2 nativos
partes = ["-- DDL generado desde src/schema.py (no editar a mano: ejecutar scripts/exportar_schema_sql.py)",
          "-- Base de datos: DataRetail360_DW (SQL Server)\n"]
for tabla in schema.metadata.sorted_tables:
    partes.append(str(CreateTable(tabla).compile(dialect=dialecto)).strip() + ";\n")
    for indice in sorted(tabla.indexes, key=lambda i: i.name):
        partes.append(str(CreateIndex(indice).compile(dialect=dialecto)).strip() + ";\n")

destino = RAIZ / "sql" / "schema_sqlserver.sql"
destino.parent.mkdir(exist_ok=True)
destino.write_text("\n".join(partes), encoding="utf-8")
print(f"Escrito {destino.relative_to(RAIZ)} ({len(schema.metadata.tables)} tablas)")

destino_vistas = RAIZ / "sql" / "vistas_bi.sql"
destino_vistas.write_text(vistas.exportar_sql_server(), encoding="utf-8")
print(f"Escrito {destino_vistas.relative_to(RAIZ)} ({len(vistas.construir_vistas('mssql'))} vistas)")
