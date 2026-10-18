# fgaBlinka30x — Agente inteligente para gestión de facturas

Prototipo web con un agente que recibe facturas simuladas, extrae sus datos, las compara con reglas de una empresa ficticia y emite una decisión:
- **Apta para pago (simulación)**
- **Frenada**
- **Requiere aprobación humana**

Datos 100% ficticios. No ejecuta pagos reales.

## Estado actual — Fase 5 completada

Aplicación web completa con backend (FastAPI + SQLAlchemy + Alembic + PostgreSQL) y frontend (React + TypeScript + Vite).
- **Acceso autenticado:** inicio de sesión con JWT y tres usuarios ficticios de demostración.
- **Fase 2:** CRUD de políticas, beneficiarios y facturas.
- **Fase 3:** motor determinista de reglas (R1–R7), endpoint `/evaluate`, registro de decisiones (`decision_record`) y control de presupuesto (`budget_reservation`).
- **Fase 4:** ingesta de documentos — `POST /invoices/upload` (PDF/imagen → texto con pypdf u OCR) y `POST /invoices/{id}/extract`.
- **Fase 5:** interfaz web — panel, tabla de facturas, detalle con motivos por regla, carga de facturas, centro de aprobaciones, historial y reglas/políticas. La estandarización manual de números asigna códigos secuenciales `A000`–`A999`, `B000`–`B999` y así sucesivamente hasta `Z999`.

## Estructura del repositorio

```text
fgaBlinka30x/
├── backend/              # API FastAPI (Fases 2-4)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              # App FastAPI + /health
│   │   ├── database.py          # SQLAlchemy engine, sesión y Base
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       ├── policy.py            # CRUD y activación de políticas
│   │   │       ├── beneficiaries.py     # CRUD de beneficiarios
│   │   │       ├── invoices.py          # CRUD de facturas
│   │   │       ├── evaluate.py          # /evaluate y /decisions (Fase 3)
│   │   │       └── upload.py            # /upload y /extract (Fase 4)
│   │   ├── models/              # Modelos SQLAlchemy (todas las entidades)
│   │   ├── schemas/             # Esquemas Pydantic
│   │   ├── rules/               # Motor determinista de reglas (Fase 3)
│   │   ├── services/
│   │   │   ├── seed.py          # Carga de datos ficticios (Fase 1)
│   │   │   ├── evaluation.py    # Motor + persistir decisión y reserva (Fase 3)
│   │   │   ├── extraction.py    # Extracción de texto de PDF/imagen (Fase 4)
│   │   │   └── ocr.py           # OCR con Tesseract (opcional, Fase 4)
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── test_crud.py
│   │       ├── test_evaluate.py
│   │       ├── test_rules.py
│   │       └── test_upload.py
├── frontend/             # Interfaz web React + TypeScript + Vite (Fase 5)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx              # Enrutamiento React Router
│   │   ├── index.css            # Estilos (Tailwind-like)
│   │   ├── lib/utils.ts         # Formateo y helpers de UI
│   │   ├── types/index.ts       # Tipos compartidos con la API
│   │   ├── services/api.ts      # Cliente de la API (fetch)
│   │   ├── components/Layout.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Invoices.tsx
│   │   │   ├── InvoiceDetail.tsx
│   │   │   ├── Upload.tsx
│   │   │   ├── ApprovalCenter.tsx
│   │   │   ├── History.tsx
│   │   │   ├── Rules.tsx
│   │   │   └── Beneficiaries.tsx
│   └── dist/                    # Build de producción
├── data-demo/                 # Dataset y reglas de la Fase 1
│   ├── demo-config.json
│   ├── expected-results.json
│   ├── invoices/
│   │   └── invoices.json
│   ├── uploads/               # Archivos subidos (Fase 4, se crea al usar)
│   └── verify_expected.py
├── docs/
│   └── catalogo-reglas.md     # Catálogo de reglas y resultados esperados (Fase 1)
├── migrations/                # Migraciones de Alembic (PostgreSQL)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_add_extracted_to_invoice.py
│       └── 0003_add_file_path_to_invoice.py
├── alembic.ini
├── docker-compose.yml         # PostgreSQL + backend
├── LICENSE
└── README.md
```

## Endpoints disponibles (Fases 2 a 4)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Estado del servicio |
| POST | `/api/v1/auth/login` | Iniciar sesión y obtener un token JWT |
| GET | `/api/v1/auth/me` | Consultar el usuario autenticado |
| GET | `/api/v1/policy` | Política activa |
| PUT | `/api/v1/policy` | Crear nueva versión de política |
| POST | `/api/v1/policy/activate` | Activar una versión de política |
| GET | `/api/v1/beneficiaries` | Listar beneficiarios (filtro opcional `company_id`) |
| POST | `/api/v1/beneficiaries` | Crear beneficiario |
| GET | `/api/v1/invoices` | Listar facturas (filtros: `company_id`, `status`, `beneficiary_id`) |
| POST | `/api/v1/invoices` | Crear factura (entrada manual) |
| GET | `/api/v1/invoices/{id}` | Obtener una factura |
| PATCH | `/api/v1/invoices/{id}` | Actualizar factura (corregir campos extraídos) |
| POST | `/api/v1/invoices/upload` | Subir PDF/imagen, extraer texto y crear factura `PENDING`; acepta `beneficiary_id` para asociar el proveedor y resolver su empresa (Fase 4) |
| POST | `/api/v1/invoices/{id}/extract` | Re-ejecutar extracción sobre el archivo ya subido (Fase 4) |
| POST | `/api/v1/invoices/{id}/evaluate` | Aplicar reglas y registrar decisión (sin ejecutar pagos) (Fase 3) |
| GET | `/api/v1/invoices/{id}/decisions` | Historial de decisiones de una factura (Fase 3) |

