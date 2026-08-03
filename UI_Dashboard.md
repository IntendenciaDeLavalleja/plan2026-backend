# Especificación de Diseño y Tecnologías: Panel de Administración

Este documento detalla los estándares de diseño, tecnologías y componentes utilizados en el panel de administración del proyecto "Buzón Ciudadano". El objetivo es servir como guía para mantener la coherencia visual en futuras expansiones o adaptaciones a otros proyectos.

## 🛠️ Stack Tecnológico

| Tecnología | Uso | Implementación |
| :--- | :--- | :--- |
| **Flask** | Framework Backend | Gestión de rutas, autenticación y lógica de negocio. |
| **Jinja2** | Motor de Plantillas | Generación de HTML dinámico con herencia de plantillas (`base.html`). |
| **Tailwind CSS** | Framework CSS | Estilizado basado en utilidades mediante CDN. |
| **Flowbite** | Componentes UI | Extend de Tailwind para elementos interactivos (modals, tooltips, drawers). |
| **Inter** | Tipografía | Fuente principal (Sans-serif) cargada vía Google Fonts. |
| **SVG** | Iconografía | Iconos vectoriales integrados directamente en el HTML para máxima fidelidad y control. |

## 🎨 Paleta de Colores y Estética

El diseño se basa en una estética **limpia, profesional y moderna**, utilizando la escala de grises de `Slate` para la estructura y colores vibrantes para la semántica.

### Colores Base
- **Fondo General:** `bg-slate-50` (#f8fafc) - Proporciona un entorno descansado para la lectura.
- **Texto Principal:** `text-slate-900` - Máximo contraste para legibilidad.
- **Texto Secundario:** `text-slate-500` / `text-slate-400` - Para descripciones y etiquetas.
- **Bordes:** `border-slate-200` - Separaciones sutiles.

### Colores Semánticos (Estados)
- **Pendiente / Neutro:** `Slate-900`
- **En Progreso / Acción:** `Blue-600` / `Indigo-600`
- **Resuelto / Éxito:** `Emerald-500`
- **Error / Alerta:** `Rose-500`
- **Historial / Deshabilitado:** `Slate-400`

## 📐 Estructura de Diseño (Layout)

1.  **Navbar Superior (fijo):**
    - Fondo: `bg-white/80` con `backdrop-blur-md` (efecto de cristal esmerilado).
    - Altura: `py-3`.
    - Elementos: Logo con degradado (`from-blue-600 to-indigo-600`) a la izquierda, perfil de usuario a la derecha.

2.  **Sidebar Lateral (fijo):**
    - Ancho: `w-64`.
    - Comportamiento: Visible en escritorio, colapsable en móviles mediante un menú hamburguesa.
    - Estilo: Fondo blanco, borde derecho sutil, items de lista con `rounded-xl`.

3.  **Contenedor Principal:**
    - Margen: `sm:ml-64` (para respetar el sidebar).
    - Ancho máximo: `max-w-7xl mx-auto`.
    - Espaciado: `px-6 py-8`.

## 🧩 Componentes y Elementos UI

### 1. Tarjetas de Estadísticas (Stats Cards)
- **Forma:** `rounded-3xl`
- **Efectos:** `shadow-sm`, transición suave (`transition-all duration-300`).
- **Interacción:** Al hacer hover, la sombra se intensifica y adquiere un tono sutil acorde al estado (ej: `hover:shadow-blue-100`).
- **Indicador Numérico:** Círculo flotante en la esquina superior derecha (`absolute -top-3 -right-3`) con fondo contrastado.

### 2. Acciones Rápidas (Icon Grid)
- **Contenedores:** Cajas con `rounded-[2rem]`.
- **Iconos:** Enmarcados en cuadrados con `rounded-2xl` y fondos pasteles de la misma gama cromática.
- **Hover:** Cambio de fondo del contenedor de icono a color sólido y texto a blanco.

### 3. Botones
- **General:** `rounded-full` (estético orgánico).
- **Acción Principal:** Fondo oscuro (`bg-slate-900`) o azul intenso.
- **Transiciones:** `transition-colors` para cambios de tono en hover.

### 4. Alertas (Flash Messages)
- **Radio:** `rounded-2xl`.
- **Colores:** Fondos muy claros (`50`) con bordes ligeros (`100`) y texto oscuro contrastado (`800`).

## 🖋️ Tipografía y Pesos
- **Títulos de Sección:** `font-extrabold` o `font-black` para dar jerarquía.
- **Etiquetas/Headers:** `uppercase tracking-widest` para un look moderno y profesional.
- **Cuerpo:** `font-medium` o `font-normal` para facilitar la lectura de datos.

## 🚀 Guía de Adaptación
Para replicar este diseño en otros módulos:
1. Utilizar siempre la escala `Slate` para la estructura.
2. Mantener radios de curvatura grandes (`xl`, `2xl`, `3xl`).
3. Aplicar `backdrop-blur` en elementos fijos sobre el contenido.
4. Usar degradados solo en logotipos o acentos muy específicos.
5. Priorizar el uso de `Inter` y pesos de fuente variados para crear jerarquía visual sin necesidad de muchos colores.
