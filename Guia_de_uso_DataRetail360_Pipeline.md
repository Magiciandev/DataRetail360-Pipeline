# Guía de Configuración y Ejecución — DataRetail360-Pipeline

Esta guía detalla el paso a paso para configurar el entorno, preparar la base de datos en SQL Server (tanto en instalaciones nuevas como al actualizar un modelado previo) y ejecutar el pipeline ETL completo.

## importante

## a partir del paso 4 e ve la conexion con la db, en caso de que trabajen a partir de

## la misma carpeta de antes, asi mismas variables de entorno (.env)

---

## 1. Requisitos Previos

- **Python 3.10+**
- **Microsoft SQL Server** (instancia local `MSSQLSERVER` o `SQLEXPRESS`)
- **Microsoft ODBC Driver 17 o 18 for SQL Server**

---

## 2. Configuración del Entorno Virtual

Abre una terminal de PowerShell en la raíz del proyecto y ejecuta:

```powershell
# Crear y activar el entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

---

## 3. Configurar Variables de Entorno (`.env`)

El archivo `.env` no se sube al repositorio, por lo que cada integrante debe crearlo en la raíz del proyecto (puedes partir de `.env.example` si existe).

### 3.1 Identificar tu instancia de SQL Server

Ejecuta en PowerShell:

```powershell
Get-Service -Name "*SQL*"
```

- Si el servicio activo se llama **`MSSQLSERVER`** (instancia por defecto), usa `DB_HOST=localhost`.
- Si el servicio activo se llama **`MSSQL$SQLEXPRESS`**, usa `DB_HOST=localhost\SQLEXPRESS`.

### 3.2 Ejemplo de `.env` recomendado (Autenticación de Windows)

```env
DB_ENGINE=sqlserver
DB_HOST=localhost
DB_NAME=DataRetail360_DW
DB_DRIVER=ODBC Driver 18 for SQL Server
DB_TRUSTED=True
```

> **Importante:** Usa siempre `localhost` (y no `127.0.0.1`) cuando `DB_TRUSTED=True`, ya que SQL Server suele rechazar la autenticación integrada de Windows si la conexión entra por dirección IP.

Para comprobar qué valores está leyendo Python:

```powershell
python -c "from src.config import get_settings; s = get_settings(); print(s.db_engine, '|', s.db_host, '|', s.db_name, '|', s.db_driver, '|', s.db_trusted)"
```

---

## 4. Preparación de SQL Server y Base de Datos

### 4.1 Verificar que el puerto TCP/IP (1433) esté escuchando

Ejecuta en PowerShell:

```powershell
Test-NetConnection -ComputerName localhost -Port 1433
```

Si **`TcpTestSucceeded`** devuelve **`False`**, habilita TCP/IP en SQL Server:

1. Abre **SQL Server Configuration Manager** (`Win + R` → `SQLServerManager15.msc` o `SQLServerManager16.msc`).
2. Ve a **SQL Server Network Configuration** → **Protocols for MSSQLSERVER** (o tu instancia).
3. Haz clic derecho en **TCP/IP** → **Enable**.
4. Haz doble clic en **TCP/IP** → pestaña **IP Addresses** → baja hasta **IPAll**, borra cualquier valor en _TCP Dynamic Ports_ y escribe `1433` en _TCP Port_.
5. Abre PowerShell **como Administrador** y reinicia el servicio:
   ```powershell
   Restart-Service -Name "MSSQLSERVER" -Force
   Start-Service -Name "SQLBrowser"
   ```

### 4.2 Crear o Reiniciar la Base de Datos `DataRetail360_DW`

> ⚠️ **Si ya tenías una versión anterior de `DataRetail360_DW` creada**, debes eliminarla y regenerarla desde cero para evitar conflictos con cambios en el modelado o en los tipos de datos.

El siguiente comando **elimina la base anterior (si existe)** cerrando conexiones activas y **crea `DataRetail360_DW` limpia** automáticamente usando los datos de tu `.env`:

```powershell
python -c "import pyodbc; from src.config import get_settings; s = get_settings(); conn = pyodbc.connect(f'DRIVER={{{s.db_driver}}};SERVER={s.db_host};DATABASE=master;Trusted_Connection=yes;TrustServerCertificate=yes;', autocommit=True); cur = conn.cursor(); cur.execute(\"IF DB_ID('DataRetail360_DW') IS NOT NULL BEGIN ALTER DATABASE DataRetail360_DW SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE DataRetail360_DW; END; CREATE DATABASE DataRetail360_DW;\"); print('Base de datos DataRetail360_DW lista OK')"
```

---

## 5. Creación del Esquema y Datos de Ejemplo

Una vez creada la base vacía, ejecuta los siguientes pasos en orden:

### Paso 1: Exportar el script DDL (opcional / respaldo)

Genera el archivo `sql\schema_sqlserver.sql` en disco (este script no modifica la base de datos):

```powershell
python scripts/exportar_schema_sql.py
```

### Paso 2: Crear las 12 tablas y sembrar los miembros `-1` (Desconocidos)

Crea la estructura completa en SQL Server e inserta los registros dummy (`-1`) requeridos por las dimensiones:

```powershell
python -c "from src import db, schema; e = db.get_engine(); schema.crear_esquema(e); print('Miembros -1 sembrados:', schema.sembrar_miembros_desconocidos(e))"
```

### Paso 3: Generar los archivos fuente de ejemplo

Crea los CSV y JSON de entrada en `data/sample/`:

```powershell
python scripts/generar_datos_ejemplo.py
```

---

## 6. Ejecución del Pipeline ETL

Lanza la orquestación completa de los notebooks de carga:

```powershell
python run_pipeline.py
```

### Notas sobre la salida en consola

- Durante la ejecución verás mensajes como `RuntimeWarning: Proactor event loop...` (de `zmq`) y `[IPKernelApp] WARNING | Kernel is running over TCP...`. **No son errores**; son avisos estándar de Jupyter/Papermill al levantar el kernel en Windows.
- Si el pipeline termina correctamente, verás `Pipeline completo OK` al final.
- Si algún notebook falla, revisa su versión ejecutada con la traza exacta del error en la carpeta `logs/ejecutados/`.

---

## 7. Solución de Problemas Frecuentes

| Error en Consola                                                                              | Causa                                                                                        | Solución                                                                                                                                        |
| :-------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| **`Error 4060`**: _Cannot open database "DataRetail360_DW"_                                   | La base de datos aún no existe en SQL Server.                                                | Ejecuta el comando del **Paso 4.2** para crearla desde `master`.                                                                                |
| **`Error 08001 / [53]`**: _Proveedor de canalizaciones con nombre / Tiempo de espera agotado_ | Instancia mal escrita en `.env`, servicio detenido o protocolo TCP/IP deshabilitado.         | Verifica `Get-Service "*SQL*"`, corrige `DB_HOST` (`localhost` vs `localhost\SQLEXPRESS`) y habilita TCP/IP en el puerto `1433` (**Paso 4.1**). |
| **`Error 18452`**: _Login failed. The login is from an untrusted domain_                      | Se usó `127.0.0.1` en lugar de `localhost` con Autenticación de Windows (`DB_TRUSTED=True`). | Cambia `DB_HOST=localhost` en el archivo `.env`.                                                                                                |
| **`Error IM002`**: _No se encuentra el nombre del origen de datos..._                         | El driver configurado en `DB_DRIVER` no coincide con el instalado en el equipo.              | Cambia `DB_DRIVER` en `.env` entre `ODBC Driver 17 for SQL Server` y `ODBC Driver 18 for SQL Server`.                                           |
