# AnimeHub Bot

Bot de Discord para comunidades de anime. Ofrece trivia, encuestas, consulta de información de series y rankings de usuarios, respaldado por una API REST con base de datos PostgreSQL.

---

## Requisitos previos

- Python 3.11+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (para la base de datos)
- Cuenta de desarrollador en [Discord](https://discord.com/developers/applications)

---

## 1. Configurar el bot en Discord Developer Portal

1. Accede a [https://discord.com/developers/applications](https://discord.com/developers/applications) y haz clic en **New Application**.
2. Dale un nombre (p. ej. `AnimeHubBot`) y confirma.
3. Ve a la sección **Bot** del menú lateral:
   - Haz clic en **Reset Token** y copia el token generado (lo necesitarás en el `.env`).
   - Activa los siguientes **Privileged Gateway Intents**:
     - `SERVER MEMBERS INTENT`
     - `MESSAGE CONTENT INTENT`
4. Ve a la sección **OAuth2 → URL Generator**:
   - En **Scopes** marca: `bot`, `applications.commands`
   - En **Bot Permissions** marca al menos: `Send Messages`, `Embed Links`, `Read Message History`, `Connect`, `Speak`
   - Copia la URL generada, ábrela en el navegador e invita el bot a tu servidor.

---

## 2. Configurar el archivo `.env`

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```env
# Token del bot (obtenido en Discord Developer Portal)
DISCORD_TOKEN=tu_token_aqui

# ID del servidor de desarrollo para sincronizar slash commands al instante (opcional)
# Si se omite, los comandos se sincronizan globalmente (puede tardar hasta 1 hora)
DEV_GUILD_ID=123456789012345678

# URL de conexión a PostgreSQL (debe coincidir con docker-compose.yml)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/animehub

# Configuración opcional del backend
DEBUG=false
API_HOST=127.0.0.1
API_PORT=8000
```

> **Nota:** el archivo `.env` está en `.gitignore` y nunca debe subirse al repositorio.

---

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Se recomienda usar un entorno virtual:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 4. Uso del backend

### Crear la base de datos PostgreSQL en un contenedor

```bash
docker compose up -d
```

Esto levanta un contenedor `animehub_db` con PostgreSQL 16 en el puerto `5432`. Los datos persisten en el volumen `animehub_pgdata`.

### Arrancar el backend

```bash
uvicorn backend.main:app --reload
```

Al iniciarse, el backend crea automáticamente las tablas en la base de datos si no existen.

### Consultar la documentación interactiva de la API

```
http://127.0.0.1:8000/docs
```

---

## 5. Arrancar el bot

Con el backend y la base de datos en marcha, ejecuta:

```bash
python main.py
```

El bot iniciará sesión, registrará los servidores donde esté presente y sincronizará los slash commands.

---

## Estructura del proyecto

```
animeHubBot/
├── backend/          # API REST (FastAPI + SQLAlchemy)
│   ├── models/       # Modelos ORM
│   ├── routers/      # Endpoints
│   └── schemas/      # Esquemas Pydantic
├── cogs/             # Módulos del bot (comandos Discord)
├── services/         # Clientes externos (AniList, AnimeThemes, backend)
├── utils/            # Utilidades (embeds, i18n)
├── docker-compose.yml
├── main.py           # Punto de entrada del bot
└── requirements.txt
```
