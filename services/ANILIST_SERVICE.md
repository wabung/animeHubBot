# AniList GraphQL Service

Módulo de servicio para interactuar con la API de AniList usando GraphQL. Proporciona métodos para búsqueda de anime, recomendaciones por género, información de personajes y más.

## Instalación

Primero, instala las dependencias:

```bash
pip install -r requirements.txt
```

## Uso Básico

### Importar el servicio

```python
from services import AniListService
import asyncio

service = AniListService()
```

### Métodos disponibles

#### 1. **Buscar anime**
```python
# Buscar por nombre
result = await service.search_anime("Demon Slayer", page=1, per_page=5)

# Resultado
# {
#   "Page": {
#     "pageInfo": {"total": 150, "currentPage": 1, ...},
#     "media": [
#       {
#         "id": 45576,
#         "title": {"romaji": "Kimetsu no Yaiba", ...},
#         "coverImage": {"large": "..."},
#         "averageScore": 87,
#         "episodes": 26,
#         "genres": ["Action", "Demon", "School"],
#         ...
#       },
#       ...
#     ]
#   }
# }
```

#### 2. **Obtener detalles de un anime**
```python
# Requiere el ID de AniList del anime
details = await service.get_anime_details(anime_id=45576)

# Incluye:
# - Información completa (sinopsis, estado, temporada)
# - Próximo episodio (si está en emisión)
# - Relaciones con otros anime
# - Recomendaciones automáticas
```

#### 3. **Buscar por género**
```python
# Obtener anime de un género específico
result = await service.get_anime_by_genre(
    genres=["Action", "Supernatural"],
    page=1,
    per_page=10,
    min_score=70  # Opcional: puntuación mínima
)
```

Géneros disponibles en AniList:
- Action, Adventure, Comedy, Drama, Fantasy, Horror, Mahou Shoujo, Mecha, Music, Mystery, Psychological, Romance, Sci-Fi, Slice of Life, Sports, Supernatural, Thriller

#### 4. **Obtener personajes de un anime**
```python
# Traer los principales personajes y sus actores de voz
characters = await service.get_anime_characters(
    anime_id=45576,
    per_page=10
)

# Incluye:
# - Nombre del personaje
# - Imagen
# - Rol (Main, Supporting, etc.)
# - Actor de voz (en japonés)
```

#### 5. **Obtener perfil de usuario**
```python
# Información de un usuario de AniList
user = await service.get_user_profile(username="Ziglute")

# Incluye:
# - Avatar e información del perfil
# - Estadísticas de anime (cantidad vistas, puntuación media)
# - Rol de moderador (si aplica)
```

#### 6. **Obtener anime en tendencia**
```python
# Anime más populares actualmente
trending = await service.get_trending_anime(page=1, per_page=10)

# Ranking en tiempo real de anime más populares
```

## Manejo de Errores

Todos los métodos retornan `None` en caso de error. Los errores se registran en el logger:

```python
import logging

result = await service.search_anime("test")
if result is None:
    # Error ocurrió, revisa discord.log o consola
    pass
```

## Testing

Para probar el servicio sin el bot:

```bash
python test_anilist.py
```

Esto ejecutará pruebas de todos los métodos principales.

## Recursos

- [API de AniList](https://anilist.co/api/graphql)
- [Documentación de AniList](https://anilist.gitbook.io/anilist-apiv2-docs/)
- [GraphQL en Python (gql)](https://github.com/graphql-python/gql)
