# IluminaRA

Herramienta de modelación de contaminación lumínica para evaluar el impacto de fuentes de luz artificial sobre el cielo nocturno. Genera mapas de brillo de cielo en unidades SQM (*Sky Quality Meter*) a partir de datos geoespaciales de luminarias.

---

## ¿Qué hace?

A partir de un archivo geoespacial con la ubicación y características eléctricas de las luminarias, IluminaRA:

1. Construye una grilla de puntos sobre el área de estudio
2. Modela la contribución lumínica de cada fuente usando el modelo de Albers-Duricoé modificado
3. Calcula el brillo de cielo resultante en cada punto de la grilla (en mag/arcsec²)
4. Exporta el resultado como un shapefile listo para visualizar en QGIS u otro SIG

---

## Requisitos

- Python `3.12` o superior
- Dependencias listadas en `requirements.txt`

```bash
pip install -r requirements.txt
```

---

## Uso

```bash
python main.py
```

El programa es interactivo y guiará al usuario paso a paso:

1. **Ruta del archivo de entrada** — shapefile (`.shp`) o GeoPackage (`.gpkg`) con las luminarias
2. **Directorio de salida** — carpeta donde se guardará el shapefile resultante
3. **Selección de capa** — solo si el archivo es un GeoPackage con múltiples capas
4. **Filtrado opcional** — permite filtrar las luminarias por el valor de cualquier columna
5. **Configuración de grilla** — opcionalmente se puede cambiar el número de puntos y el margen

---

## Formato del archivo de entrada

El archivo debe contener geometría de **puntos** (no multipuntos), con al menos las siguientes columnas:

| Columna | Descripción |
|---|---|
| `default_power_columname` | Potencia eléctrica de la luminaria (W) |
| `default_efficiency_columname` | Eficiencia luminosa (lm/W) |

Los nombres de estas columnas se configuran en `config.json`.

---

## Configuración (`config.json`)

```json
{
    "n_grid_points": 1000,
    "margin_from_points": 40,
    "margin_type": "percentage",
    "cd_2_sqm": "***",
    "natural_background_skyglow": "***",
    "background_sqm": "***",
    "default_power_columname": "***",
    "default_efficiency_columname": "***"
}
```

| Parámetro | Descripción |
|---|---|
| `n_grid_points` | Número de puntos por eje de la grilla (total = n²) |
| `margin_from_points` | Margen alrededor del área de las luminarias |
| `margin_type` | Tipo de margen: `percentage` o `flat` (en unidades del CRS) |
| `cd_2_sqm` | Función de conversión de cd/m² a mag/arcsec² |
| `natural_background_skyglow` | Brillo de cielo natural de fondo |
| `background_sqm` | Valor máximo SQM permitido (cielo sin contaminación) |
| `default_power_columname` | Nombre de la columna de potencia en el archivo de entrada |
| `default_efficiency_columname` | Nombre de la columna de eficiencia en el archivo de entrada |

---

## Archivo de salida

Se genera un shapefile con el nombre:

```
{n_puntos}_points_{margen}_{tipo_margen}_{timestamp}.shp
```

Cada punto de la grilla contiene el campo `Value` con el valor SQM calculado. Un valor **mayor** indica un cielo **más oscuro** (menos contaminado).

---

## Logs

Los registros de ejecución se guardan en la carpeta `logs/` con el formato:

```
iluminara_YYYY_MM_DD_HH_MM_SS.log
```

Esta carpeta está excluida del control de versiones (`.gitignore`).

---

## Estructura del proyecto

```
IluminaRA/
├── main.py             # Orquesta el flujo principal
├── config.py           # Configuración y dataclasses
├── cli.py              # Interacción con el usuario por consola
├── geofile.py          # Clases para manejo de archivos geoespaciales
├── processing.py       # Modelación y cálculo de SQM
├── i_o.py              # Lectura y escritura de archivos
├── logger.py           # Configuración del sistema de logs
├── config.json         # Parámetros por defecto
├── model/
│   ├── model.py        # Escena, grilla y cálculo de skyglow
│   └── luminica.py     # Modelo de fuente lumínica Albers-Duricoé
├── geo.py              # Utilidades geoespaciales
├── errors.py           # Errores personalizados
└── logs/               # Archivos de log (ignorado por git)
```

---

## Modelo físico

IluminaRA implementa el modelo de propagación de luz de **Albers & Duriscoe (****)**, adaptado para estimar el brillo de cielo artificial en función de la distancia y flujo luminoso de cada fuente. La conversión a unidades SQM sigue la relación:

> `SQM = *** `

---

## Licencia

`***`
