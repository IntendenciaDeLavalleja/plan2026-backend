# Configuración del Backend - Guía de Replicación

Este documento detalla la arquitectura, tecnologías y pasos necesarios para replicar la estructura de este backend en otros proyectos con necesidades similares (gestión de archivos en MinIO, base de datos MariaDB, seguridad robusta y servicios de correo).

## 🚀 Tecnologías Principales

- **Lenguaje:** Python 3.x
- **Framework Web:** [Flask](https://flask.palletsprojects.com/)
- **Base de Datos:** MariaDB (usando `mariadb` driver y `Flask-SQLAlchemy`)
- **Gestión de Migraciones:** `Flask-Migrate` (Alembic)
- **Almacenamiento de Objetos:** [MinIO](https://min.io/) (S3 compatible)
- **Seguridad:**
  - `Argon2` (Hashing de contraseñas)
  - `Flask-Talisman` (Seguridad de headers HTTP/CSP)
  - `Flask-Limiter` (Rate limiting)
  - `CSRFProtect` (Protección contra CSRF)
  - `Bleach` (Sanitización de HTML)
- **Validación y Serialización:** `Marshmallow` / `Flask-Marshmallow`
- **Formularios:** `Flask-WTF`
- **Envío de Correos:** `Flask-Mail`

## 📂 Estructura del Proyecto

El backend sigue el **Application Factory Pattern** de Flask para facilitar la escalabilidad y las pruebas.

```text
backend/
├── app/
│   ├── __init__.py          # Fábrica de la aplicación (create_app)
│   ├── config.py            # Configuraciones (Dev/Prod)
│   ├── extensions.py        # Inicialización de extensiones (db, mail, etc.)
│   ├── commands.py          # Comandos CLI (crear admin, inicializar buckets)
│   ├── models/              # Modelos de SQLAlchemy
│   ├── routes/              # Blueprints (public, admin)
│   ├── services/            # Lógica de negocio/integraciones (MinioService, MailService)
│   ├── schemas/             # Esquemas Marshmallow (validación API)
│   ├── forms/               # Formularios WTForms (validación server-side)
│   ├── static/              # Archivos estáticos
│   └── templates/           # Plantillas Jinja2 (Emails y páginas Admin)
├── migrations/              # Scripts de migración de base de datos
├── tests/                   # Pruebas unitarias y de integración
├── manage.py                # Punto de entrada para comandos
└── requirements.txt         # Dependencias del proyecto
```

## 🛠️ Instrucciones de Replicación

### 1. Preparación del Entorno
Clonar la estructura o crear una similar. Se recomienda usar un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
```

Instalar dependencias:
```bash
pip install -r requirements.txt
```

### 2. Configuración de Variables de Entorno (`.env`)
Crear un archivo `.env` en la raíz del backend con los siguientes parámetros obligatorios:

```env
# Flask
SECRET_KEY=tu_clave_secreta_muy_larga
FLASK_APP=manage.py
FLASK_ENV=development

# Database (MariaDB)
# Formato: mariadb+mariadbconnector://user:password@host:port/dbname
SQLALCHEMY_DATABASE_URI=mariadb+mariadbconnector://user:pass@localhost:3306/nombre_db

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=mi-proyecto-archivos
MINIO_SECURE=False
MINIO_PUBLIC_BASE_URL=http://localhost:9000/mi-proyecto-archivos

# Mail
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=tu-app-password
MAIL_DEFAULT_SENDER=tu-email@gmail.com
```

### 3. Implementación de Servicios Clave

#### Servicio MinIO (`app/services/minio_service.py`)
Utiliza la librería oficial `minio`. El servicio se inicializa con la app (`init_app`) y maneja:
- Verificación/creación automática del bucket.
- Subida de archivos con keys únicas (`uuid`).
- Generación de rutas seguras.

#### Seguridad (`app/extensions.py` y `app/__init__.py`)
Se utiliza `Flask-Talisman` para inyectar headers de seguridad y definir el **Content Security Policy (CSP)**. Es vital configurar `img-src` para permitir imágenes desde el endpoint de MinIO.

### 4. Inicialización de Base de Datos
Para generar la base de datos y aplicar migraciones:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 5. Comandos de Utilidad Personalizados
En `app/commands.py` se definen comandos para agilizar el setup inicial:
- `flask create-admin`: Crea el primer usuario administrador.
- `flask init-bucket`: Asegura que MinIO esté listo.

## 📋 Recomendaciones para Proyectos Similares

1. **Service Layer**: Mantener la lógica pesada de MinIO y Mail en `services/` y no en los `routes`.
2. **Modularidad de Modelos**: Separar modelos en archivos dentro de `app/models/` para evitar archivos gigantes.
3. **Validación Doble**: Usar `Marshmallow` para las APIs y `WTForms` para las vistas que usen templates Jinja2.
4. **Rate Limiting**: Configurar `Flask-Limiter` especialmente en rutas de login y envío de formularios públicos para evitar spam.
5. **Driver MariaDB**: Asegurarse de tener instalado `libmariadb-dev` (en Linux) antes de instalar el conector de Python.

---
*Documento generado para facilitar la estandarización de backends basados en Flask.*
