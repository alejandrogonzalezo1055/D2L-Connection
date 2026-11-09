# EduTrace - D2L Connection

Cliente OAuth2 (Authorization Code) de EduTrace hacia Brightspace (D2L). Hoy se conecta al mock de Brightspace y obtiene tokens de acceso y de refresco. Es parte del proyecto de innovación en TI.

## Requisitos

- Python 3.14. El `.venv` local se creó con esa versión. El código usa `match` y f-strings con comillas dobles anidadas, así que necesita 3.12 o superior.
- Acceso al mock de Brightspace por Tailscale. La IP o nombre del mock va en `common/.env`.
- Mock corriendo en el puerto 8800 (carpeta hermana `mock-brightspace`).

## Instalación

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install fastapi httpx pydantic-settings uvicorn
```

No hay `requirements.txt` ni `pyproject.toml`. Las dependencias salen de los imports del código:

| Paquete | Dónde se usa |
|---|---|
| `fastapi` | `app/` (routers, app factory) |
| `httpx` | `app/services/oauth_service.py` (llamadas al mock) |
| `pydantic` | `common/schemas.py` |
| `pydantic-settings` | `common/settings.py` |
| `uvicorn` | Solo para arrancar el servidor |

Versiones instaladas en el `.venv` local al escribir este README: fastapi 0.162.0, httpx 0.28.1, pydantic 2.14.2, pydantic-settings 2.16.2, uvicorn 0.54.0 (starlette 1.10.0 viene como dependencia de fastapi).

## Configuración

Las variables se leen de `common/.env`. La ruta es relativa, así que la app debe ejecutarse desde la raíz del proyecto.

Crear el archivo local a partir de la plantilla:

```bash
cp common/.env.example common/.env
```

Luego reemplazar los valores de ejemplo por los reales. `common/.env` no se sube al repositorio (está en `.gitignore`). Si alguna vez se subió a un repositorio remoto, hay que rotar el secreto.

| Variable | Para qué sirve | Ejemplo (falso) |
|---|---|---|
| `MOCK_API_BASE_URL` | Host del mock para la API y el logout | `192.0.2.10` |
| `MOCK_AUTH_BASE_URL` | Host del mock para autorización y emisión de tokens | `192.0.2.10` |
| `APP_ID` | `client_id` de la aplicación registrada en el mock | `00000000-0000-0000-0000-000000000000` |
| `APP_SECRET` | `client_secret` de esa aplicación | `cambia-por-el-secreto-real` |
| `APP_SCOPE` | Scopes pedidos, separados por espacios | `users:own_profile:read grades:own_grades:read` |

El puerto 8800 del mock y la URL de callback `http://localhost:9000/auth/callback` están fijos en el código, no en la configuración.

## Cómo ejecutar

Desde la raíz del proyecto:

```bash
uvicorn app.main:create_app --factory --port 9000
```

`--factory` es obligatorio porque `create_app()` es una función que crea la app. Para desarrollo se puede agregar `--reload`:

```bash
uvicorn app.main:create_app --factory --port 9000 --reload
```

## Endpoints

| Método | Ruta | Qué hace | Cookies y cuerpo |
|---|---|---|---|
| GET | `/health` | Sondeo de vida. Responde `{"status": "ok"}` | Ninguna |
| GET | `/auth/login-url` | Responde 302 a `/oauth2/auth` del mock con `state` aleatorio | Pone `oauth_state` (HttpOnly, 300 s) |
| GET | `/auth/logout-url` | Responde 302 a `/d2l/logout` del mock | Ninguna |
| GET | `/auth/callback` | Recibe `code` y `state` por query. Compara `state` con la cookie `oauth_state` | Lee `oauth_state`. Pone `auth_code` (HttpOnly, 300 s). Responde 200 con texto |
| POST | `/auth/obtain-token` | Con `"access"` canjea `auth_code` por tokens. Con `"refresh"` usa `refresh_token` para renovar | Lee `auth_code` o `refresh_token`. Body JSON: una cadena, `"access"` o `"refresh"`. Pone `access_token`, `refresh_token` y `response_time`. Responde `token_type`, `expires_in` y `scope` |

Errores que se ven en el código:

- `/auth/callback`: 400 si no hay cookies, si falta `oauth_state` o si `state` no coincide. 422 si `state` tiene menos de 32 caracteres (verificado).
- `/auth/obtain-token`: 400 si no llega la cookie necesaria (verificado). 406 si la opción no es `access` ni `refresh`. 422 si el body es un objeto JSON y no una cadena (verificado).

## Flujo de autenticación

1. El navegador abre `GET /auth/login-url`. La app genera un `state` aleatorio, lo guarda en la cookie `oauth_state` y redirige al mock.
2. El usuario inicia sesión y da consentimiento en el mock. El mock redirige a `http://localhost:9000/auth/callback?code=...&state=...`.
3. `/auth/callback` compara el `state` de la URL con la cookie `oauth_state`. Si coinciden, guarda el código en la cookie `auth_code`. La cookie `oauth_state` evita CSRF: un callback que no inició esta app no pasa la comparación.
4. `POST /auth/obtain-token` con `"access"` canjea `auth_code` en el mock por `access_token` y `refresh_token`. Las dos cookies quedan guardadas.
5. `POST /auth/obtain-token` con `"refresh"` usa la cookie `refresh_token` para pedir un access token nuevo. El refresh token es de un solo uso (lo indica la documentación del mock, `mock-brightspace/docs/04-TOKENS-SCOPES-PERMISOS.md` §5): el mock devuelve uno nuevo y la app lo guarda en la cookie. El refresh anterior deja de servir.

