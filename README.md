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
- `GET  /api/public/tribute-types`
- `GET  /api/public/tribute-types/<id>`
- `GET  /api/public/locations`
- `GET  /api/public/availability?tribute_type_id=&from=&to=&days=`
- `GET  /api/public/slots?tribute_type_id=&date=`
- `POST /api/public/appointments`
- `GET  /api/public/appointments/<code>?document=…`
- `POST /api/public/appointments/<code>/cancel`

### Administración (requiere sesión)
- `GET  /api/admin/auth/captcha`
- `POST /api/admin/auth/login`
- `POST /api/admin/auth/verify-2fa`
- `POST /api/admin/auth/logout`
- `GET  /api/admin/auth/me`
- `GET  /api/admin/dashboard`
- `GET  /api/admin/tribute-types`
- `POST /api/admin/tribute-types`
- `PATCH/DELETE /api/admin/tribute-types/<id>`
- `GET/POST /api/admin/availability/rules`
- `GET/PATCH/DELETE /api/admin/availability/rules/<id>`
- `POST /api/admin/availability/rules/<id>/generate-slots`
- `GET /api/admin/availability/slots`
- `PATCH/DELETE /api/admin/availability/slots/<id>`
- `POST /api/admin/availability/slots/bulk-generate`
- `POST /api/admin/availability/slots/block`
- `GET/POST /api/admin/availability/holidays`
- `DELETE /api/admin/availability/holidays/<id>`
- `GET/POST /api/admin/locations`
- `PATCH/DELETE /api/admin/locations/<id>`
- `GET /api/admin/appointments`
- `GET/PATCH /api/admin/appointments/<id>`
- `POST /api/admin/appointments/<id>/cancel`
- `POST /api/admin/appointments/<id>/reschedule`
- `GET /api/admin/appointments/status-options`
- `GET /api/admin/settings`
- `GET/PUT /api/admin/settings/<key>`

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

- **Overbooking**: el endpoint `POST /api/public/appointments` usa
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
flask create-bootstrap-admin    # usa BOOTSTRAP_ADMIN_*
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
