# Documento de Descripción Funcional ## Software Web para la Gestión de Egresados de Formación Titulada ### Centro Industrial y de Energías Alternativas – SENA Regional La Guajira 

**Versión:** 1.0 (borrador para validación) **Elaborado por:** Análisis de sistemas – Ingeniería de requisitos **Estado:** Para revisión y aprobación institucional **Convención:** Los elementos marcados con **[SUPUESTO]** corresponden a valores asumidos por ausencia de información explícita y deben validarse con la institución. 

## 1. Contexto 

### 1.1 Situación actual 

El Centro Industrial y de Energías Alternativas (CIEA) del SENA Regional La Guajira forma aprendices en programas de **formación titulada** (técnicos y tecnólogos) en áreas industriales, energías alternativas y afines. Al finalizar su proceso formativo, los aprendices se convierten en **egresados**, y el centro tiene la responsabilidad institucional de: 

- Realizar seguimiento a su trayectoria (vinculación laboral, emprendimiento, continuidad formativa). 

- Reportar indicadores de pertinencia y empleabilidad a nivel regional y nacional. - Mantener actualizada la información de contacto para encuestas y programas de bienestar. 

- Ofrecer servicios de intermediación laboral, orientación y certificaciones. 

En la actualidad **[SUPUESTO]**, esta gestión se realiza de forma dispersa: hojas de cálculo, correos electrónicos, formularios aislados y bases de datos personales de los funcionarios. Esto genera duplicidad de información, pérdida de contacto con egresados, baja tasa de respuesta en encuestas, imposibilidad de consolidar indicadores confiables y dificultad para cumplir con la normativa de protección de datos personales. 

# ### 1.2 Problema a resolver 

El software debe resolver la **dispersión, desactualización y baja trazabilidad** de la información de egresados, permitiendo: 

- Un repositorio único y centralizado de egresados. 

- Seguimiento periódico y verificable de su situación. 

- Generación automática de indicadores institucionales. 

- Cumplimiento de la normativa colombiana de tratamiento de datos personales. 

- Operación funcional en condiciones de **conectividad limitada** propias de la región. 

### 1.3 Objetivos del sistema 

# | # | Objetivo | 

# |---|----------| 

| O1 | Centralizar el registro de egresados de formación titulada del CIEA. | 

- | O2 | Automatizar el seguimiento periódico mediante encuestas y alertas. | 

- | O3 | Generar indicadores de empleabilidad, emprendimiento y continuidad formativa. | 

- | O4 | Garantizar el tratamiento lícito de datos personales (Ley 1581 de 2012 y Decreto 1377 de 2013). | 

- | O5 | Permitir autogestión del egresado sobre su propia información. | 

- | O6 | Operar con tolerancia a fallos de conectividad (modo offline / registro diferido) 

- **[SUPUESTO]**. | 

| O7 | Proveer información confiable para la toma de decisiones del centro y de la regional. | 

# ### 1.4 Alcance funcional 

- **Incluye:** 

- Registro y administración de egresados de formación titulada del CIEA. 

- Módulo de seguimiento (encuestas, actualización de datos, historial). 

- Gestión de estados del egresado. 

- Módulo de oportunidades (oferta laboral, emprendimiento, convocatorias). 

- Módulo de certificaciones y documentos. 

- Reportería e indicadores. 

- Administración de usuarios, roles y parametrización. 

- Módulo de notificaciones (correo/SMS) **[SUPUESTO]**. 

- Bitácora de auditoría. 

- **No incluye (fuera de alcance):** 

- Gestión académica de aprendices en formación (matrícula, notas). 

- Nómina o gestión de contratos laborales. 

- Integración transaccional con portales externos de empleo (solo enlaces y carga manual) 

- **[SUPUESTO]**. 

- Aplicaciones móviles nativas (se prevé diseño web responsive). 

# ### 1.5 Particularidades regionales a considerar 

- **Geografía dispersa:** municipios como Uribia, Manaure, Maicao, Dibulla y zonas rurales con baja cobertura. 

