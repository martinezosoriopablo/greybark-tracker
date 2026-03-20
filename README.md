# Greybark Deal Tracker

Sistema de gestión de proyectos de intermediación financiera.

## Stack Tecnológico

- **Backend**: FastAPI + SQLModel
- **Base de datos**: PostgreSQL (via Supabase)
- **Templates**: Jinja2
- **Frontend**: HTML + Tailwind CSS (CDN)
- **Deploy**: Render.com

## Estructura del Proyecto

```
greybark-tracker/
├── main.py              # Aplicación FastAPI principal
├── database.py          # Modelos SQLModel y configuración DB
├── routers/
│   ├── projects.py      # CRUD de proyectos
│   ├── milestones.py    # Toggle de hitos
│   ├── documents.py     # Gestión de documentos
│   ├── activities.py    # Log de actividades
│   └── ai_summary.py    # Resumen con Claude AI
├── templates/
│   ├── base.html        # Template base
│   ├── dashboard.html   # Dashboard principal
│   ├── project_detail.html
│   └── project_form.html
├── static/
│   └── logo.png         # Logo (reemplazar)
├── requirements.txt
├── Procfile
├── render.yaml
├── .env.example
└── seed_data.py         # Datos de ejemplo
```

## Desarrollo Local

### 1. Clonar y configurar entorno

```bash
git clone <tu-repo>
cd greybark-tracker

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### 3. Ejecutar localmente

```bash
# Con SQLite local (para desarrollo)
uvicorn main:app --reload

# Cargar datos de ejemplo
python seed_data.py
```

La aplicación estará en: http://localhost:8000

## Deploy en Producción

### Paso 1: Crear proyecto en Supabase

1. Ve a [supabase.com](https://supabase.com) y crea una cuenta
2. Crea un nuevo proyecto
3. Ve a **Settings > Database**
4. Copia el **Connection string** (URI)
   - Formato: `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
5. Guarda esta URL, la necesitarás para Render

### Paso 2: Subir código a GitHub

```bash
git init
git add .
git commit -m "Initial commit: Greybark Deal Tracker"
git branch -M main
git remote add origin https://github.com/tu-usuario/greybark-tracker.git
git push -u origin main
```

### Paso 3: Deploy en Render

1. Ve a [render.com](https://render.com) y crea una cuenta
2. Click en **New > Web Service**
3. Conecta tu repositorio de GitHub
4. Configura el servicio:
   - **Name**: `greybark-tracker`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

5. Agrega las variables de entorno:
   - `DATABASE_URL`: La URL de Supabase del Paso 1
   - `ANTHROPIC_API_KEY`: Tu API key de Anthropic (para resúmenes IA)
   - `PYTHON_VERSION`: `3.11`

6. Click en **Create Web Service**

### Paso 4: Cargar datos iniciales (opcional)

Una vez desplegado, puedes conectarte via Render Shell:

```bash
python seed_data.py
```

## Funcionalidades

### Dashboard
- KPIs: proyectos activos, pipeline ponderado, en closing/term sheet, comisión cerrados
- Grid de proyectos con barra de progreso de hitos
- Semáforo de estado (verde/amarillo/rojo)

### Detalle de Proyecto
- Información completa del proyecto
- Checklist de 11 hitos clickeables
- Gestión de documentos (links a Google Drive)
- Timeline de actividades
- **Resumen IA** con Claude (análisis ejecutivo, riesgos, próximos pasos)

### Hitos del Proyecto
1. NDA
2. Teaser
3. Acuerdo Comercial
4. Reunión Inversionista
5. Proyecto
6. Data Room
7. Due Diligence
8. LOI
9. Negociación
10. Term Sheet
11. Closing

## API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Dashboard |
| GET | `/project/new` | Formulario nuevo proyecto |
| POST | `/project/new` | Crear proyecto |
| GET | `/project/{id}` | Detalle proyecto |
| GET | `/project/{id}/edit` | Formulario editar |
| POST | `/project/{id}/edit` | Actualizar proyecto |
| POST | `/project/{id}/delete` | Eliminar proyecto |
| POST | `/api/milestones/{id}/toggle` | Marcar/desmarcar hito |
| POST | `/api/documents/add` | Agregar documento |
| POST | `/api/documents/{id}/delete` | Eliminar documento |
| POST | `/api/activities/add` | Agregar actividad |
| POST | `/api/ai_summary/{id}` | Generar resumen IA |
| GET | `/health` | Health check |

## Variables de Entorno

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `DATABASE_URL` | URL de conexión PostgreSQL | Sí |
| `ANTHROPIC_API_KEY` | API key de Anthropic para resúmenes IA | Para IA |

## Personalización

### Cambiar el logo
Reemplaza `static/logo.png` con tu logo (formato PNG, ~40x40px recomendado).

### Modificar hitos
Edita `MILESTONE_NAMES` en `database.py` para cambiar los nombres de los hitos.

## Licencia

MIT