Los tokens se guardan en cookies HttpOnly, así que JavaScript de la página no puede leerlas. El código de autorización vence en 5 minutos y sirve una sola vez.

## Cómo probar a mano

Usar `localhost`, no `127.0.0.1`. Las cookies son por host, y el `redirect_uri` registrado usa `localhost`. Si se mezclan, el navegador no envía las cookies a donde deben ir.

1. Arrancar el mock (puerto 8800) y la app (puerto 9000).
2. En el navegador abrir `http://localhost:9000/auth/login-url`. Iniciar sesión en el mock. El navegador vuelve a `/auth/callback`.
3. Copiar el valor de la cookie `auth_code` desde las herramientas de desarrollo del navegador y pedir el access token:

   ```bash
   curl -i -X POST http://localhost:9000/auth/obtain-token \
     -H "Content-Type: application/json" \
     -H "Cookie: auth_code=<VALOR_DE_AUTH_CODE>" \
     -d '"access"'
   ```

4. Para renovar, copiar la cookie `refresh_token` que dejó el paso anterior y llamar:

   ```bash
   curl -i -X POST http://localhost:9000/auth/obtain-token \
     -H "Content-Type: application/json" \
     -H "Cookie: refresh_token=<VALOR_DE_REFRESH_TOKEN>" \
     -d '"refresh"'
   ```

El body es la cadena JSON `"access"` o `"refresh"`, no un objeto `{"option": ...}`. Con objeto la API responde 422.

Para cambiar de usuario, abrir `http://localhost:9000/auth/logout-url` y cerrar sesión en el mock. La app no borra sus cookies, así que hay que eliminar `auth_code`, `access_token`, `refresh_token`, `response_time` y `oauth_state` desde las herramientas del navegador, o esperar a que venzan.

## Estructura del proyecto

```
.
├── .gitignore
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py                 # create_app(): middleware, errores y routers
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py           # GET /health
│   │   └── oauth_router.py     # /auth/*
│   └── services/
│       ├── __init__.py
│       └── oauth_service.py    # lógica OAuth2 contra el mock
├── common/
│   ├── __init__.py
│   ├── .env                    # local, no se versiona
│   ├── .env.example            # plantilla con valores falsos
│   ├── errors.py               # register_error_handler (vacío)
│   ├── schemas.py              # modelos Pydantic y helpers de cookies y respuestas
│   └── settings.py             # Settings (pydantic-settings)
└── .idea/                      # configuración de PyCharm (en .gitignore, pero aún rastreada)
```

## Limitaciones conocidas

- Middleware de renovación automática no funciona (`app/main.py:14-35`). Llama a `OAuthServ.auto_obtain_tokens(...)` sobre el alias `Annotated`, no sobre una instancia. Al llamarlo, Python lanza `TypeError` por el argumento `response` que falta (verificado). Además, compara `time_diff.seconds`, que ignora los días, y parte de un `strptime` con fecha 1900. Solo revisa la respuesta que se acaba de generar, que es la que trae `response_time` recién creado, así que la rama de renovación casi nunca se activa.
- `auto_access_token` tiene errores (`app/services/oauth_service.py:289-291`). Usa `.json` sin paréntesis y referencia `auth_code`, que no existe en ese método. Es código que no se usa desde ningún endpoint, pero el middleware sí intenta llamarlo.
- `/auth/callback` sin query string responde 500 (verificado). `request` puede ser `None` y se accede a `request.state` sin comprobar.
- `redirect_uri` fijo en `http://localhost:9000/auth/callback` (`oauth_service.py:47` y `:148`). Puerto 8800 fijo para el mock (`oauth_service.py:32`, `:67`, `:138`). Cambiar de host o puerto exige editar código.
- `register_error_handler` está vacío (`common/errors.py:4-5`). Los errores usan los manejadores por defecto de FastAPI.
- `api_v1 = APIRouter(prefix="/api/v1")` se incluye sin rutas (`app/main.py:41-42`).
- `get_service` tiene `@lru_cache`. La instancia no guarda estado por usuario: lo que comparte es el `httpx.Client` (`oauth_service.py:28`), que nunca se cierra. Los tokens viajan en cookies del navegador, no en el servidor.
- Las URL del mock salen de `MOCK_*`, que tienen default `None`. Si falta la variable, la URL queda como `http://None:8800`. `APP_SECRET` también tiene default `None`: la app arranca sin él y falla al pedir tokens.
- Las cookies no llevan `secure`. Es aceptable para `localhost` por HTTP, pero no para un despliegue.
- Sin tests, sin logging y sin `requirements.txt` o `pyproject.toml`.
- `common/.env` está versionado en git (ver `git ls-files`). Hay que quitarlo del índice y rotar las credenciales.
