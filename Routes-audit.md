# Auditoría de rutas

Generado: 2026-08-05 01:20
Fuente de las rutas: url_map de Flask (autoritativo)
Constantes leídas de `admin.js`: `API_BASE_URL = '/admin/api'`, `PUBLIC_API_BASE_URL = '/api/v1/public'`

## Resumen

- Rutas declaradas en el servidor: **81**
- Llamadas encontradas en la interfaz: **43**
- Llamadas con problema: **0**

## Llamadas de la interfaz con problema

Ninguno. Todas las llamadas de la interfaz coinciden con una ruta real.

## Todas las llamadas de la interfaz

| Archivo:línea | Llamada | Método | URL resuelta | Ruta que matchea | Estado |
|---|---|---|---|---|---|
| `app/templates/admin/appointment_create.html:149` | `public/tribute-types` | GET | `/api/v1/public/tribute-types` | `/api/v1/public/tribute-types` | OK |
| `app/templates/admin/appointment_create.html:171` | `public/availability?tribute_type_id=` | GET | `/api/v1/public/availability?tribute_type_id=` | `/api/v1/public/availability` | OK |
| `app/templates/admin/appointment_create.html:191` | `public/slots?tribute_type_id=` | GET | `/api/v1/public/slots?tribute_type_id=` | `/api/v1/public/slots` | OK |
| `app/templates/admin/appointment_create.html:304` | `public/appointments` | POST | `/api/v1/public/appointments` | `/api/v1/public/appointments` | OK |
| `app/templates/admin/appointments.html:221` | `admin/appointments?` | GET | `/admin/api/appointments?` | `/admin/api/appointments` | OK |
| `app/templates/admin/appointments.html:245` | `admin/appointments/status-options` | GET | `/admin/api/appointments/status-options` | `/admin/api/appointments/status-options` | OK |
| `app/templates/admin/appointments.html:246` | `admin/tribute-types?per_page=200` | GET | `/admin/api/tribute-types?per_page=200` | `/admin/api/tribute-types` | OK |
| `app/templates/admin/appointments.html:285` | `admin/appointments/<id>` | GET | `/admin/api/appointments/<id>` | `/admin/api/appointments/<int:appointment_id>` | OK |
| `app/templates/admin/appointments.html:308` | `public/availability?tribute_type_id=` | GET | `/api/v1/public/availability?tribute_type_id=` | `/api/v1/public/availability` | OK |
| `app/templates/admin/appointments.html:330` | `public/slots?tribute_type_id=` | GET | `/api/v1/public/slots?tribute_type_id=` | `/api/v1/public/slots` | OK |
| `app/templates/admin/appointments.html:369` | `admin/appointments/<id>` | PATCH | `/admin/api/appointments/<id>` | `/admin/api/appointments/<int:appointment_id>` | OK |
| `app/templates/admin/appointments.html:384` | `admin/appointments/<id>/cancel` | POST | `/admin/api/appointments/<id>/cancel` | `/admin/api/appointments/<int:appointment_id>/cancel` | OK |
| `app/templates/admin/appointments.html:400` | `admin/appointments/<id>/reschedule` | POST | `/admin/api/appointments/<id>/reschedule` | `/admin/api/appointments/<int:appointment_id>/reschedule` | OK |
| `app/templates/admin/availability.html:381` | `admin/tribute-types?per_page=200&include_inactive=true` | GET | `/admin/api/tribute-types?per_page=200&include_inactive=true` | `/admin/api/tribute-types` | OK |
| `app/templates/admin/availability.html:382` | `admin/locations` | GET | `/admin/api/locations` | `/admin/api/locations` | OK |
| `app/templates/admin/availability.html:438` | `admin/availability/slots?` | GET | `/admin/api/availability/slots?` | `/admin/api/availability/slots` | OK |
| `app/templates/admin/availability.html:505` | `admin/availability/slots/<id>` | PATCH | `/admin/api/availability/slots/<id>` | `/admin/api/availability/slots/<int:slot_id>` | OK |
| `app/templates/admin/availability.html:519` | `admin/availability/slots/<id>` | PATCH | `/admin/api/availability/slots/<id>` | `/admin/api/availability/slots/<int:slot_id>` | OK |
| `app/templates/admin/availability.html:559` | `admin/availability/slots/<id>` | DELETE | `/admin/api/availability/slots/<id>` | `/admin/api/availability/slots/<int:slot_id>` | OK |
| `app/templates/admin/availability.html:704` | `admin/availability/slots/bulk-generate` | POST | `/admin/api/availability/slots/bulk-generate` | `/admin/api/availability/slots/bulk-generate` | OK |
| `app/templates/admin/availability.html:773` | `admin/availability/slots/bulk-delete` | POST | `/admin/api/availability/slots/bulk-delete` | `/admin/api/availability/slots/bulk-delete` | OK |
| `app/templates/admin/availability.html:800` | `admin/availability/slots/bulk-delete` | POST | `/admin/api/availability/slots/bulk-delete` | `/admin/api/availability/slots/bulk-delete` | OK |
| `app/templates/admin/availability.html:820` | `admin/availability/rules?per_page=200` | GET | `/admin/api/availability/rules?per_page=200` | `/admin/api/availability/rules` | OK |
| `app/templates/admin/availability.html:933` | `admin/availability/rules/<id>/generate-slots` | POST | `/admin/api/availability/rules/<id>/generate-slots` | `/admin/api/availability/rules/<int:rule_id>/generate-slots` | OK |
| `app/templates/admin/availability.html:946` | `admin/availability/rules/<id>` | DELETE | `/admin/api/availability/rules/<id>` | `/admin/api/availability/rules/<int:rule_id>` | OK |
| `app/templates/admin/availability.html:967` | `admin/availability/slots/block` | POST | `/admin/api/availability/slots/block` | `/admin/api/availability/slots/block` | OK |
| `app/templates/admin/availability.html:982` | `admin/availability/holidays` | GET | `/admin/api/availability/holidays` | `/admin/api/availability/holidays` | OK |
| `app/templates/admin/availability.html:1013` | `admin/availability/holidays` | POST | `/admin/api/availability/holidays` | `/admin/api/availability/holidays` | OK |
| `app/templates/admin/availability.html:1026` | `admin/availability/holidays/<id>` | DELETE | `/admin/api/availability/holidays/<id>` | `/admin/api/availability/holidays/<int:holiday_id>` | OK |
| `app/templates/admin/dashboard.html:175` | `admin/dashboard` | GET | `/admin/api/dashboard` | `/admin/api/dashboard` | OK |
| `app/templates/admin/locations.html:191` | `admin/locations` | GET | `/admin/api/locations` | `/admin/api/locations` | OK |
| `app/templates/admin/locations.html:237` | `admin/locations/<id>` | DELETE | `/admin/api/locations/<id>` | `/admin/api/locations/<int:location_id>` | OK |
| `app/templates/admin/login.html:143` | `admin/auth/captcha` | GET | `/admin/api/auth/captcha` | `/admin/api/auth/captcha` | OK |
| `app/templates/admin/login.html:170` | `admin/auth/login` | POST | `/admin/api/auth/login` | `/admin/api/auth/login` | OK |
| `app/templates/admin/login.html:193` | `admin/auth/verify-2fa` | POST | `/admin/api/auth/verify-2fa` | `/admin/api/auth/verify-2fa` | OK |
| `app/templates/admin/logs.html:7` | `admin/access/activity-logs.csv` | GET | `/admin/api/access/activity-logs.csv` | `/admin/api/access/activity-logs.csv` | OK |
| `app/templates/admin/logs.html:28` | `admin/access/activity-logs?per_page=100` | GET | `/admin/api/access/activity-logs?per_page=100` | `/admin/api/access/activity-logs` | OK |
| `app/templates/admin/tribute_types.html:267` | `admin/tribute-types?per_page=200&include_inactive=true` | GET | `/admin/api/tribute-types?per_page=200&include_inactive=true` | `/admin/api/tribute-types` | OK |
| `app/templates/admin/tribute_types.html:324` | `admin/tribute-types/<id>` | DELETE | `/admin/api/tribute-types/<id>` | `/admin/api/tribute-types/<int:tribute_id>` | OK |
| `app/templates/admin/users.html:45` | `admin/access/users?per_page=100` | GET | `/admin/api/access/users?per_page=100` | `/admin/api/access/users` | OK |
| `app/templates/admin/users.html:68` | `admin/access/users/<id>` | DELETE | `/admin/api/access/users/<id>` | `/admin/api/access/users/<int:user_id>` | OK |
| `app/templates/admin/users.html:123` | `admin/access/users/<id>` | PATCH | `/admin/api/access/users/<id>` | `/admin/api/access/users/<int:user_id>` | OK |
| `app/templates/admin/users.html:125` | `admin/access/users` | POST | `/admin/api/access/users` | `/admin/api/access/users` | OK |