- **Conectividad intermitente:** el diseño debe soportar **registro diferido** y sincronización posterior. 

- **Diversidad cultural:** población wayuu y otros grupos étnicos; la interfaz debe ser clara, con posibilidad de **contenidos en lengua wayuunaiki** para mensajes clave **[SUPUESTO]**. 

- **Acceso a dispositivos:** predominio de uso móvil; se requiere **diseño responsive**. 

- **Identidad:** articulación con la política de inclusión y enfoque diferencial del SENA. 

## 2. Reglas de negocio 

> Todas las reglas son verificables y numeradas para trazabilidad con requisitos funcionales. 

**RN-01. Elegibilidad.** Solo se registra como egresado quien haya **culminado y aprobado** un programa de formación titulada del CIEA. El sistema debe validar contra el listado de certificados/actas de grado cargado por el administrativo **[SUPUESTO sobre fuente de validación]**. 

**RN-02. Unicidad.** Un egresado se identifica de forma única por su **número de documento de identidad**. No se permiten duplicados activos. Si se detecta un posible duplicado, el sistema lo marca para revisión del funcionario. 

**RN-03. Consentimiento.** El registro y tratamiento de datos requiere **autorización previa, expresa e informada** del egresado (Ley 1581 de 2012). Sin consentimiento registrado, el sistema solo puede almacenar datos mínimos para contacto y no puede usarlos para fines distintos. 

**RN-04. Estados del egresado.** Todo egresado debe tener **exactamente un estado vigente** entre: 

- `ACTIVO` (egresado localizable, sin vinculación reportada) 

- `VINCULADO_LABORAL` 

- `EMPRENDEDOR` 

- `CONTINUIDAD_FORMATIVA` **[SUPUESTO: se añade por pertinencia]** 

- `INACTIVO` (no localizable o sin respuesta tras N intentos) 

- `FALLECIDO` **[SUPUESTO: se añade por integridad del dato]** 

Los cambios de estado se registran con **fecha, usuario y justificación** (historial inmutable). 

**RN-05. Periodicidad de seguimiento.** El seguimiento debe realizarse **al menos cada 12 meses** por egresado **[SUPUESTO]**. El sistema genera alertas a los **11 meses** de la última actualización y marca al egresado como `INACTIVO` tras **2 intentos fallidos** de contacto documentados en un plazo de 60 días **[SUPUESTO]**. 

**RN-06. Actualización de datos.** El egresado puede actualizar sus propios datos de contacto y situación en cualquier momento. Los cambios quedan en **historial de versiones** con fecha y origen (autogestión o funcionario). 

**RN-07. Verificación.** Los datos actualizados por el egresado quedan en estado `PENDIENTE_VERIFICACION` hasta que un funcionario los valide **[SUPUESTO]**, salvo datos de contacto que se consideran válidos de inmediato. 

**RN-08. Protección de datos.** 

- Los datos personales solo se usan para los fines autorizados. 

- El acceso se rige por **mínimo privilegio** según rol. 

- Se registra **bitácora de auditoría** de todo acceso y modificación. 

- Se atienden derechos de **conocimiento, actualización, rectificación y supresión** (Ley 1581). 

- Los datos sensibles (p. ej., condición de discapacidad, pertenencia étnica) requieren consentimiento **explícito y separado** **[SUPUESTO]**. 

**RN-09. Retención.** Los datos se conservan mientras el egresado mantenga vínculo con el centro o hasta que solicite supresión, salvo obligación legal de conservación **[SUPUESTO: 5 años tras inactividad]**. 

**RN-10. Permisos por rol.** Ningún rol puede ejecutar acciones fuera de las definidas en la sección 3. El sistema deniega por defecto (deny-by-default). 

**RN-11. Encuestas.** Solo egresados con consentimiento vigente pueden ser incluidos en encuestas. La participación es **voluntaria**; una no respuesta no elimina al egresado del registro. 

