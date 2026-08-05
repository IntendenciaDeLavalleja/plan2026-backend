# Backend — Amnistía Financiera (Flask)

API REST para la agenda electrónica de la Amnistía Financiera de la
Intendencia de Lavalleja. Incluye autenticación administrativa con doble
factor, gestión de tributos, disponibilidad, turnos y configuración general.

## Requisitos

- Python 3.11+
- MariaDB / MySQL (o SQLite para desarrollo)
- pip + virtualenv

## Puesta en marcha

```bash
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Copiar `.env.example` (ver `README.md` raíz) a `.env` y completar los datos
reales (DB, SMTP, etc.).

```bash
flask db upgrade
flask seed-data --force
flask create-admin <user> <email> <password> true
flask run
```

## Endpoints

### Públicos
- `GET  /api/v1/public/tribute-types`
- `GET  /api/v1/public/tribute-types/<id>`
- `GET  /api/v1/public/locations`
- `GET  /api/v1/public/availability?tribute_type_id=&from=&to=&days=`
- `GET  /api/v1/public/slots?tribute_type_id=&date=`
- `POST /api/v1/public/appointments`
- `GET  /api/v1/public/appointments/<code>?document=…`
- `POST /api/v1/public/appointments/<code>/cancel`

### Administración (requiere sesión)
- `GET  /api/v1/admin/auth/captcha`
- `POST /api/v1/admin/auth/login`
- `POST /api/v1/admin/auth/verify-2fa`
- `POST /api/v1/admin/auth/logout`
- `GET  /api/v1/admin/auth/me`
- `GET  /api/v1/admin/dashboard`
- `GET  /api/v1/admin/tribute-types`
- `POST /api/v1/admin/tribute-types`
- `PATCH/DELETE /api/v1/admin/tribute-types/<id>`
- `GET/POST /api/v1/admin/availability/rules`
- `GET/PATCH/DELETE /api/v1/admin/availability/rules/<id>`
- `POST /api/v1/admin/availability/rules/<id>/generate-slots`
- `GET /api/v1/admin/availability/slots`
- `PATCH/DELETE /api/v1/admin/availability/slots/<id>`
- `POST /api/v1/admin/availability/slots/bulk-generate`
- `POST /api/v1/admin/availability/slots/block`
- `GET/POST /api/v1/admin/availability/holidays`
- `DELETE /api/v1/admin/availability/holidays/<id>`
- `GET/POST /api/v1/admin/locations`
- `PATCH/DELETE /api/v1/admin/locations/<id>`
- `GET /api/v1/admin/appointments`
- `GET/PATCH /api/v1/admin/appointments/<id>`
- `POST /api/v1/admin/appointments/<id>/cancel`
- `POST /api/v1/admin/appointments/<id>/reschedule`
- `GET /api/v1/admin/appointments/status-options`

## Modelos principales

- `AdminUser` — usuarios administradores (Argon2 + 2FA)
- `TwoFactorCode` — códigos 2FA de un solo uso hasheados
- `ActivityLog` — auditoría de acciones administrativas
- `TributeType` — tipos de tributo / adeudo administrables
- `Location` — sedes donde se atiende
- `AvailabilityRule` — reglas recurrentes de disponibilidad
- `AppointmentSlot` — slots concretos disponibles para reservar
- `HolidayOrBlockedDay` — feriados o días bloqueados
- `Appointment` — reservas de vecinos

## Reglas de negocio críticas

- **Overbooking**: el endpoint `POST /api/v1/public/appointments` usa
  `SELECT … FOR UPDATE` + incremento atómico de `reserved_count` para
  impedir que dos vecinos obtengan el mismo turno.
- **Anticipación**: configurable vía `min_anticipation_hours` y
  `MAX_ANTICIPATION_DAYS` en la configuración de la aplicación.
- **Cupo por documento**: `max_reservations_per_document` limita cuántas
  reservas activas puede tener una misma cédula.
- **Códigos amigables**: generados con `IDL-AF-{año}-{6 caracteres sin
  ambigüedades}`. El sufijo es único y se valida con un índice único.
- **Soft delete**: los tributos con historial se desactivan en lugar de
  eliminarse, preservando la trazabilidad de las reservas.

## CLI

```bash
flask create-admin <user> <email> <password> <true|false>
flask reset-admin-password <user> <new>
flask init-db
flask seed-data [--force]
flask routes
flask db migrate -m "..."
flask db upgrade
```

Los superadministradores gestionan usuarios desde `/admin/usuarios`, donde
pueden crear cuentas, editar sus datos completos (incluida la contraseña, rol y
estado) y eliminar otros administradores.
También consultan la actividad completa desde `/admin/logs` y pueden descargarla
en CSV. Estas áreas están protegidas también en la API y responden `403` a los
administradores comunes.
