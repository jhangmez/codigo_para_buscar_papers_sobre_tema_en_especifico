# 🎓 Thesis Consensus: Buscador y Evaluador de Literatura Científica para Tesis

Sistema automatizado en Python para tesistas que necesitan **fundamentar afirmaciones teóricas** con literatura científica arbitrada, evaluada mediante **modelos de decisión (Unsloth Laya / Jev API / Heurístico con umbral alto 80%-85%)** y formateada bajo las normas oficiales **APA 7ma Edición**.

---

## 🚀 Nuevas Características y Mejoras Implementadas

1. **Síntesis Teórica Multi-Paper Integrada**:
   - En lugar de citas aisladas de un solo artículo, ahora genera párrafos fluidos que **conectan y contrastan múltiples autores** dentro de una misma sección:
     - **Opción A (Narrativa Dialéctica)**: Conecta posturas operativas y estratégicas (*"Por un lado, según destacan Autor1 (Año)... En esta misma línea, Autor2 (Año) complementan al demostrar que..."*).
     - **Opción B (Por Enfoque y Tipología)**: Separa estudios de caso empíricos en universidades frente a modelos teóricos o métricas de tickets.
     - **Opción C (Cita Parentética Agrupada APA 7)**: Agrupa múltiples autores en una sola afirmación formal (*"(Autor1, 2020; Autor2, 2022; Autor3, 2024)"*).
2. **Redacción 100% en Español Académico**:
   - Controlado mediante la variable central `DEFAULT_LANGUAGE = "es"`.
   - Normaliza y traduce los hallazgos y métricas del inglés al español formal, evitando fragmentos mezclados.
3. **Módulo Centralizado de Constantes (`thesis_consensus/constants.py`)**:
   - Todas las configuraciones (URLs, umbrales, idioma, límites, timeouts, léxico y acrónimos) se gestionan en un único punto.
4. **Umbral de Decisión Exigente (80% - 85%)**:
   - Para garantizar que solo ingresen a tu tesis fuentes de máxima pertinencia científica, se aplica un corte estricto del **80% o 85%**.
5. **Tarjeta de Justificación del Modelo de Decisión (El "Por qué se escogieron")**:
   - Cada sección incluye una tabla detallando: probabilidad de relevancia, cumplimiento del umbral, tipología clasificada, rigor metodológico y justificación de elección.
6. **Procesamiento de Múltiples Preguntas Simultáneas (Batch)**:
   - Permite consultar 5, 10 o más preguntas de tesis juntas sin desorden.
   - Genera un reporte maestro en Markdown con **índice interactivo**, secciones diferenciadas y una **bibliografía general única y deduplicada al final**.
7. **Código con Tipado Estricto (Cero `Any`)**:
   - 100% validado con `mypy` sin errores ni advertencias.

---

## 🛠️ Instalación y Requisitos

Requiere Python 3.10 o superior (compatible con Python 3.14).

```bash
# 1. Activar entorno virtual
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt
```

---

## 📖 Modos de Uso

### 1. Evaluar Múltiples Preguntas de Tesis en Lote (Batch)
Puedes pasar varias preguntas juntas en la misma línea de comandos:

```bash
python main.py --topic \
  "How is IT Service Management (ITSM) or ITIL implemented in higher education institutions and university help desks?" \
  "What are the challenges, ticket volume overloads, and bottlenecks in university IT support and help desk services?" \
  --threshold 0.80 \
  --out-md "fundamentos_teoricos_tesis.md" \
  --out-bib "referencias_tesis.bib"
```

### 2. Cargar Preguntas desde un Archivo de Texto
Crea un archivo `preguntas.txt` con un tema o afirmación por línea y ejecútalo así:

```bash
python main.py --file preguntas.txt --threshold 0.85
```

### 3. Modo Interactivo con Menú Visual
```bash
python main.py --interactive
```

---

## 📁 Arquitectura del Proyecto

```
├── thesis_consensus/
│   ├── constants.py           # TODAS las constantes centrales (umbrales, idioma, endpoints, léxico)
│   ├── models.py              # Pydantic Models con tipado estricto (cero Any)
│   ├── apa7.py                # Reglas estrictas de citación y referenciación APA 7
│   ├── synthesizer.py         # Síntesis multi-paper, dialéctica y traducción a español
│   ├── agent.py               # Agente orquestador (individual y batch)
│   ├── exporter.py            # Generador de Markdown con índice, tarjetas de decisión y BibTeX único
│   ├── cli.py                 # Interfaz de consola visual con tablas Rich
│   ├── providers/
│   │   ├── base.py            # Interfaz BaseAcademicProvider
│   │   ├── openalex.py        # Conector OpenAlex (resúmenes invertidos sin malware)
│   │   ├── crossref.py        # Conector Crossref (metadatos DOI y revistas)
│   │   └── composite.py       # Búsqueda federada combinada y deduplicada
│   └── decision/
│       ├── protocol.py        # Protocolo BaseDecisionJudge con umbrales configurables
│       ├── unsloth_laya.py    # Integración con Unsloth Laya (Jev API /v1/systemone)
│       ├── openai_judge.py    # Integración con Ollama / OpenAI
│       └── heuristic.py       # Evaluador semántico por facetas conceptuales (umbral 80%-85%)
├── main.py                    # Punto de entrada ejecutable
├── tests/
│   └── test_consensus.py      # Pruebas unitarias completas
└── requirements.txt           # Dependencias del proyecto
```