**RN-12. Oportunidades.** Las ofertas laborales o de emprendimiento publicadas deben indicar **fuente, vigencia y responsable**. El sistema las despublica automáticamente al vencer. 

**RN-13. Certificaciones.** Solo el administrativo o funcionario autorizado puede emitir certificaciones. Toda emisión queda registrada con número único y código de verificación. 

**RN-14. Registro offline.** Los registros capturados sin conectividad se almacenan localmente y se sincronizan al restablecerse la conexión, respetando RN-02 (unicidad) y RN-04 (estado). 

**RN-15. Trazabilidad.** Toda operación crítica (crear, modificar, eliminar lógico, cambiar estado, emitir certificado) genera registro de auditoría con usuario, fecha, IP/dispositivo y valores anterior/nuevo. 

**RN-16. Baja lógica.** No se elimina físicamente información de egresados; se aplica **borrado lógico** con posibilidad de restauración por el administrativo **[SUPUESTO]**. 

## 3. Roles y permisos 

> Convención: **C** = Crear, **R** = Consultar, **U** = Actualizar, **D** = Eliminar (lógico), **—** = Sin acceso. 

### 3.1 Administrativo 

**Responsabilidades:** Gestión general del sistema, parametrización, administración de usuarios, generación de reportes institucionales y supervisión de la calidad del dato. 

**Funcionalidades permitidas:** 

- CRUD de usuarios y asignación de roles. 

- Parametrización de catálogos (programas, estados, tipos de vinculación, encuestas). 

- Carga masiva de egresados y certificados. 

- Emisión y anulación de certificaciones. 

- Gestión de encuestas y su publicación. 

- Generación de reportes institucionales y exportación. 

- Restauración de registros con baja lógica. 

- Consulta de bitácora de auditoría. 

# **Restricciones:** 

- No puede modificar datos de egresados sin dejar trazabilidad (RN-15). 

- No puede eliminar físicamente registros (RN-16). 

- Su acceso a datos sensibles se limita a lo necesario para su función (RN-08). 

# ### 3.2 Egresado 

**Responsabilidades:** Mantener actualizada su información y participar en el seguimiento. 

- **Funcionalidades permitidas:** 

- Consultar y actualizar su propia información (contacto, situación laboral, emprendimiento, formación). 

- Responder encuestas de seguimiento. 

- Consultar oferta laboral y oportunidades. 

- Consultar y descargar sus certificaciones. 

- Ejercer derechos de datos (solicitar actualización, rectificación o supresión). 

- Gestionar su consentimiento. 

**Restricciones:** 

- Solo accede a **su propio registro** (R/U limitado). - No puede cambiar su estado directamente; sus cambios quedan `PENDIENTE_VERIFICACION` (RN-07). 

- No puede consultar información de otros egresados. 

- No puede emitir certificaciones. 

# ### 3.3 Funcionario 

**Responsabilidades:** Registro y seguimiento operativo de egresados, gestión de encuestas y casos, generación de información de su área. 

**Funcionalidades permitidas:** 

- Registrar egresados (validando RN-01). 

- Actualizar y verificar datos de egresados de su área de competencia. 

- Gestionar casos de seguimiento y documentar intentos de contacto. 

- Crear y administrar encuestas de su área. 

- Cambiar estado del egresado con justificación (RN-04). 

- Consultar y generar reportes de su área. 

- Cargar información en modo offline y sincronizar (RN-14). 

**Restricciones:** 

- Acceso limitado a los egresados de **su área/programa** asignado **[SUPUESTO: alcance por área]**. 

- No administra usuarios ni parametrización global. - No puede anular certificaciones emitidas por el administrativo. - Sus cambios quedan auditados (RN-15). 

# ### 3.4 Visor 

**Responsabilidades:** Consulta de indicadores e información para toma de decisiones. Aplica a **coordinador académico** y **responsable de bienestar aprendiz**. 

**Funcionalidades permitidas:** - Consultar indicadores, tableros y reportes predefinidos. - Consultar información agregada de egresados según su función. - Exportar reportes de solo lectura. 

