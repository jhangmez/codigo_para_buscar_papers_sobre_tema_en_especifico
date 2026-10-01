# 🎓 Thesis Consensus: Buscador y Evaluador Científico para Fundamentos Teóricos de Tesis

**Thesis Consensus** es un sistema automatizado en Python diseñado específicamente para tesistas de pregrado y posgrado. Su propósito es **fundamentar con rigor científico afirmaciones y preguntas de investigación**, contrastando la literatura mediante **modelos de decisión (Unsloth Laya / Jev API / Evaluador por Facetas)**, aplicando un **umbral exigente (80% - 85%)** y redactando automáticamente párrafos de marco teórico y bibliografía bajo las normas oficiales **APA 7ma Edición**.

Inspirado en plataformas como *Consensus.app*, pero adaptado a la elaboración sistemática del marco teórico y fundamentación teórica de una tesis universitaria.

---

## 📑 Tabla de Contenidos

- [1. Arquitectura y Flujo de Trabajo](#1-arquitectura-y-flujo-de-trabajo)
- [2. ¿Qué se le envía al Modelo de Decisión? (Resumen vs. Contenido Completo)](#2-qué-se-le-envía-al-modelo-de-decisión-resumen-vs-contenido-completo)
- [3. Mecanismos de Validación y Toma de Decisiones](#3-mecanismos-de-validación-y-toma-de-decisiones)
- [4. Seguridad y Cero Riesgo de Malware](#4-seguridad-y-cero-riesgo-de-malware)
- [5. Redacción Multi-Paper y Estándar APA 7ma Edición](#5-redacción-multi-paper-y-estándar-apa-7ma-edición)
- [6. Configuración Centralizada (constants.py)](#6-configuración-centralizada-constantspy)
- [7. Modos de Uso y Ejecución por Lote (Batch)](#7-modos-de-uso-y-ejecución-por-lote-batch)
- [8. Tipado Estricto (Cero Any) y Pruebas Unitarias](#8-tipado-estricto-cero-any-y-pruebas-unitarias)

---

## 1. Arquitectura y Flujo de Trabajo

El sistema opera bajo un pipeline secuencial de 5 fases para garantizar que ningún texto quede sin sustento científico:

```mermaid
flowchart TD
    A["Preguntas / Afirmaciones de Tesis (Batch o Individual)"] --> B["Búsqueda Federada en Bases Indexadas (OpenAlex + Crossref)"]
    B --> C["Extracción Segura de Contenido (Abstract + Open Access HTML/PDF en Memoria)"]
    C --> D["Evaluación con Modelo de Decisión (Unsloth Laya o Semántico por Facetas)"]
    D -->|P Relevancia >= 80% y Rigor >= 1.6| E["CONSERVAR: Generación de Síntesis Multi-Paper y APA 7"]
    D -->|P Relevancia < 80% o Fuera de foco| F["DESCARTAR: Justificación registrada en la tabla de decisión"]
    E --> G["Reporte Maestro Markdown (Índice, Secciones y Bibliografía Unificada)"]
    E --> H["Archivo BibTeX Deduplicado (.bib para Zotero / LaTeX)"]
```

---

## 2. ¿Qué se le envía al Modelo de Decisión? (Resumen vs. Contenido Completo)

Una duda fundamental en la investigación asistida por IA es: **¿Es suficiente evaluar el resumen o se debe enviar el contenido completo del artículo (HTML / PDF)?**

### La Realidad Técnica y los Desafíos del Contenido Completo:
1. **Límite de Contexto de los Modelos de Decisión:**
   - Modelos especializados como **Unsloth Laya** tienen una ventana de contexto de **1024 tokens** (en modo multilingüe) o **512 tokens** (en inglés).
   - Un paper científico completo promedio tiene entre **10,000 y 25,000 palabras** (15 a 30 páginas). Si se intenta enviar un PDF completo de golpe, la ventana de contexto se satura de inmediato, provocando errores de memoria o truncando el 95% del documento (dejando únicamente la introducción genérica).
2. **Paywalls y Bloqueos de Editoriales:**
   - Más del 50% de los DOIs en editoriales académicas (IEEE, Springer, Elsevier, Taylor & Francis) tienen muros de pago (*paywalls*). La URL del DOI conduce a una página resumen y bloquea la descarga del texto completo con errores `403 Forbidden` a menos que se cuente con suscripción institucional.
   - Sin embargo, los **metadatos y resúmenes estructurados** están indexados legal y abiertamente a través de OpenAlex y Crossref.

### La Solución Implementada: Extracción Progresiva en 2 Fases (`SafeContentExtractor`)
El sistema no se limita a un simple resumen, sino que implementa una arquitectura progresiva inteligente:

1. **Fase 1: Cribado Rápido (Screening):**
   - Se analizan el título, palabras clave y el resumen estructurado reconstruido en memoria desde OpenAlex. Los artículos totalmente irrelevantes (p. ej. papers de medicina o física cuántica que aparecieron por homonimia de palabras) se descartan en milisegundos sin consumir ancho de banda.
2. **Fase 2: Extracción Profunda de Secciones Críticas (Deep Extraction):**
   - Para artículos que son de **Acceso Abierto (Open Access)**, el módulo `SafeContentExtractor` resuelve la URL oficial y extrae el texto enriquecido:
     - **Si es HTML Open Access:** Limpia etiquetas, scripts y rastreadores, extrayendo los párrafos centrales.
     - **Si es PDF Open Access:** Lee el archivo directamente en memoria (mediante `pypdf`), sin guardar nada en disco.
   - **Priorización de Secciones de Evidencia:** En lugar de saturar el modelo con párrafos de agradecimientos o fórmulas matemáticas irrelevantes, el algoritmo localiza y extrae las secciones de **Resultados (Results/Findings)**, **Discusión** y **Conclusiones**, seleccionando las mejores 500–650 palabras.
   - **Entrada al Modelo:** Se envía al modelo de decisión una estructura limpia que incluye:
     ```
     Paper Title: [Título]
     Venue/Journal: [Revista arbitrada o Congreso]
     Year: [Año]
     Content Source: open_access_pdf | open_access_html | abstract_only
     Content/Findings Excerpt:
     [Párrafos con resultados empíricos, porcentajes, métricas de tickets o conclusiones teóricas]
     ```

---

## 3. Mecanismos de Validación y Toma de Decisiones

El sistema valida la idoneidad teórica de cada artículo mediante dos motores complementarios:

### A. Integración con Unsloth Laya (Jev Decision API)
Si tienes **Unsloth Desktop** instalado y activo en `http://localhost:8888/v1/systemone`, el sistema le formula 3 preguntas estructuradas:
1. **`is_relevant` (`noul`):** Calibra la probabilidad matemática de que el paper fundamente directamente la afirmación de tesis.
2. **`evidence_type` (`choice`):** Clasifica el paper en:
   - `case_study`: Estudio de caso en instituciones educativas o help desks reales.
   - `survey_or_data`: Encuesta estadística, análisis de métricas de tickets o cuellos de botella.
   - `theoretical`: Marco conceptual, mejores prácticas ITIL/ITSM o revisión de literatura.
   - `irrelevant`: Descarte por no pertenecer al dominio.
3. **`rigor_score` (`score`):** Calibra la calidad y solidez académica en una escala de 0.0 a 3.0.

### B. Evaluador Semántico por Facetas Conceptuales (Zero-GPU Fallback)
Si Unsloth no está activo en ese instante, entra en acción el motor heurístico por facetas conceptuales, el cual evalúa si el artículo cubre los 3 pilares indispensables de tu tesis:
1. **Faceta 1 (Marco metodológico):** Presencia de ITSM, ITIL, gestión de servicios o gobernanza tecnológica.
2. **Faceta 2 (Contexto institucional):** Presencia de educación superior, universidades, facultades o campus académico.
3. **Faceta 3 (Problema operativo):** Presencia de mesa de ayuda (help desk), volumen de tickets, cuellos de botella o acuerdos de nivel de servicio (SLAs).

### C. Umbral Estricto de Corte (80% - 85%)
- **Regla:** Solo se conserva un artículo si su probabilidad calculada es **mayor o igual al 80% (o al 85% en modo estricto)** y su tipología no es irrelevante.
- Si un artículo habla solo de educación sin TI, o habla de ITIL en la banca sin tocar universidades, su puntaje no alcanza el 80% y se descarta automáticamente.

---

## 4. Seguridad y Cero Riesgo de Malware

Descargar y ejecutar archivos PDF arbitrarios de internet representa vectores de ataque conocidos (exploits de Adobe/PDF, macros incrustadas o scripts maliciosos). Thesis Consensus garantiza **100% de inmunidad**:

1. **Sin Almacenamiento en Disco de Binarios:** No se crea ningún archivo binario ejecutable ni archivo `.pdf` temporal en tu sistema de archivos.
2. **Procesamiento Estrictamente en Memoria:** Las solicitudes a PDFs abiertos se descargan como un flujo de bytes en `io.BytesIO` y son leídas por el analizador en memoria `pypdf`, el cual solo extrae cadenas de texto plano UTF-8 y descarta por diseño scripts, formularios y acciones automáticas.
3. **Sanitización HTML:** Al procesar páginas web, se eliminan todas las etiquetas `<script>`, `<style>`, `<iframe>` y manejadores de eventos JavaScript.
4. **Bases Indexadas Confiables:** Las fuentes provienen exclusivamente de las APIs académicas oficiales (OpenAlex y Crossref).

---

## 5. Redacción Multi-Paper y Estándar APA 7ma Edición

En un marco teórico de tesis no se citan artículos aislados de forma inconexa. El módulo `synthesizer.py` genera **3 opciones de redacción integrada** en **español académico formal**:

### Opción A: Redacción Narrativa Dialéctica
Conecta múltiples autores en un discurso continuo utilizando conectores de contraste y adición:
> *"En el análisis de los fundamentos vinculados a [Tema], la literatura especializada converge en puntos críticos de gestión. Por un lado, según destacan **Marrone et al. (2014)**, las organizaciones priorizan procesos de nivel operativo. En esta misma línea, **Palilingan y Batmetan (2018)** complementan esta perspectiva al demostrar que el 84.5% de los incidentes pueden resolverse de manera ágil. De manera concordante, estos autores coinciden en que..."*

### Opción B: Enfoque por Tipología de Evidencia
Separa la evidencia práctica en universidades de los modelos cuantitativos:
> *"A nivel empírico en centros de educación superior, los estudios de caso desarrollados por **Ibrahim y Hamarash (2025)** demuestran que la estructuración formal mejora los tiempos de respuesta. Por otra parte, desde una aproximación de métricas de servicio, autores como **Babar et al. (2025)** subrayan que la automatización previene cuellos de botella..."*

### Opción C: Citación Parentética Agrupada (APA 7)
Agrupa las fuentes ordenadas alfabéticamente y separadas por punto y coma:
> *"... resultan determinantes para resolver la congestión operativa y optimizar la atención de incidencias en mesas de ayuda académicas **(Babar, 2025; Ibrahim y Hamarash, 2025; Marrone et al., 2014)**."*

### Formato de Referencia Bibliográfica Completa (APA 7):
- **Formato:** `Apellido, Inicial(es). (Año). Título del artículo en sentence case. *Nombre de la Revista*, *volumen*(número), páginas. https://doi.org/...`
- **Sentence Case:** Se preservan acrónimos como ITIL, ITSM, SLA, AI, IEEE.
- **DOI Seguro:** Enlace activo estándar `https://doi.org/...` sin punto final.

---

## 6. Configuración Centralizada (`constants.py`)

Todas las opciones globales se configuran en [`thesis_consensus/constants.py`](file:///Users/jhan/Documents/Proyectos/codigo_para_buscar_papers_sobre_tema_en_especifico/thesis_consensus/constants.py):

| Variable | Valor por Defecto | Propósito |
| :--- | :--- | :--- |
| `DEFAULT_LANGUAGE` | `"es"` | Idioma de redacción de los párrafos y reportes |
| `DEFAULT_RELEVANCE_THRESHOLD` | `0.80` (80%) | Umbral de aprobación estándar del modelo de decisión |
| `STRICT_RELEVANCE_THRESHOLD` | `0.85` (85%) | Umbral estricto para máxima rigurosidad |
| `MINIMUM_RIGOR_SCORE` | `1.6 / 3.0` | Calidad metodológica mínima exigida |
| `UNSLOTH_DEFAULT_URL` | `http://localhost:8888/v1/systemone` | Endpoint del modelo de decisión Laya |
| `DEFAULT_MIN_PUBLICATION_YEAR`| `2015` | Garantiza literatura actualizada de los últimos años |
| `DEFAULT_SEARCH_LIMIT` | `15` | Cantidad de papers candidatos a explorar por tema |

---

## 7. Modos de Uso y Ejecución por Lote (Batch)

### A. Evaluar Múltiples Preguntas de Tesis en un Solo Comando
```bash
python main.py --topic \
  "How is IT Service Management (ITSM) or ITIL implemented in higher education institutions and university help desks?" \
  "What are the challenges, ticket volume overloads, and bottlenecks in university IT support and help desk services?" \
  --threshold 0.80 \
  --out-md "fundamentos_teoricos_tesis.md" \
  --out-bib "referencias_tesis.bib"
```

### B. Cargar Preguntas desde un Archivo (`preguntas.txt`)
Crea un archivo de texto con una pregunta por línea:
```text
How is IT Service Management (ITSM) or ITIL implemented in higher education institutions?
What are the challenges and bottlenecks in university IT support and help desk services?
Impact of ITIL incident management and service level agreements (SLAs) on user satisfaction
```
Y ejecútalo con:
```bash
python main.py --file preguntas.txt --threshold 0.85
```

### C. Menú Visual Interactivo
```bash
python main.py --interactive
```

### D. Usando Unsloth Desktop (Laya)
1. Abre la aplicación **Unsloth Desktop**.
2. Ve a **Settings → API → Decision API** y activa **Serve requests**.
3. Ejecuta el comando agregando `--engine laya`:
   ```bash
   python main.py --topic "Tu tema" --engine laya --threshold 0.80
   ```

---

## 8. Tipado Estricto (Cero Any) y Pruebas Unitarias

El código fue diseñado bajo las mejores prácticas de ingeniería de software en Python:
- **Cero uso de `Any`:** Cada estructura, diccionario y parámetro posee tipos concretos (`str`, `int`, `float`, `Author`, `PaperMetadata`, `DecisionEvaluation`, etc.).
- **Validación con Mypy:**
  ```bash
  mypy thesis_consensus
  # Resultado: Success: no issues found in 19 source files
  ```
- **Pruebas Unitarias Automatizadas:**
  ```bash
  python -m unittest discover tests
  # Resultado: Ran 7 tests in 0.002s - OK
  ```

---

## 📄 Archivos Generados Listos para tu Tesis

Al finalizar la ejecución, encontrarás:
1. **[`fundamentos_teoricos_tesis.md`](file:///Users/jhan/Documents/Proyectos/codigo_para_buscar_papers_sobre_tema_en_especifico/fundamentos_teoricos_tesis.md):** Documento estructurado con tabla de contenidos, párrafos redactados con citas narrativas y parentéticas, tablas de decisión que justifican cada elección y bibliografía general unificada sin duplicados.
2. **[`referencias_tesis.bib`](file:///Users/jhan/Documents/Proyectos/codigo_para_buscar_papers_sobre_tema_en_especifico/referencias_tesis.bib):** Archivo BibTeX unificado listo para importar en **Zotero**, **Mendeley** o tu proyecto en **Overleaf / LaTeX**.