## Rutas del servidor que la interfaz nunca llama

No es necesariamente un error: puede ser API para el visualizer, el portal público o uso externo.

| Ruta | Métodos | Blueprint |
|---|---|---|
| `/admin` | GET | `admin_ui` |
| `/admin/api/access/users/<int:user_id>/password` | PATCH | `admin_access` |
| `/admin/api/auth/csrf-token` | GET | `admin_auth` |
| `/admin/api/auth/logout` | POST | `admin_auth` |
| `/admin/api/auth/me` | GET | `admin_auth` |
| `/admin/api/dashboard/today` | GET | `admin_dashboard` |
| `/admin/api/health` | GET | `admin_dashboard` |
| `/admin/api/tickets` | GET | `admin_tickets` |
| `/admin/api/tickets/<int:ticket_id>` | GET | `admin_tickets` |
| `/admin/api/tickets/<int:ticket_id>/history` | GET | `admin_tickets` |
| `/admin/api/tickets/<int:ticket_id>/status` | PATCH | `admin_tickets` |
| `/admin/api/tickets/current-hour` | GET | `admin_tickets` |
| `/admin/disponibilidad` | GET | `admin_ui` |
| `/admin/login` | GET | `admin_ui` |
| `/admin/logs` | GET | `admin_ui` |
| `/admin/registrar-turno` | GET | `admin_ui` |
| `/admin/sedes` | GET | `admin_ui` |
| `/admin/tributos` | GET | `admin_ui` |
| `/admin/turnos` | GET | `admin_ui` |
| `/admin/usuarios` | GET | `admin_ui` |
| `/api/v1/admin/auth/login` | POST | `dashboard_auth` |
| `/api/v1/admin/auth/logout` | POST | `dashboard_auth` |
| `/api/v1/admin/auth/me` | GET | `dashboard_auth` |
| `/api/v1/admin/auth/resend-2fa` | POST | `dashboard_auth` |
| `/api/v1/admin/auth/verify-2fa` | POST | `dashboard_auth` |
| `/api/v1/admin/dashboard/today` | GET | `dashboard_api` |
| `/api/v1/admin/tickets` | GET | `dashboard_api` |
| `/api/v1/admin/tickets/<int:ticket_id>` | GET | `dashboard_api` |
| `/api/v1/admin/tickets/<int:ticket_id>/history` | GET | `dashboard_api` |
| `/api/v1/admin/tickets/<int:ticket_id>/status` | PATCH | `dashboard_api` |
| `/api/v1/admin/tickets/current-hour` | GET | `dashboard_api` |
| `/api/v1/public/appointments/<string:code>` | GET | `public_api` |
| `/api/v1/public/appointments/<string:code>/cancel` | POST | `public_api` |
| `/api/v1/public/locations` | GET | `public_api` |
| `/api/v1/public/tribute-types/<int:tribute_id>` | GET | `public_api` |
| `/healthz` | GET | `(app)` |
| `/static/<path:filename>` | GET | `(app)` |

