# Guía de Implementación: Sistema 2FA y Mail Service

Este documento describe la arquitectura e implementación del sistema de doble autenticación (2FA) y el servicio de mensajería electrónica utilizado en el proyecto, diseñado para ser replicable en futuros desarrollos.

---

## 1. Sistema de Doble Autenticación (2FA)

El sistema implementa un login en dos pasos para el panel de administración, asegurando que solo usuarios con acceso a su correo electrónico puedan entrar.

### Arquitectura (2-Step Login)
1.  **Paso 1 (Credenciales):** El usuario ingresa email, contraseña y captcha.
2.  **Paso 2 (Verificación):** Si las credenciales son válidas, se genera un código aleatorio, se envía por mail y el ID del usuario se guarda en una **sesión temporal** (`session['2fa_user_id']`). No se usa `login_user()` hasta que el código sea validado.
3.  **Finalización:** Tras validar el código, se limpia la sesión temporal y se inicia la sesión real con `Flask-Login`.

### Modelos de Datos (SQLAlchemy)
Se utilizan dos tablas principales:
-   `User`: Almacena el hash de la contraseña (Argon2), estado activo y relación con códigos.
-   `TwoFactorCode`: Almacena el **hash** del código (nunca en texto plano), fecha de expiración, intentos y estado de consumo.

### Flujo de Seguridad
1.  **Captcha:** El primer paso del login incluye un captcha aritmético simple para evitar ataques automatizados.
2.  **Rate Limiting:** Se utiliza `Flask-Limiter` en las rutas de `/login` y `/2fa` para mitigar ataques de fuerza bruta.
3.  **Generación Segura:** Se utiliza `secrets.choice` para generar códigos criptográficamente fuertes.
4.  **Hashing:** Los códigos se hashea con **Argon2** antes de persistirse en la DB.
5.  **Auditoría:** Cada inicio de sesión (exitoso o fallido) se registra en una tabla de `ActivityLog` con IP y User Agent.
6.  **Expiración y Un Solo Uso:** Los códigos caducan a los 10 minutos y se marcan como `consumed_at` tras su primer uso exitoso.

### Implementación en `AuthService`
```python
def generate_and_send_2fa(self, user, mail_service):
    # Verificar cooldown
    # Generar código: generate_random_code(6)
    # Hashear y guardar en TwoFactorCode
    # Enviar vía mail_service.send_admin_2fa_code(user, code)

def verify_2fa_code(self, user, code):
    # Buscar código no expirado y no consumido
    # Verificar hash con ph.verify()
    # Marcar como consumido
```

---

## 2. Sistema de Envío de Mails (`MailService`)

El servicio de correo está construido sobre `Flask-Mail` con abstracciones para facilitar su uso asíncrono.

### Características Principales
-   **Envío Asíncrono:** Utiliza `threading.Thread` para que el usuario no experimente retrasos mientras se conecta al servidor SMTP.
-   **Templating:** Integración nativa con Jinja2 para correos HTML estilizados.
-   **Logging de Debug:** En modo desarrollo, imprime los códigos 2FA en la consola para facilitar el testing.
-   **Soporte de Adjuntos:** Permite enviar múltiples archivos pasando una lista de diccionarios con `data` en bytes.

### Clase `MailService`
Implementa un método genérico `send_email` que encapsula la lógica de Flask-Mail:

```python
def send_email(self, subject, recipients, template, sync=False, attachments=None, **kwargs):
    msg = Message(subject, recipients=recipients)
    msg.html = render_template(template, **kwargs)
    # Manejo de adjuntos y envío (sync o async)
```

---

## 3. Cómo Replicar en Otros Proyectos

### Paso 1: Dependencias
Instalar los paquetes necesarios:
```bash
pip install Flask-Mail argon2-cffi
```

### Paso 2: Variables de Entorno
Configurar las credenciales en el `.env`:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu-correo@gmail.com
MAIL_PASSWORD=tu-app-password
```

### Paso 3: Configurar Extensiones
En `extensions.py`:
```python
from flask_mail import Mail
mail = Mail()
# En create_app: mail.init_app(app)
```

### Paso 4: Integrar Lógica
1. Copiar `backend/app/services/mail_service.py` (ajustando los imports).
2. Copiar los modelos de `User` y `TwoFactorCode`.
3. Implementar las rutas de `/login` y `/2fa` siguiendo el patrón de redirección temporal en sesión (`session['2fa_user_id']`).

### Paso 5: Templates
Crear la carpeta `templates/emails/` y añadir los archivos HTML. Es importante usar estilos inline para máxima compatibilidad con clientes de correo.

---
*Nota: Para seguridad adicional, se recomienda usar un `limiter` (Flask-Limiter) en las rutas de login y verificación.*