**Restricciones:** 

- **Solo lectura** (R); sin C/U/D. - Acceso restringido según su función (p. ej., coordinador académico ve su programa; bienestar ve indicadores agregados) **[SUPUESTO]**. - No accede a datos sensibles individuales salvo autorización expresa (RN-08). - No puede modificar parámetros ni usuarios. 

### 3.5 Matriz resumida de permisos 

| Módulo / Acción | Administrativo | Egresado | Funcionario | Visor | |---|:---:|:---:|:---:|:---:| | Usuarios y roles | CRUD | — | — | — | | Parametrización | CRUD | — | — | — | | Registro de egresados | CRUD | — | CRU | — | | Autogestión de datos propios | — | RU | — | — | | Cambio de estado | RU | — | RU | — | | Encuestas (gestión) | CRUD | R (responder) | CRU | R | | Oportunidades | CRUD | R | CRU | R | | Certificaciones | CRU/D | R | R | R | | Reportes institucionales | R | — | R (área) | R | | Auditoría | R | — | — | — | 

## 4. Requisitos funcionales 

> Cada módulo indica **propósito**, **entradas**, **procesamiento** y **salidas**. Numeración: RF-XX. 

### 4.1 Módulo de Autenticación y Gestión de Usuarios 

- **RF-01. Inicio de sesión.** *Propósito:* autenticar usuarios. *Entradas:* usuario/contraseña o documento. *Procesamiento:* validación de credenciales, control de intentos fallidos, segundo factor opcional **[SUPUESTO]**. *Salidas:* sesión activa, token, registro en auditoría. 

- **RF-02. Recuperación de contraseña.** *Entradas:* correo/documento. *Procesamiento:* envío de enlace temporal. *Salidas:* notificación y registro. 

- **RF-03. Gestión de usuarios.** *Entradas:* datos de usuario, rol. *Procesamiento:* CRUD con validación de unicidad y permisos. *Salidas:* usuario creado/actualizado, auditoría. - **RF-04. Asignación de roles y alcances.** *Entradas:* usuario, rol, área. *Procesamiento:* asignación según matriz de permisos. *Salidas:* permisos efectivos, auditoría. 

# ### 4.2 Módulo de Registro de Egresados 

- **RF-05. Registro individual.** *Propósito:* crear ficha de egresado. *Entradas:* documento, nombres, contacto, programa, fecha de grado, consentimiento. 

*Procesamiento:* validación RN-01, RN-02, RN-03; asignación de estado inicial `ACTIVO`. *Salidas:* ficha creada, código único, auditoría. 

- **RF-06. Carga masiva.** *Entradas:* archivo CSV/Excel con estructura definida. *Procesamiento:* validación por fila, detección de duplicados, reporte de errores. *Salidas:* registros creados y log de rechazos. 

- **RF-07. Búsqueda y consulta.** *Entradas:* criterios (documento, nombre, programa, estado, municipio). *Procesamiento:* filtrado según permisos del rol. *Salidas:* listado paginado y ficha detallada. 

- **RF-08. Baja lógica y restauración.** *Entradas:* identificador, motivo. *Procesamiento:* cambio de indicador de vigencia (RN-16). *Salidas:* registro marcado/restaurado, auditoría. 

# ### 4.3 Módulo de Seguimiento 

- **RF-09. Actualización de datos.** *Entradas:* datos modificados por egresado o funcionario. *Procesamiento:* versionado, estado `PENDIENTE_VERIFICACION` (RN-07). *Salidas:* nueva versión, historial. 

- **RF-10. Registro de intentos de contacto.** *Entradas:* fecha, medio, resultado, observación. *Procesamiento:* acumulación de intentos, evaluación de RN-05. *Salidas:* historial de contactos, alertas. 