## Todas las rutas declaradas

### `(app)`

| Ruta | Métodos |
|---|---|
| `/healthz` | GET |
| `/static/<path:filename>` | GET |

### `admin_access`

| Ruta | Métodos |
|---|---|
| `/admin/api/access/activity-logs` | GET |
| `/admin/api/access/activity-logs.csv` | GET |
| `/admin/api/access/users` | GET |
| `/admin/api/access/users` | POST |
| `/admin/api/access/users/<int:user_id>` | PATCH |
| `/admin/api/access/users/<int:user_id>` | DELETE |
| `/admin/api/access/users/<int:user_id>/password` | PATCH |

### `admin_appointments`

| Ruta | Métodos |
|---|---|
| `/admin/api/appointments` | GET |
| `/admin/api/appointments/<int:appointment_id>` | GET |
| `/admin/api/appointments/<int:appointment_id>` | PATCH |
| `/admin/api/appointments/<int:appointment_id>/cancel` | POST |
| `/admin/api/appointments/<int:appointment_id>/reschedule` | POST |
| `/admin/api/appointments/status-options` | GET |

### `admin_auth`

| Ruta | Métodos |
|---|---|
| `/admin/api/auth/captcha` | GET |
| `/admin/api/auth/csrf-token` | GET |
| `/admin/api/auth/login` | POST |
| `/admin/api/auth/logout` | POST |
| `/admin/api/auth/me` | GET |
| `/admin/api/auth/verify-2fa` | POST |

