# Glosario de Indicadores

> Referencia de los indicadores SIMCE y de Desarrollo Personal y Social (IDPS),
> y de la comparación por Grupo Socioeconómico (GSE). Fuente de las definiciones:
> Agencia de Calidad de la Educación / MINEDUC.

---

## 1. Grupo Socioeconómico (GSE)

Clasificación del MINEDUC (Agencia de Calidad de la Educación) que agrupa a los
establecimientos según el perfil socioeconómico de sus familias. Se construye con
**análisis de conglomerados (clusters)** sobre:

- **IVE** (Índice de Vulnerabilidad del Establecimiento), proporcionado por JUNAEB.
- Información de **madres, padres y apoderados** (escolaridad e ingreso del hogar),
  recogida en los *Cuestionarios de Calidad y Contexto*.

**Grupos**: 5 → *Bajo (A), Medio-Bajo (B), Medio (C), Medio-Alto (D), Alto (E)*.

**Comparación "colegios similares"**: el resultado de un colegio se compara contra el
**promedio de los colegios de su mismo GSE**. El campo `indicadores.comparacion_gse_glosa`
ya contiene ese juicio:

| Valor | Significado | Semáforo en UI |
|---|---|---|
| `Más alto` | supera el promedio de su grupo | 🟢 verde |
| `Similar` | en la media de su grupo | ⚪ gris |
| `Más bajo` | bajo el promedio de su grupo | 🔴 rojo |
| `No es posible comparar…` / vacío / `NA` | sin dato (pocos evaluados) | gris apagado |

> **Importante**: el color es **relativo al GSE propio** de cada colegio. No es comparable
> entre colegios de distinto GSE; el puntaje crudo sí lo es (misma escala y prueba).

**Fuente**: Agencia de Calidad de la Educación, "Descripción de grupos socioeconómicos (GSE)"
— `s3.amazonaws.com/archivos-web.agenciaeducacion.cl/resultados-simce/descarga/Simce+Descripcion+GSE.pdf`

---

## 2. Indicadores SIMCE

Puntaje de Lenguaje y Matemática (escala ~0–400), evaluado en Enseñanza Básica y Media.
El juicio GSE (Más alto/Similar/Más bajo) es el dato principal; el puntaje crudo es
secundario porque correlaciona con el nivel socioeconómico.

| Indicador | Nota |
|---|---|
| Lenguaje | Puntaje SIMCE de Lenguaje (lectura) |
| Matemática | Puntaje SIMCE de Matemática |

---

## 3. Indicadores de Desarrollo Personal y Social (IDPS)

Índices **0–100** basados en **cuestionarios (percepciones autodeclaradas)** de estudiantes,
docentes y apoderados — no pruebas objetivas. Complementan al SIMCE ampliando la noción de
calidad educativa.

| Indicador | Definición | Subdimensiones |
|---|---|---|
| **Autoestima académica y motivación escolar** | Cómo el estudiante valora su capacidad de aprender y su disposición hacia el aprendizaje y el logro académico. | *Autopercepción/autovaloración académica* (aptitudes, posibilidades de superarse) · *Motivación escolar* (interés, expectativas, actitud frente a dificultades). |
| **Clima de convivencia escolar** | Percepción de estudiantes, docentes y apoderados sobre un ambiente **de respeto, organizado y seguro**. | *Ambiente de respeto* (trato, diversidad, no discriminación) · *Ambiente organizado* (normas claras) · *Ambiente seguro*. |
| **Participación y formación ciudadana** | Actitud del estudiante hacia su colegio y percepción de cuánto se fomenta la participación, el compromiso y la **vida democrática**. | *Sentido de pertenencia* · *Participación* · *Vida democrática*. |
| **Hábitos de vida saludable** | Actitudes y conductas **autodeclaradas** sobre vida saludable + percepción de cuánto el colegio promueve hábitos sanos. | *Hábitos alimenticios* · *Hábitos de vida activa* (actividad física). |

**Fuentes**:
- Curriculum Nacional — "Indicadores de Desarrollo Personal y Social (IDPS)": `https://www.curriculumnacional.cl/evaluacion/estandares-indicadores/indicadores-desarrollo-personal-social`
- Agencia de Calidad — "Marco de Evaluación IDPS 2025": `archivos.agenciaeducacion.cl/Marco+Evaluacion+IDPS+2025+v3.pdf`

---

## 4. Notas de implementación

- `indicadores.descripcion_indicador` viene **vacío** en el dataset (34.716 filas): las
  definiciones se hardcodean en el frontend (`frontend/src/lib/format.ts`, `indicadorDef()`),
  no se leen del API.
- `indicadores.nivel_indicador` ("Básica"/"Media") = **nivel educativo evaluado**, NO "promedio".
  En UI se muestra como "Enseñanza Básica"/"Enseñanza Media".
- `indicadores.comparacion_gse_numero` **no** identifica el GSE ni el ranking (sus valores se
  solapan entre "Más alto"/"Similar"/"Más bajo"); no usar para exponer posición.
- **Roadmap post-MVP (Opción B)**: para mostrar "GSE: Alto/Medio-Bajo" por colegio se requiere
  ingerir el GSE por RBD desde una fuente adicional (SIMCE / Agencia de Calidad) y cruzar por RBD.