Documentación interactiva automática del backend: `http://localhost:8000/docs` (una vez levantado el backend).

## Cómo levantar el entorno

### Opción A: Backend + PostgreSQL con Docker Compose

Define un secreto aleatorio de al menos 32 caracteres en `.env` antes de iniciar:

```env
JWT_SECRET=una-clave-aleatoria-de-al-menos-32-caracteres
```

```bash
docker compose up -d --build
```

Levanta PostgreSQL y el backend, y carga los datos ficticios iniciales si aún no existen. La documentación queda en `http://localhost:8000/docs`.

Usuarios de demostración (los tres usan la contraseña `Demo2026!`):

| Usuario | Nombre |
|---------|--------|
| `ana.perez` | Ana Pérez |
| `carlos.ruiz` | Carlos Ruiz |
| `laura.gomez` | Laura Gómez |

Los cambios de datos requieren autenticación. El actor se determina a partir del token, nunca de un identificador enviado en el cuerpo de la petición.

### Opción B: Backend sin Docker

```bash
cd backend
pip install -r requirements.txt
# Iniciar PostgreSQL desde otra terminal: docker compose up -d postgres
# Configurar DATABASE_URL si no se usan los valores locales por defecto.
# Configurar JWT_SECRET con una clave aleatoria de al menos 32 caracteres.
alembic -c ../alembic.ini upgrade head
python -m app.services.seed
uvicorn app.main:app --reload
```

### Aplicación completa (incluido acceso desde otros dispositivos)

La forma recomendada de iniciar todo es ejecutar desde la raíz del repositorio:

```bash
docker compose up -d --build
```

Compose inicia PostgreSQL, aplica las migraciones, carga los datos ficticios e inicia la API y el frontend de producción. La interfaz y todas sus rutas API se sirven bajo el mismo origen: abre `http://localhost:8080`. El proxy interno del frontend reenvía `/api` a FastAPI, así que el navegador de cada dispositivo no depende de su propio `localhost` ni requiere configurar una dirección de API.

Para entrar desde otro dispositivo conectado a la misma red, abre `http://<IP-DE-ESTE-PC>:8080` (en Windows, consulta la IP con `ipconfig`). Si Windows Firewall pregunta, permite el acceso en la red privada. Los datos permanecen en el volumen de PostgreSQL del equipo que ejecuta Docker; los demás dispositivos acceden a esa misma instancia. Comprueba el estado con `docker compose ps`; el backend debe aparecer saludable.

La API sigue disponible para diagnóstico en `http://localhost:8000/health` (debe responder `{"status":"ok"}`) y su documentación en `http://localhost:8000/docs`.

### Desarrollo del frontend

Para desarrollar con recarga en caliente, inicia primero PostgreSQL y el backend con `docker compose up -d postgres backend`, y luego ejecuta:

```bash
cd frontend
npm install
npm run dev        # abrir http://localhost:5173
```

Vite escucha en la red local y su proxy `/api` reenvía las solicitudes al backend del mismo equipo. Para abrir esta instancia de desarrollo desde otro dispositivo, usa `http://<IP-DE-ESTE-PC>:5173`. Para uso normal entre dispositivos, prefiere el frontend de producción en el puerto 8080.

Para detener los servicios Docker:

```bash
docker compose down
```

Para iniciar solamente el frontend de desarrollo (por ejemplo, si el backend ya está ejecutándose por separado):

```bash
cd frontend
npm run dev
```

## Ejecutar pruebas

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

Las pruebas usan SQLite en memoria y cubren CRUD (fase 2), motor de reglas contra el dataset de 26 facturas (fase 3), ingesta de documentos (fase 4) y seguridad/demostración (fase 6): **17 pruebas pasando**.

## Fase 6 — Seguridad, pruebas y demostración

Criterios de aceptación verificados:

| Criterio | Estado | Prueba |
|----------|--------|--------|
| Dataset 26/26 consistente vs expected-results.json | ✅ | `test_rules.py::test_motor_contra_dataset_26` |
| Dos facturas simultáneas nunca ambas aptas (presupuesto) | ✅ | `test_phase6.py::test_concurrencia_presupuesto` |
| Reevaluación: nueva decisión sin duplicar factura/reserva | ✅ | `test_phase6.py::test_reevaluacion_no_duplica_historial` |
| Sin rutas de pago en la API | ✅ | `test_phase6.py::test_no_rutas_pago` |
| Datos 100% ficticios | ✅ | `test_phase6.py::test_datos_ficticios` |
| Aprobaciones humanas registradas sin reescribir historial | ✅ | `test_phase6.py::test_reevaluacion_no_duplica_historial` |

Ejecutar la demostración repetible de la Fase 6:

```bash
chmod +x demo_phase6.sh
./demo_phase6.sh
```

La aplicación es utilizable de principio a fin (salida de la Fase 5 y verificación de la Fase 6). El reto queda listo para demostrar con datos ficticios: cargar facturas, evaluarlas con el motor determinista, revisar decisiones y aprobar/rechazar en el centro de aprobaciones.

## Licencia

MIT — ver `LICENSE`.