- **RF-11. Cambio de estado.** *Entradas:* nuevo estado, justificación. *Procesamiento:* validación RN-04, registro de historial inmutable. *Salidas:* estado actualizado, auditoría. - **RF-12. Alertas de seguimiento.** *Procesamiento:* job programado que evalúa RN-05. *Salidas:* notificaciones a funcionarios y egresados. - **RF-13. Gestión de casos.** *Entradas:* caso (tipo, descripción, responsable). *Procesamiento:* asignación, seguimiento, cierre. *Salidas:* caso con trazabilidad. 

# ### 4.4 Módulo de Encuestas 

- **RF-14. Creación de encuestas.** *Entradas:* título, preguntas, tipos, vigencia, público objetivo. *Procesamiento:* validación de estructura y permisos. *Salidas:* encuesta publicada. 

- **RF-15. Aplicación de encuestas.** *Entradas:* respuestas del egresado. *Procesamiento:* validación de consentimiento (RN-11), registro de respuestas. *Salidas:* respuesta almacenada, actualización de indicadores. 

- **RF-16. Resultados y análisis.** *Procesamiento:* consolidación y estadísticas. *Salidas:* tableros y exportación. 

# ### 4.5 Módulo de Oportunidades 

- **RF-17. Publicación de ofertas.** *Entradas:* título, descripción, fuente, vigencia, responsable. *Procesamiento:* validación RN-12. *Salidas:* oferta publicada. - **RF-18. Consulta de oportunidades.** *Entradas:* filtros. *Procesamiento:* listado según vigencia y perfil. *Salidas:* detalle y enlace de postulación. - **RF-19. Despublicación automática.** *Procesamiento:* job al vencer vigencia (RN-12). *Salidas:* oferta despublicada. 

# ### 4.6 Módulo de Certificaciones 

- **RF-20. Emisión de certificación.** *Entradas:* egresado, tipo, motivo. *Procesamiento:* validación de permisos (RN-13), generación de número único y código de verificación. *Salidas:* documento PDF verificable, registro. - **RF-21. Verificación de certificados.** *Entradas:* código de verificación. *Procesamiento:* búsqueda y validación. *Salidas:* resultado de autenticidad. - **RF-22. Anulación.** *Entradas:* certificado, motivo. *Procesamiento:* cambio de estado a anulado (solo administrativo). *Salidas:* certificado invalidado, auditoría. 

# ### 4.7 Módulo de Reportería e Indicadores 

- **RF-23. Tablero de indicadores.** *Procesamiento:* cálculo de empleabilidad, emprendimiento, continuidad, inactivos, cobertura de seguimiento. *Salidas:* tableros por programa, área, municipio y periodo. 

- **RF-24. Reportes institucionales.** *Entradas:* filtros y formato. *Procesamiento:* generación según permisos. *Salidas:* PDF/Excel, registro de exportación. - **RF-25. Reportes de área.** *Procesamiento:* filtrado por alcance del funcionario/visor. *Salidas:* reportes restringidos. 

# ### 4.8 Módulo de Notificaciones 

- **RF-26. Notificaciones transaccionales.** *Entradas:* evento. *Procesamiento:* envío por correo/SMS **[SUPUESTO]**. *Salidas:* registro de envío y estado. 

- **RF-27. Plantillas de mensajes.** *Entradas:* contenido, idioma **[SUPUESTO: español/wayuunaiki]**. *Procesamiento:* parametrización. *Salidas:* plantillas disponibles. 

# ### 4.9 Módulo de Administración y Auditoría 

- **RF-28. Parametrización de catálogos.** *Entradas:* ítems de catálogo. *Procesamiento:* CRUD con validación. *Salidas:* catálogos actualizados. - **RF-29. Bitácora de auditoría.** *Procesamiento:* registro automático de operaciones críticas (RN-15). *Salidas:* consulta filtrable y exportación. 

- **RF-30. Gestión de consentimientos y derechos de datos.** *Entradas:* solicitud del egresado. *Procesamiento:* registro, trazabilidad y respuesta según Ley 1581. *Salidas:* constancia y actualización del consentimiento. 

### 4.10 Módulo de Operación Offline 

