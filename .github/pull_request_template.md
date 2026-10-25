## ¿Qué cambia este PR?
<!-- Dimensión o módulo afectado y resumen en 2-3 líneas -->

## Checklist de code review (adaptada de la checklist 2.3.4 — contrástala con el documento original del curso)

**1. Funcionalidad**
- [ ] El notebook corre completo con *Restart & Run All* y sin errores
- [ ] Las dimensiones se cargan antes que los hechos; las claves sustitutas se asignan correctamente
- [ ] Los conteos finales cuadran (leídas = cargadas + rechazadas)

**2. Manejo de errores**
- [ ] Los errores se capturan y se registran; no hay `except:` vacíos ni fallas en silencio
- [ ] Se distingue lo recuperable (reintento) de lo fatal (detener el pipeline)

**3. Logging**
- [ ] Se usa `get_logger`, no `print`, para lo importante (inicio, fin, conteos, advertencias)
- [ ] Los logs y las salidas del notebook NO contienen RUT, correos ni otros datos personales

**4. Idempotencia**
- [ ] Ejecutar dos veces no duplica filas ni crea versiones SCD2 de más (probado)

**5. Validación de datos**
- [ ] Hay al menos 3 reglas de calidad; lo inválido va a `auditoria_rechazos` con su motivo
- [ ] La validación del notebook pasa (`chequear_scd2`, unicidad, nulos)

**6. Seguridad y secretos**
- [ ] No hay credenciales ni sal en el código; todo sale de `.env`
- [ ] `.env` y `data/` (salvo `data/sample`) siguen fuera de Git

**7. Legibilidad**
- [ ] Funciones cortas con una responsabilidad; nombres claros; sin código muerto ni celdas duplicadas

**8. Documentación y versionado**
- [ ] README y `docs/acuerdos_tecnicos.md` actualizados si cambió una decisión
- [ ] Commits pequeños con mensaje claro; el PR fue revisado por otro integrante

**9. Veredicto del revisor:** ☐ Aprobado ☐ Aprobado con cambios menores ☐ Requiere cambios