### `admin_availability`

| Ruta | Métodos |
|---|---|
| `/admin/api/availability/holidays` | GET |
| `/admin/api/availability/holidays` | POST |
| `/admin/api/availability/holidays/<int:holiday_id>` | DELETE |
| `/admin/api/availability/rules` | GET |
| `/admin/api/availability/rules` | POST |
| `/admin/api/availability/rules/<int:rule_id>` | GET |
| `/admin/api/availability/rules/<int:rule_id>` | PATCH |
| `/admin/api/availability/rules/<int:rule_id>` | DELETE |
| `/admin/api/availability/rules/<int:rule_id>/generate-slots` | POST |
| `/admin/api/availability/slots` | GET |
| `/admin/api/availability/slots/<int:slot_id>` | PATCH |
| `/admin/api/availability/slots/<int:slot_id>` | DELETE |
| `/admin/api/availability/slots/block` | POST |
| `/admin/api/availability/slots/bulk-delete` | POST |
| `/admin/api/availability/slots/bulk-generate` | POST |

### `admin_dashboard`

| Ruta | Métodos |
|---|---|
| `/admin/api/dashboard` | GET |
| `/admin/api/dashboard/today` | GET |
| `/admin/api/health` | GET |

### `admin_locations`

| Ruta | Métodos |
|---|---|
| `/admin/api/locations` | GET |
| `/admin/api/locations` | POST |
| `/admin/api/locations/<int:location_id>` | PATCH |
| `/admin/api/locations/<int:location_id>` | DELETE |

### `admin_tickets`

| Ruta | Métodos |
|---|---|
| `/admin/api/tickets` | GET |
| `/admin/api/tickets/<int:ticket_id>` | GET |
| `/admin/api/tickets/<int:ticket_id>/history` | GET |
| `/admin/api/tickets/<int:ticket_id>/status` | PATCH |
| `/admin/api/tickets/current-hour` | GET |

### `admin_tribute_types`

| Ruta | Métodos |
|---|---|
| `/admin/api/tribute-types` | GET |
| `/admin/api/tribute-types` | POST |
| `/admin/api/tribute-types/<int:tribute_id>` | GET |
| `/admin/api/tribute-types/<int:tribute_id>` | PATCH |
| `/admin/api/tribute-types/<int:tribute_id>` | DELETE |

### `admin_ui`

| Ruta | Métodos |
|---|---|
| `/admin` | GET |
| `/admin/disponibilidad` | GET |
| `/admin/login` | GET |
| `/admin/logs` | GET |
| `/admin/registrar-turno` | GET |
| `/admin/sedes` | GET |
| `/admin/tributos` | GET |
| `/admin/turnos` | GET |
| `/admin/usuarios` | GET |

### `dashboard_api`

| Ruta | Métodos |
|---|---|
| `/api/v1/admin/dashboard/today` | GET |
| `/api/v1/admin/tickets` | GET |
| `/api/v1/admin/tickets/<int:ticket_id>` | GET |
| `/api/v1/admin/tickets/<int:ticket_id>/history` | GET |
| `/api/v1/admin/tickets/<int:ticket_id>/status` | PATCH |
| `/api/v1/admin/tickets/current-hour` | GET |

### `dashboard_auth`

| Ruta | Métodos |
|---|---|
| `/api/v1/admin/auth/login` | POST |
| `/api/v1/admin/auth/logout` | POST |
| `/api/v1/admin/auth/me` | GET |
| `/api/v1/admin/auth/resend-2fa` | POST |
| `/api/v1/admin/auth/verify-2fa` | POST |

### `public_api`

| Ruta | Métodos |
|---|---|
| `/api/v1/public/appointments` | POST |
| `/api/v1/public/appointments/<string:code>` | GET |
| `/api/v1/public/appointments/<string:code>/cancel` | POST |
| `/api/v1/public/availability` | GET |
| `/api/v1/public/locations` | GET |
| `/api/v1/public/slots` | GET |
| `/api/v1/public/tribute-types` | GET |
| `/api/v1/public/tribute-types/<int:tribute_id>` | GET |