- **RF-31. Captura offline.** *Entradas:* registros capturados sin conexión. *Procesamiento:* almacenamiento local y cola de sincronización (RN-14). *Salidas:* registros pendientes. 

- **RF-32. Sincronización.** *Procesamiento:* envío al restablecer conexión, resolución de conflictos por reglas (RN-02, RN-04). *Salidas:* registros sincronizados y log de conflictos. 

## 5. Supuestos, restricciones y preguntas abiertas 

# ### 5.1 Supuestos 

| # | Supuesto | |---|----------| 

| S1 | La gestión actual es dispersa en hojas de cálculo y correos. | 

- | S2 | Existe un listado de certificados/actas de grado que sirve para validar elegibilidad (RN-01). | 

- | S3 | La periodicidad de seguimiento es de 12 meses con alertas a los 11 (RN-05). | 

- | S4 | Los cambios del egresado quedan pendientes de verificación (RN-07). | 

- | S5 | Se contempla estado `CONTINUIDAD_FORMATIVA` y `FALLECIDO` (RN-04). | 

- | S6 | Retención de datos: 5 años tras inactividad (RN-09). | 

| S7 | Se aplica baja lógica, no borrado físico (RN-16). | 

- | S8 | Se soporta operación offline con sincronización diferida (RF-31, RF-32). | 

- | S9 | Notificaciones por correo y SMS; interfaz en español con mensajes clave en wayuunaiki. | 

- | S10 | El alcance del funcionario se limita a su área/programa asignado. | 

- | S11 | Se requiere segundo factor de autenticación opcional (RF-01). | 

- | S12 | Los datos sensibles requieren consentimiento explícito y separado (RN-08). | 

- | S13 | Integración con portales externos de empleo solo por enlaces y carga manual. | 

# ### 5.2 Restricciones 

- **Normativas:** Ley 1581 de 2012, Decreto 1377 de 2013 y normas concordantes sobre protección de datos personales en Colombia; lineamientos del SENA sobre tratamiento de información de aprendices y egresados. 

- **Técnicas:** operación en conectividad intermitente; diseño responsive; compatibilidad con navegadores modernos **[SUPUESTO]**; almacenamiento seguro y cifrado de datos sensibles. 

- **Institucionales:** sujeción a la política de seguridad de la información del SENA; aprobación de la Oficina de Protección de Datos **[SUPUESTO]**. 

- **Culturales/regionales:** interfaz clara y accesible; consideración de enfoque diferencial y diversidad lingüística. 

### 5.3 Preguntas abiertas 

1. ¿Cuál es la fuente oficial para validar la elegibilidad del egresado (actas, certificados, sistema académico)? 

2. ¿Cuál es la periodicidad de seguimiento institucionalmente definida y los criterios exactos para marcar `INACTIVO`? 

3. ¿Se requiere integración con el sistema académico del SENA o con portales de empleo? ¿Con cuáles y bajo qué protocolo? 

4. ¿Qué datos se consideran sensibles y requieren consentimiento separado? 

5. ¿Cuál es la política de retención y borrado aprobada por la institución? 

6. ¿Se requiere soporte multiidioma (wayuunaiki) y en qué alcance? 

7. ¿Qué canales de notificación están disponibles y autorizados (correo institucional, SMS, WhatsApp)? 

8. ¿Cuál es el alcance exacto de acceso del rol Visor (coordinador académico vs. bienestar aprendiz)? 

9. ¿Se requiere firma electrónica o sello de verificación en certificaciones? 

10. ¿Cuáles son los indicadores oficiales que debe reportar el sistema y con qué periodicidad? 

11. ¿Existe un comité o responsable de validación de datos y de atención de derechos de datos? 

12. ¿Se requiere segundo factor de autenticación obligatorio para roles administrativos? 

**Fin del documento.** 

*Este documento constituye la línea base funcional para el equipo de desarrollo y debe ser validado con el CIEA – SENA Regional La Guajira antes de iniciar la implementación.* 

