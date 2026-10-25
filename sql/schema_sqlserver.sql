-- DDL generado desde src/schema.py (no editar a mano: ejecutar scripts/exportar_schema_sql.py)
-- Base de datos: DataRetail360_DW (SQL Server)

CREATE TABLE auditoria_ejecuciones (
	ejecucion_id INTEGER NOT NULL IDENTITY, 
	proceso VARCHAR(50) NOT NULL, 
	inicio DATETIME NOT NULL, 
	fin DATETIME NULL, 
	estado VARCHAR(15) NOT NULL, 
	filas_leidas INTEGER NULL, 
	filas_cargadas INTEGER NULL, 
	filas_rechazadas INTEGER NULL, 
	mensaje VARCHAR(500) NULL, 
	PRIMARY KEY (ejecucion_id)
);

CREATE TABLE auditoria_rechazos (
	rechazo_id INTEGER NOT NULL IDENTITY, 
	proceso VARCHAR(50) NOT NULL, 
	origen_archivo VARCHAR(150) NOT NULL, 
	fila_origen INTEGER NOT NULL, 
	motivo_rechazo VARCHAR(100) NOT NULL, 
	detalle VARCHAR(250) NULL, 
	registrado_en DATETIME NOT NULL, 
	PRIMARY KEY (rechazo_id), 
	CONSTRAINT uq_rechazo UNIQUE (proceso, origen_archivo, fila_origen, motivo_rechazo)
);

CREATE TABLE dim_canal (
	canal_key INTEGER NOT NULL, 
	canal VARCHAR(40) NOT NULL, 
	tipo_canal VARCHAR(20) NULL, 
	PRIMARY KEY (canal_key), 
	UNIQUE (canal)
);

CREATE TABLE dim_fecha (
	fecha_key INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	dia INTEGER NULL, 
	mes INTEGER NULL, 
	nombre_mes VARCHAR(20) NULL, 
	trimestre INTEGER NULL, 
	anio INTEGER NULL, 
	dia_semana VARCHAR(15) NULL, 
	es_fin_de_semana INTEGER NULL, 
	PRIMARY KEY (fecha_key), 
	UNIQUE (fecha)
);

CREATE TABLE dim_geografia (
	geografia_key INTEGER NOT NULL, 
	codigo_comuna VARCHAR(10) NOT NULL, 
	comuna VARCHAR(80) NULL, 
	provincia VARCHAR(80) NULL, 
	region VARCHAR(80) NULL, 
	pais VARCHAR(40) NULL, 
	zona_comercial VARCHAR(30) NULL, 
	latitud FLOAT NULL, 
	longitud FLOAT NULL, 
	valido_desde DATE NOT NULL, 
	valido_hasta DATE NOT NULL, 
	es_actual INTEGER NOT NULL, 
	PRIMARY KEY (geografia_key), 
	CONSTRAINT uq_geografia_version UNIQUE (codigo_comuna, valido_desde)
);

CREATE INDEX ix_geografia_actual ON dim_geografia (codigo_comuna, es_actual);

CREATE TABLE dim_producto (
	producto_key INTEGER NOT NULL, 
	sku VARCHAR(30) NOT NULL, 
	nombre_producto VARCHAR(150) NULL, 
	marca VARCHAR(60) NULL, 
	categoria VARCHAR(60) NULL, 
	subcategoria VARCHAR(60) NULL, 
	linea_negocio VARCHAR(60) NULL, 
	valido_desde DATE NOT NULL, 
	valido_hasta DATE NOT NULL, 
	es_actual INTEGER NOT NULL, 
	PRIMARY KEY (producto_key), 
	CONSTRAINT uq_producto_version UNIQUE (sku, valido_desde)
);

CREATE INDEX ix_producto_actual ON dim_producto (sku, es_actual);

CREATE TABLE dim_cliente (
	cliente_key INTEGER NOT NULL, 
	rut_anonimizado VARCHAR(64) NOT NULL, 
	tramo_etario VARCHAR(20) NULL, 
	segmento VARCHAR(30) NULL, 
	codigo_comuna VARCHAR(10) NULL, 
	geografia_key INTEGER NULL, 
	fecha_primer_registro DATE NULL, 
	valido_desde DATE NOT NULL, 
	valido_hasta DATE NOT NULL, 
	es_actual INTEGER NOT NULL, 
	PRIMARY KEY (cliente_key), 
	CONSTRAINT uq_cliente_version UNIQUE (rut_anonimizado, valido_desde), 
	FOREIGN KEY(geografia_key) REFERENCES dim_geografia (geografia_key)
);

CREATE INDEX ix_cliente_actual ON dim_cliente (rut_anonimizado, es_actual);

CREATE TABLE dim_sucursal (
	sucursal_key INTEGER NOT NULL, 
	id_sucursal VARCHAR(10) NOT NULL, 
	nombre_sucursal VARCHAR(100) NULL, 
	tipo_tienda VARCHAR(40) NULL, 
	geografia_key INTEGER NULL, 
	PRIMARY KEY (sucursal_key), 
	UNIQUE (id_sucursal), 
	FOREIGN KEY(geografia_key) REFERENCES dim_geografia (geografia_key)
);

CREATE TABLE fact_ventas (
	id_transaccion VARCHAR(40) NOT NULL, 
	linea INTEGER NOT NULL, 
	fecha_key INTEGER NOT NULL, 
	producto_key INTEGER NOT NULL, 
	cliente_key INTEGER NOT NULL, 
	sucursal_key INTEGER NOT NULL, 
	canal_key INTEGER NOT NULL, 
	cantidad INTEGER NULL, 
	monto_neto NUMERIC(14, 2) NULL, 
	monto_iva NUMERIC(14, 2) NULL, 
	monto_total NUMERIC(14, 2) NULL, 
	devolucion INTEGER NOT NULL, 
	PRIMARY KEY (id_transaccion, linea), 
	FOREIGN KEY(fecha_key) REFERENCES dim_fecha (fecha_key), 
	FOREIGN KEY(producto_key) REFERENCES dim_producto (producto_key), 
	FOREIGN KEY(cliente_key) REFERENCES dim_cliente (cliente_key), 
	FOREIGN KEY(sucursal_key) REFERENCES dim_sucursal (sucursal_key), 
	FOREIGN KEY(canal_key) REFERENCES dim_canal (canal_key)
);
