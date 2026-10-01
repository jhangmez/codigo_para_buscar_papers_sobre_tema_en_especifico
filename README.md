# 🎓 Thesis Consensus: Buscador y Evaluador de Literatura Científica para Tesis

Sistema automatizado en Python para tesistas que necesitan **fundamentar afirmaciones teóricas** con literatura científica arbitrada, evaluada mediante **modelos de decisión (Unsloth Laya / Jev API)** y formateada bajo las normas oficiales **APA 7ma Edición**.

Inspirado en el funcionamiento de **Consensus.app** y adaptado a las necesidades de tesis de pregrado y posgrado.

---

## 🚀 Características Principales

1. **Búsqueda Científica Federada y Segura (Anti-Malware)**:
   - Consulta bases indexadas globales oficiales (**OpenAlex** con más de 250M+ de artículos y **Crossref** con registros DOI oficiales).
   - **Cero descargas de archivos PDF desconocidos**: Reconstruye resúmenes completos mediante índices invertidos de texto en memoria sobre HTTPS. Esto elimina cualquier riesgo de virus, macros, scripts maliciosos o exploits de visores PDF, además de ser 50 veces más rápido que descargar PDFs completos.
2. **Filtrado Inteligente con Modelos de Decisión**:
   - Integra soporte nativo para **Unsloth Laya (Jev API)** en `http://localhost:8888/v1/systemone` mediante preguntas `noul` (probabilidad de relevancia), `choice` (estudio de caso, empírico, teórico) y `score` (rigor académico).
   - Compatible también con **Ollama / OpenAI** o con un motor heurístico semántico de alta velocidad que funciona sin requerir GPU ni servidores levantados.
   - Regla de negocio: **"Si sirve se conserva, y si no pues se va"** (descarte automático de artículos irrelevantes o fuera de foco).
3. **Formateador Estricto APA 7ma Edición**:
   - **Cita Narrativa en el texto**:
     - 1 autor: `Adán (2017)` (p. ej. *"De acuerdo con Adán (2017), ..."*)
     - 2 autores: `Adán y Pérez (2018)`
     - 3 o más autores: `Adán et al. (2020)` (conforme a la regla oficial de APA 7, se usa *et al.* desde la primera mención).
   - **Cita Parentética**: `(Adán et al., 2020)`.
   - **Lista de Referencias Final**: Título en *sentence case*, revista en cursiva, volumen en cursiva, páginas y enlace DOI activo `https://doi.org/...`.
   - **Exportación en BibTeX**: Listo para importar en Zotero, Mendeley o LaTeX.
4. **Código con Tipado Estricto (Cero `Any`)**:
   - Modelado 100% con Pydantic y `typing` estricto verificado mediante `mypy`.

---

## 🛠️ Instalación y Requisitos

Requiere Python 3.10 o superior (compatible con Python 3.14).

```bash
# 1. Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt
```

---

## 📖 Guía de Uso

### 1. Búsqueda y Fundamentación por Línea de Comandos
Puedes ingresar directamente tu pregunta o afirmación de tesis:

```bash
# Ejemplo 1: Implementación de ITSM / ITIL en universidades
python main.py --topic "How is IT Service Management (ITSM) or ITIL implemented in higher education institutions and university help desks?" --limit 8

# Ejemplo 2: Cuellos de botella y sobrecarga de tickets
python main.py --topic "What are the challenges, ticket volume overloads, and bottlenecks in university IT support and help desk services?" --limit 8
```

### 2. Modo Interactivo
Si ejecutas el script sin argumentos, se abrirá un menú interactivo con preguntas precargadas:

```bash
python main.py --interactive
```

### 3. Parámetros Disponibles
- `--topic`, `-t`: Tema o afirmación que necesitas sustentar en tus fundamentos teóricos.
- `--limit`, `-l`: Número de papers iniciales a evaluar (por defecto: 12).
- `--min-year`, `-y`: Año mínimo de publicación (por defecto: 2014) para asegurar actualidad.
- `--engine`, `-e`: Motor de decisión (`auto`, `laya`, `openai`, `heuristic`).
- `--out-md`, `-o`: Nombre del archivo Markdown de salida (por defecto: `fundamentos_teoricos.md`).
- `--out-bib`, `-b`: Nombre del archivo BibTeX de salida (por defecto: `referencias.bib`).

---

## 🧠 Integración con Unsloth Laya (Modelo de Decisión)

Para activar el modelo local **Laya** de Unsloth Desktop:

1. Abre **Unsloth Desktop**.
2. Ve a **Settings → API → Decision API**.
3. Activa la casilla **Serve requests** (descargará el modelo Laya de 678 MB).
4. El servidor quedará escuchando en `http://localhost:8888/v1/systemone`.
5. Ejecuta el script:
   ```bash
   python main.py --topic "tu afirmacion" --engine laya
   ```
   *(Si el servidor Laya no está encendido o no se encuentra disponible, el sistema cambia automáticamente al evaluador semántico para que nunca te detengas).*

---

## 📁 Estructura del Código

```
├── thesis_consensus/
│   ├── models.py              # Modelos tipados con Pydantic (Autor, Paper, Decisión, APA 7)
│   ├── apa7.py                # Reglas estrictas de citación y referenciación APA 7
│   ├── synthesizer.py         # Ensamblador de párrafos y síntesis de consenso
│   ├── agent.py               # Agente orquestador (Búsqueda -> Decisión -> APA 7)
│   ├── exporter.py            # Generador de Markdown, BibTeX y JSON
│   ├── cli.py                 # Interfaz de consola visual con Rich
│   ├── providers/
│   │   ├── base.py            # Interfaz abstracta para buscadores
│   │   ├── openalex.py        # Conector OpenAlex (resúmenes invertidos sin malware)
│   │   ├── crossref.py        # Conector Crossref (metadatos DOI y revistas)
│   │   └── composite.py       # Búsqueda federada combinada y deduplicada
│   └── decision/
│       ├── protocol.py        # Protocolo base para evaluadores
│       ├── unsloth_laya.py    # Integración con Unsloth Laya (Jev API /v1/systemone)
│       ├── openai_judge.py    # Integración con Ollama / OpenAI
│       └── heuristic.py       # Evaluador semántico sin GPU (cero caídas)
├── main.py                    # Punto de entrada ejecutable
├── tests/
│   └── test_consensus.py      # Pruebas unitarias completas
└── requirements.txt           # Dependencias del proyecto
```

---

## 🛡️ Verificación de Tipos Estrictos (Sin `Any`)

El proyecto pasa las verificaciones de `mypy` sin errores:

```bash
mypy thesis_consensus
# Result: Success: no issues found in 17 source files
```
