# Estructura MongoDB para Extracción de Prendas (con Almacenamiento en Disco)

## Colección: `historial_personas` (o la que configures en COLLECTION_NAME)

Cada documento representa **UNA extracción de prendas** (cada vez que presionas "Separar prendas"):

```json
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "persona_id": 1,
  "timestamp": ISODate("2025-01-25T14:35:22.123Z"),
  "imagen_entrada_path": "extracted_garments/persona_1/2025-01-25_14-35-22_entrada.jpg",
  "prendas": {
    "topwear": {
      "imagen_path": "extracted_garments/persona_1/2025-01-25_14-35-22_topwear.png",
      "color_hex": "#FF5733"
    },
    "lowerwear": {
      "imagen_path": "extracted_garments/persona_1/2025-01-25_14-35-22_lowerwear.png",
      "color_hex": "#22FF33"
    },
    "footwear": {
      "imagen_path": null,
      "color_hex": null
    }
  }
}
```

## Campos Explicados

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `_id` | ObjectId | ID único de MongoDB |
| `persona_id` | int | ID del tracking de la persona (ej: 1, 2, 3...) |
| `timestamp` | datetime | Hora exacta de la extracción en UTC |
| `imagen_entrada_path` | string | Ruta relativa a la foto de cámara completa (JPEG) |
| `prendas` | object | Contiene las 3 categorías de prendas |
| `prendas.topwear.imagen_path` | string | Ruta relativa al recorte PNG de la prenda superior |
| `prendas.topwear.color_hex` | string | Color dominante en formato hexadecimal (#RRGGBB) |
| `prendas.lowerwear.imagen_path` | string | Ruta relativa al recorte PNG del pantalón/falda |
| `prendas.lowerwear.color_hex` | string | Color dominante |
| `prendas.footwear.imagen_path` | string | Ruta relativa al recorte PNG del zapato |
| `prendas.footwear.color_hex` | string | Color dominante |

## Estructura de Carpetas en Disco

```
Backend/
└─ extracted_garments/
   ├─ persona_1/
   │  ├─ 2025-01-25_14-35-22_entrada.jpg       (foto de cámara)
   │  ├─ 2025-01-25_14-35-22_topwear.png       (recorte)
   │  ├─ 2025-01-25_14-35-22_lowerwear.png
   │  ├─ 2025-01-25_14-35-22_entrada.jpg       (nueva extracción)
   │  ├─ 2025-01-25_14-36-15_topwear.png       (nueva extracción)
   │  └─ ...
   ├─ persona_2/
   │  ├─ 2025-01-25_14-35-30_entrada.jpg
   │  ├─ 2025-01-25_14-35-30_topwear.png
   │  └─ ...
   └─ persona_3/
      └─ ...
```

## Ventajas de esta Estructura

✅ **MongoDB ligero**: Solo almacena rutas (~1 KB por registro)
✅ **Historico**: Cada extracción es un registro independiente con timestamp
✅ **Archivos en disco**: Acceso rápido, fácil visualización
✅ **Organización**: Carpetas por persona, archivos nombrados con fecha-hora
✅ **Escalable**: Puedes mover `extracted_garments/` a otro storage sin actualizar MongoDB

## Ejemplos de Consultas Útiles

### 1. Ver todas las extracciones de una persona
```python
db.historial_personas.find({"persona_id": 1})
```

### 2. Ver extracciones de hoy
```python
from datetime import datetime, timedelta
hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
db.historial_personas.find({
    "timestamp": {"$gte": hoy}
})
```

### 3. Contar cuántas veces se extrajo cada prenda
```python
db.historial_personas.aggregate([
    {"$group": {
        "_id": None,
        "topwear_detectadas": {
            "$sum": {"$cond": ["$prendas.topwear.imagen_path", 1, 0]}
        },
        "lowerwear_detectadas": {
            "$sum": {"$cond": ["$prendas.lowerwear.imagen_path", 1, 0]}
        }
    }}
])
```

### 4. Obtener rutas de todas las prendas de una persona
```python
db.historial_personas.find(
    {"persona_id": 1},
    {"prendas.topwear.imagen_path": 1, "prendas.lowerwear.imagen_path": 1}
)
```

## Tamaño Aproximado

- Documento MongoDB por extracción: ~500 bytes (solo rutas + metadata)
- Imagen entrada (JPEG): ~50-100 KB
- Recorte de prenda (PNG): ~10-30 KB cada uno
- **Total en disco por extracción**: ~100-200 KB
- **Total en MongoDB**: ~500 bytes

Para 1000 extracciones:
- MongoDB: ~500 KB
- Disco: ~100-200 MB
