# Walena · Talento y Hospitalidad

Portal web para el seguimiento de egresados del Centro Industrial y de Energías
Alternativas del SENA Regional La Guajira. Está construido con Django y usa
SQLite en desarrollo.

## Puesta en marcha

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Ingresa a `http://127.0.0.1:8000/` para consultar la portada. El panel de
administración está en `/admin/`.

## Configuración de roles

Desde Django Admin, el superusuario debe crear los grupos `Administrador`,
`Administrativo`, `Funcionario`, `Egresado` y `Visor`, y asignar cada usuario al
grupo que corresponda. Para limitar un funcionario, crea su registro en
**Alcances de funcionarios** y asígnale los programas autorizados. Un
funcionario sin alcance asignado no puede consultar registros.

El catálogo de programas se administra en **Programas de formación**. El alta
de egresados requiere verificación de elegibilidad y autorización de tratamiento
de datos. La autenticación de egresados existentes se asocia a su ficha desde
Django Admin.

## Funcionalidades implementadas

- Inicio de sesión Django y autorización por grupos.
- Tablero agregado con estado de seguimiento, alertas de actualización y
  registros recientes.
- Registro, búsqueda, consulta, actualización y baja lógica del padrón.
- Historial inmutable de cambios de estado y seguimiento de intentos de contacto.
- Historial versionado, autogestión de datos de contacto y verificación
  institucional de la situación.
- Consulta pública, publicación y despublicación de oportunidades.
- Encuestas tipadas, respuestas voluntarias y análisis agregado.
- Emisión de certificaciones PDF con número, código público de verificación y
  anulación trazable.
- Reportes por alcance con exportación CSV; los visores reciben solo datos
  agregados.
- Bitácora de accesos a fichas, cambios, publicaciones y exportaciones.
- Interfaz adaptable a escritorio y móvil con la identidad visual de `docs/DESIGN.md`.

## Operación

Las ofertas vencidas dejan de aparecer en el sitio inmediatamente. Para marcar
su estado como despublicado en la base de datos, programa este comando una vez
al día en el servidor:

```powershell
python manage.py expire_opportunities
```

Antes de desplegar, configura `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` y
`DJANGO_DEBUG=False`. En producción habilita HTTPS; los ajustes de cookies
seguras y redirección HTTPS se activan automáticamente cuando `DEBUG` es falso.

Las pruebas se ejecutan con:

```powershell
python manage.py test
```
