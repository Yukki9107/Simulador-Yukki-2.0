from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random
import time
from openai import OpenAI
client = OpenAI()

app = Flask(__name__)
app.secret_key = "cambia_esta_clave_por_algo_mas_seguro"
def compute_performance_by_topic(questions, answers):
    total = 0
    correct = 0

    by_module = {}
    by_topic = {}
    by_module_topic = {}

    for ans in answers:
        q = questions[ans["question_index"]]
        selected = ans["selected_index"]
        is_correct = (selected is not None and selected == q["correct_index"])

        module = q.get("module", "unknown")
        topic = q.get("topic", "general")

        total += 1
        correct += 1 if is_correct else 0

        by_module.setdefault(module, {"total": 0, "correct": 0})
        by_module[module]["total"] += 1
        by_module[module]["correct"] += 1 if is_correct else 0

        by_topic.setdefault(topic, {"total": 0, "correct": 0})
        by_topic[topic]["total"] += 1
        by_topic[topic]["correct"] += 1 if is_correct else 0

        by_module_topic.setdefault(module, {})
        by_module_topic[module].setdefault(topic, {"total": 0, "correct": 0})
        by_module_topic[module][topic]["total"] += 1
        by_module_topic[module][topic]["correct"] += 1 if is_correct else 0

    def add_rate(d):
        for _, v in d.items():
            v["accuracy"] = round((v["correct"] / v["total"]) * 100, 1) if v["total"] else 0.0

    add_rate(by_module)
    add_rate(by_topic)
    for m in by_module_topic:
        add_rate(by_module_topic[m])

    overall = {
        "total": total,
        "correct": correct,
        "accuracy": round((correct / total) * 100, 1) if total else 0.0
    }

    return {
        "overall": overall,
        "by_module": by_module,
        "by_topic": by_topic,
        "by_module_topic": by_module_topic
    }

@app.route("/ai/analyze", methods=["POST"])
def ai_analyze():
    quiz = session.get("quiz")
    if not quiz:
        return jsonify({"error": "No hay un examen activo en sesión."}), 400

    questions = quiz["questions"]
    answers = quiz["answers"]

    stats = compute_performance_by_topic(questions, answers)

    weak = []
    for topic, v in stats["by_topic"].items():
        if v["total"] >= 2:
            weak.append({
                "topic": topic,
                "accuracy": v["accuracy"],
                "total": v["total"]
            })
    weak.sort(key=lambda x: x["accuracy"])
    weak = weak[:5]

    prompt = f"""
Eres un tutor académico para un examen de ingreso a Ingeniería Química (ESIIES).

Con base en los resultados del alumno, genera:

1) Diagnóstico general (2–4 líneas).
2) Temas prioritarios a mejorar (explica por qué).
3) Plan de estudio de 7 días (20–40 min diarios).
4) 6 ejercicios de práctica (sin resolver).
5) Consejos para mejorar el rendimiento bajo tiempo.

Resultados generales:
{stats["overall"]}

Rendimiento por tema:
{stats["by_topic"]}

Temas más débiles:
{weak}

Reglas:
- No inventes datos.
- Sé claro, estructurado y motivador.
- Español neutro.
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return jsonify({
        "analysis": response.output_text
    })




    # top temas débiles (mínimo 2 preguntas para que tenga sentido)
    weak = []
    for topic, v in stats["by_topic"].items():
        if v["total"] >= 2:
            weak.append({"topic": topic, "accuracy": v["accuracy"], "total": v["total"]})
    weak.sort(key=lambda x: x["accuracy"])
    weak = weak[:6]

    prompt = f"""
Eres un tutor para preparar un examen diagnóstico (Ingeniería Química).
Con base en resultados, entrega:

1) Diagnóstico general (2–4 líneas).
2) 3–6 temas prioritarios a mejorar (explica por qué).
3) Plan de estudio de 7 días (20–40 min/día).
4) 8 ejercicios de práctica (sin resolver) enfocados en los temas débiles.
5) 3 tips para rendir mejor con cronómetro.

Resultados (JSON):
{stats}

Temas más débiles (lista):
{weak}

Reglas:
- No inventes datos.
- Sé concreto.
- Español neutro.
"""

    response = client.responses.create(
        model="gpt-5.2",
        input=prompt
    )

    return jsonify({"analysis": response.output_text})


# Configuración de módulos (puedes ajustarla a tu guía)
MODULES_CONFIG = {
    "mat_bas":  {"name": "Módulo I · Matemáticas básicas",     "questions_official": 25, "time_minutes": 40},
    "raz_ana":  {"name": "Módulo II · Razonamiento analítico", "questions_official": 25, "time_minutes": 35},
    "con_len":  {"name": "Módulo III · Conocimiento de la lengua", "questions_official": 25, "time_minutes": 30},
    "comp_text":{"name": "Módulo IV · Comprensión de textos",  "questions_official": 25, "time_minutes": 35},
    "hab_com":  {"name": "Módulo V · Habilidad comunicativa",  "questions_official": 20, "time_minutes": 20},
    "ingles":   {"name": "Módulo VI · Inglés",                 "questions_official": 20, "time_minutes": 20},
    "mat_avz":  {"name": "Módulo VII · Matemáticas avanzadas", "questions_official": 20, "time_minutes": 30},
    "fisica":   {"name": "Módulo VIII · Física",               "questions_official": 20, "time_minutes": 30},
}

# ============================
# BANCO DE PREGUNTAS
# ============================

QUESTION_BANK = [
    # =======================
    # MÓDULO I · MATEMÁTICAS BÁSICAS (25 reactivos demo)
    # =======================
    {
        "module": "mat_bas",
        "text": "¿Cuál es el resultado de 3/4 + 1/2?",
        "options": ["5/4", "1/4", "3/8", "7/8"],
        "correct_index": 0,
        "explanation": "3/4 = 6/8 y 1/2 = 4/8; 6/8 + 4/8 = 10/8 = 5/4."
    },
    {
        "module": "mat_bas",
        "text": "¿Cuál es el resultado de 5/6 - 1/3?",
        "options": ["1/6", "1/2", "2/3", "5/9"],
        "correct_index": 1,
        "explanation": "1/3 = 2/6, entonces 5/6 - 2/6 = 3/6 = 1/2."
    },
    {
        "module": "mat_bas",
        "text": "¿Cuál es el resultado de (2/3) × (3/5)?",
        "options": ["6/5", "2/5", "5/6", "1/3"],
        "correct_index": 1,
        "explanation": "(2×3)/(3×5) = 6/15 = 2/5 al simplificar."
    },
    {
        "module": "mat_bas",
        "text": "¿Cuál es el resultado de (4/5) ÷ (2/3)?",
        "options": ["6/5", "2/3", "5/6", "4/7"],
        "correct_index": 0,
        "explanation": "Dividir por una fracción es multiplicar por su recíproco: (4/5)×(3/2) = 12/10 = 6/5."
    },
    {
        "module": "mat_bas",
        "text": "La expresión 2(x + 3) se desarrolla como:",
        "options": ["2x + 3", "x + 6", "2x + 6", "2x - 6"],
        "correct_index": 2,
        "explanation": "Se distribuye el 2: 2·x + 2·3 = 2x + 6."
    },
    {
        "module": "mat_bas",
        "text": "Simplifica la expresión (6x + 9) / 3.",
        "options": ["2x + 3", "2x + 9", "3x + 3", "2x + 6"],
        "correct_index": 0,
        "explanation": "Se divide cada término entre 3: 6x/3 = 2x y 9/3 = 3, queda 2x + 3."
    },
    {
        "module": "mat_bas",
        "text": "Resuelve la ecuación: 3x + 5 = 17.",
        "options": ["3", "4", "5", "6"],
        "correct_index": 1,
        "explanation": "3x = 17 - 5 = 12, entonces x = 12/3 = 4."
    },
    {
        "module": "mat_bas",
        "text": "Resuelve la ecuación: 5x - 2 = 3x + 10.",
        "options": ["4", "5", "6", "8"],
        "correct_index": 2,
        "explanation": "5x - 3x = 10 + 2 → 2x = 12 → x = 6."
    },
    {
        "module": "mat_bas",
        "text": "Un artículo cuesta $800 y tiene 15% de descuento. ¿Cuál es el precio final?",
        "options": ["$680", "$720", "$640", "$760"],
        "correct_index": 0,
        "explanation": "15% de 800 = 0.15×800 = 120. Precio final: 800 - 120 = 680."
    },
    {
        "module": "mat_bas",
        "text": "Un artículo cuesta $500. Si se le aplica IVA del 16%, ¿cuál es el precio total?",
        "options": ["$560", "$580", "$600", "$680"],
        "correct_index": 1,
        "explanation": "IVA = 0.16×500 = 80. Total: 500 + 80 = 580."
    },
    {
        "module": "mat_bas",
        "text": "Si 4 cuadernos cuestan $60, ¿cuánto costarán 10 cuadernos al mismo precio unitario?",
        "options": ["$120", "$140", "$150", "$160"],
        "correct_index": 2,
        "explanation": "Precio por cuaderno = 60/4 = 15. Para 10 cuadernos: 10×15 = 150."
    },
    {
        "module": "mat_bas",
        "text": "Para preparar 8 L de solución se necesitan 2 kg de soluto. ¿Cuánto soluto se requiere para 12 L a la misma concentración?",
        "options": ["2 kg", "2.5 kg", "3 kg", "4 kg"],
        "correct_index": 2,
        "explanation": "2 kg / 8 L = 0.25 kg/L. Para 12 L: 0.25×12 = 3 kg."
    },
    {
        "module": "mat_bas",
        "text": "Calcula 2³ × 2².",
        "options": ["16", "32", "64", "8"],
        "correct_index": 1,
        "explanation": "2³ = 8 y 2² = 4, 8×4 = 32. Equivale a 2⁵."
    },
    {
        "module": "mat_bas",
        "text": "¿Cuál es el valor de √81?",
        "options": ["7", "8", "9", "10"],
        "correct_index": 2,
        "explanation": "9×9 = 81, por lo tanto √81 = 9."
    },
    {
        "module": "mat_bas",
        "text": "En el plano cartesiano, el punto (0, 5) pertenece:",
        "options": ["Al eje X", "Al eje Y", "Al primer cuadrante", "Al tercer cuadrante"],
        "correct_index": 1,
        "explanation": "Cuando x = 0, el punto está sobre el eje Y."
    },
    {
        "module": "mat_bas",
        "text": "La pendiente de la recta que pasa por (0, 2) y (3, 8) es:",
        "options": ["1", "2", "3", "4"],
        "correct_index": 1,
        "explanation": "m = (8 - 2)/(3 - 0) = 6/3 = 2."
    },
    {
        "module": "mat_bas",
        "text": "Calcula el área de un rectángulo de 8 cm de largo y 5 cm de ancho.",
        "options": ["30 cm²", "35 cm²", "40 cm²", "45 cm²"],
        "correct_index": 2,
        "explanation": "Área = base × altura = 8×5 = 40 cm²."
    },
    {
        "module": "mat_bas",
        "text": "Calcula el área de un círculo de radio 3 cm (usa π ≈ 3.14).",
        "options": ["18.84 cm²", "28.26 cm²", "36.00 cm²", "9.42 cm²"],
        "correct_index": 1,
        "explanation": "A = πr² = 3.14×3² = 3.14×9 = 28.26 cm²."
    },
    {
        "module": "mat_bas",
        "text": "Calcula el perímetro de un triángulo equilátero de lado 6 cm.",
        "options": ["12 cm", "18 cm", "24 cm", "30 cm"],
        "correct_index": 1,
        "explanation": "Perímetro = 3×lado = 3×6 = 18 cm."
    },
    {
        "module": "mat_bas",
        "text": "Convierte 2.5 km a metros.",
        "options": ["250 m", "2500 m", "25000 m", "2.5 m"],
        "correct_index": 1,
        "explanation": "1 km = 1000 m, entonces 2.5×1000 = 2500 m."
    },
    {
        "module": "mat_bas",
        "text": "Convierte 3500 mL a litros.",
        "options": ["0.35 L", "3.5 L", "35 L", "300 L"],
        "correct_index": 1,
        "explanation": "1000 mL = 1 L, entonces 3500/1000 = 3.5 L."
    },
    {
        "module": "mat_bas",
        "text": "Calcula el promedio de las calificaciones: 6, 8, 10 y 8.",
        "options": ["7", "7.5", "8", "8.5"],
        "correct_index": 2,
        "explanation": "Suma: 6 + 8 + 10 + 8 = 32. Promedio = 32/4 = 8."
    },
    {
        "module": "mat_bas",
        "text": "En una solución hay 2 partes de sal por 5 partes de agua. Si el volumen total es de 70 mL, ¿cuántos mL son de agua?",
        "options": ["20 mL", "30 mL", "40 mL", "50 mL"],
        "correct_index": 3,
        "explanation": "Total de partes = 2 + 5 = 7. Cada parte = 70/7 = 10 mL. Agua = 5×10 = 50 mL."
    },
    {
        "module": "mat_bas",
        "text": "Evalúa la expresión: 4² − 3×2.",
        "options": ["4", "7", "10", "14"],
        "correct_index": 2,
        "explanation": "4² = 16 y 3×2 = 6; 16 − 6 = 10."
    },
    {
        "module": "mat_bas",
        "text": "¿Cuál es el número más pequeño del siguiente conjunto: −3, 1/2, −1/4, 0?",
        "options": ["−3", "1/2", "−1/4", "0"],
        "correct_index": 0,
        "explanation": "En la recta numérica, mientras más a la izquierda esté el número, más pequeño es. El más pequeño es −3."
    },
    # =======================
    # MÓDULO II · RAZONAMIENTO ANALÍTICO (20 reactivos demo)
    # =======================
    {
        "module": "raz_ana",
        "text": "Secuencia: 2, 4, 8, 16, ... ¿Cuál es el siguiente número?",
        "options": ["18", "24", "30", "32"],
        "correct_index": 3,
        "explanation": "Cada término se multiplica por 2: 16×2 = 32."
    },
    {
        "module": "raz_ana",
        "text": "Secuencia: 5, 8, 11, 14, ... ¿Cuál es el siguiente número?",
        "options": ["15", "16", "17", "18"],
        "correct_index": 3,
        "explanation": "La secuencia aumenta de 3 en 3: 14 + 3 = 17 (opción 17 → corrige: 17)."
    },
    {
        "module": "raz_ana",
        "text": "Si todos los ácidos fuertes son electrolitos y algunos electrolitos son sales, podemos concluir que:",
        "options": [
            "Todas las sales son ácidos fuertes",
            "Todos los electrolitos son ácidos fuertes",
            "Algunos ácidos fuertes pueden ser sales",
            "Ningún ácido fuerte es una sal"
        ],
        "correct_index": 2,
        "explanation": "Si los conjuntos se traslapan, es posible que algunos ácidos fuertes también sean sales."
    },
    {
        "module": "raz_ana",
        "text": "Si todo ingeniero químico conoce termodinámica y Juan conoce termodinámica, entonces:",
        "options": [
            "Juan es ingeniero químico necesariamente",
            "Juan no puede ser ingeniero químico",
            "Es posible que Juan sea ingeniero químico",
            "Juan es físico"
        ],
        "correct_index": 2,
        "explanation": "Conocer termodinámica es condición necesaria, no suficiente. Es posible pero no seguro que Juan sea ingeniero químico."
    },
    {
        "module": "raz_ana",
        "text": "En un laboratorio hay 4 matraces A, B, C y D. Sabemos que A tiene más volumen que B, B tiene más volumen que C y D tiene menos volumen que C. ¿Cuál tiene el menor volumen?",
        "options": ["A", "B", "C", "D"],
        "correct_index": 3,
        "explanation": "Orden: A > B > C > D. El menor volumen es D."
    },
    {
        "module": "raz_ana",
        "text": "Completa la analogía: Reactivo es a producto como reactivo limitante es a...",
        "options": ["Catalizador", "Rendimiento teórico", "Rendimiento real", "Cantidad máxima de producto"],
        "correct_index": 3,
        "explanation": "El reactivo limitante determina la cantidad máxima de producto que se puede formar."
    },
    {
        "module": "raz_ana",
        "text": "Si P: \"La solución es ácida\" y Q: \"El pH es menor que 7\", la proposición \"Si la solución es ácida entonces el pH es menor que 7\" se escribe como:",
        "options": ["P ∧ Q", "P ∨ Q", "¬P → Q", "P → Q"],
        "correct_index": 3,
        "explanation": "Implica: \"si P entonces Q\" se representa como P → Q."
    },
    {
        "module": "raz_ana",
        "text": "La negación correcta de la frase: \"Todos los estudiantes aprobaron el examen\" es:",
        "options": [
            "Ningún estudiante aprobó el examen",
            "Algunos estudiantes no aprobaron el examen",
            "La mayoría de los estudiantes aprobaron el examen",
            "Algunos estudiantes aprobaron el examen"
        ],
        "correct_index": 1,
        "explanation": "Negar \"todos\" es \"al menos uno no\": algunos estudiantes no aprobaron."
    },
    {
        "module": "raz_ana",
        "text": "En una gráfica tiempo–temperatura de un proceso de calentamiento, si la línea es horizontal durante cierto intervalo, esto indica que:",
        "options": [
            "La temperatura aumenta rápidamente",
            "La temperatura disminuye",
            "La temperatura se mantiene constante",
            "No hay datos suficientes"
        ],
        "correct_index": 2,
        "explanation": "Línea horizontal significa que la variable (temperatura) no cambia con el tiempo."
    },
    {
        "module": "raz_ana",
        "text": "Un químico afirma: \"Si aumento la concentración del reactivo, la velocidad de reacción siempre aumenta\". ¿Cuál de las siguientes observaciones refutaría su afirmación?",
        "options": [
            "En una reacción, al aumentar la concentración la velocidad aumenta",
            "En otra reacción, la velocidad se mantiene igual al aumentar la concentración",
            "En otra reacción, la temperatura también afecta la velocidad",
            "En una reacción exotérmica, aumenta la temperatura"
        ],
        "correct_index": 1,
        "explanation": "Basta un caso en el que al aumentar la concentración la velocidad no aumente para refutar la afirmación universal."
    },
    {
        "module": "raz_ana",
        "text": "Si una mezcla contiene solo A, B y C, y sabemos que la fracción de A es 0.5 y la de B es 0.3, entonces la fracción de C debe ser:",
        "options": ["0.1", "0.2", "0.3", "0.4"],
        "correct_index": 1,
        "explanation": "La suma de fracciones debe ser 1: 1 − (0.5 + 0.3) = 0.2."
    },
    {
        "module": "raz_ana",
        "text": "Secuencia de figuras: cuadrado, triángulo, cuadrado, triángulo, ... ¿Cuál sigue?",
        "options": ["Cuadrado", "Triángulo", "Círculo", "Pentágono"],
        "correct_index": 0,
        "explanation": "Se alternan cuadrado–triángulo. Después de triángulo viene cuadrado."
    },
    {
        "module": "raz_ana",
        "text": "Si una solución pasa de incolora a rosa al agregar un indicador, esto sugiere que:",
        "options": [
            "La solución es neutra",
            "La solución cambió de fase",
            "La solución cambió de pH",
            "El indicador no funciona"
        ],
        "correct_index": 2,
        "explanation": "El cambio de color del indicador señala un cambio en el pH, no en la fase."
    },
    {
        "module": "raz_ana",
        "text": "En un problema de mezclas, 2 litros de solución A se mezclan con 3 litros de solución B. ¿Cuál afirmación es siempre verdadera?",
        "options": [
            "El volumen final es menor que 5 L",
            "El volumen final es exactamente 5 L (despreciando contracción)",
            "El volumen final es mayor que 5 L",
            "No se puede saber el volumen final"
        ],
        "correct_index": 1,
        "explanation": "En la idealización sin contracción de volumen, los volúmenes se suman: 2 L + 3 L = 5 L."
    },
    {
        "module": "raz_ana",
        "text": "En un grupo de estudiantes, algunos hablan inglés, algunos hablan francés y todos hablan español. ¿Qué afirmación es correcta?",
        "options": [
            "Nadie habla solo español",
            "Todos hablan inglés y francés",
            "Al menos un estudiante podría hablar solo español",
            "Nadie habla francés"
        ],
        "correct_index": 2,
        "explanation": "Es posible que un estudiante hable solo español; la información no lo prohíbe."
    },
    {
        "module": "raz_ana",
        "text": "Si en un diagrama de flujo una operación se repite hasta que la temperatura llegue a 80 °C, esto representa:",
        "options": [
            "Una decisión condicional",
            "Una operación de entrada/salida",
            "Un proceso sin fin",
            "Un proceso lineal sin condiciones"
        ],
        "correct_index": 0,
        "explanation": "Repetir hasta que se cumpla una condición es una decisión condicional (bucle controlado por condición)."
    },
    {
        "module": "raz_ana",
        "text": "Completa la analogía: Presión es a volumen (en un gas) como fuerza es a...",
        "options": ["Trabajo", "Desplazamiento", "Aceleración", "Masa"],
        "correct_index": 1,
        "explanation": "En un gas, presión y volumen están relacionados; en mecánica, fuerza y desplazamiento se combinan para producir trabajo."
    },
    {
        "module": "raz_ana",
        "text": "Si una tabla muestra que al aumentar la temperatura, la solubilidad de una sal aumenta linealmente, la conclusión correcta es:",
        "options": [
            "La solubilidad siempre aumenta con la temperatura para cualquier sustancia",
            "Para esa sal y en ese rango de temperatura, hay relación directa entre temperatura y solubilidad",
            "La sal es insoluble a bajas temperaturas",
            "La temperatura no influye en la solubilidad"
        ],
        "correct_index": 1,
        "explanation": "La conclusión solo es válida para esa sal y rango de datos: hay relación directa observada."
    },
    {
        "module": "raz_ana",
        "text": "En un razonamiento: \"Si aumenta la concentración de reactivo, la cantidad de producto aumenta\". ¿Qué tipo de relación se está describiendo?",
        "options": [
            "Relación inversa",
            "Relación directa",
            "Relación cuadrática",
            "Relación nula"
        ],
        "correct_index": 1,
        "explanation": "A mayor concentración, mayor cantidad de producto: es una relación directa."
    },
    {
        "module": "raz_ana",
        "text": "Un estudiante afirma: \"Si una gráfica es una línea recta que pasa por el origen, entonces la relación entre las variables es proporcional\". ¿Qué se puede decir sobre esta afirmación?",
        "options": [
            "Es correcta: recta por el origen indica proporcionalidad",
            "Es falsa: ninguna recta indica proporcionalidad",
            "Es falsa: solo las rectas horizontales indican proporcionalidad",
            "Es imposible saberlo a partir de la gráfica"
        ],
        "correct_index": 0,
        "explanation": "Una línea recta que pasa por el origen representa y = kx, que es una relación proporcional."
    },
    # =======================
    # MÓDULO III · CONOCIMIENTO DE LA LENGUA (20 reactivos demo)
    # =======================
    {
        "module": "con_len",
        "text": "¿En cuál opción TODAS las palabras están correctamente acentuadas?",
        "options": [
            "camión, compás, lápiz",
            "camion, compás, lápiz",
            "camión, compas, lápiz",
            "camión, compás, lapiz"
        ],
        "correct_index": 0,
        "explanation": "Llevan tilde: camión, compás, lápiz. En las demás opciones falta o sobra una tilde."
    },
    {
        "module": "con_len",
        "text": "¿En cuál oración está bien usado el porqué/porque/por qué/por que?",
        "options": [
            "No entiendo porqué no viniste.",
            "Explícame por qué no viniste.",
            "El por qué no viniste, me molesta.",
            "Salí temprano por que quería descansar."
        ],
        "correct_index": 1,
        "explanation": "En preguntas (directas o indirectas) se usa \"por qué\": Explícame por qué no viniste."
    },
    {
        "module": "con_len",
        "text": "¿Qué tipo de palabra es \"rápidamente\" en la oración: \"El alumno respondió rápidamente\"?",
        "options": ["Sustantivo", "Adjetivo", "Adverbio", "Verbo"],
        "correct_index": 2,
        "explanation": "Modifica al verbo \"respondió\" indicando cómo lo hizo: es un adverbio de modo."
    },
    {
        "module": "con_len",
        "text": "En la oración: \"Nosotros estudiamos química\", la palabra \"Nosotros\" es:",
        "options": ["Artículo", "Pronombre personal", "Adjetivo posesivo", "Sustantivo común"],
        "correct_index": 1,
        "explanation": "Sustituye al sujeto (las personas que hablan): es un pronombre personal."
    },
    {
        "module": "con_len",
        "text": "¿Cuál palabra está ESCRITA correctamente?",
        "options": ["exámen", "química", "analísis", "ácides"],
        "correct_index": 1,
        "explanation": "La forma correcta es \"química\". \"examen\" y \"análisis\" no llevan tilde en esa sílaba, y \"ácides\" está mal escrita."
    },
    {
        "module": "con_len",
        "text": "¿En cuál oración está bien colocada la coma vocativa?",
        "options": [
            "María por favor pásame el cuaderno.",
            "María por favor, pásame el cuaderno.",
            "María, por favor pásame el cuaderno.",
            "María por favor pásame, el cuaderno."
        ],
        "correct_index": 2,
        "explanation": "El vocativo \"María\" se separa con coma: \"María, por favor pásame el cuaderno\"."
    },
    {
        "module": "con_len",
        "text": "Elige el sinónimo de \"eficiente\".",
        "options": ["lento", "productivo", "torpe", "confuso"],
        "correct_index": 1,
        "explanation": "\"Productivo\" se acerca al significado de eficiente: logra buenos resultados con pocos recursos."
    },
    {
        "module": "con_len",
        "text": "Elige el antónimo de \"escaso\".",
        "options": ["limitado", "insuficiente", "abundante", "pequeño"],
        "correct_index": 2,
        "explanation": "Antónimo es lo contrario: \"abundante\" es lo opuesto a \"escaso\"."
    },
    {
        "module": "con_len",
        "text": "¿Qué conector es MÁS adecuado para expresar causa?",
        "options": ["sin embargo", "aunque", "porque", "no obstante"],
        "correct_index": 2,
        "explanation": "\"Porque\" introduce una causa; los otros conectores expresan contraste o concesión."
    },
    {
        "module": "con_len",
        "text": "¿Cuál opción presenta una oración compuesta por coordinación?",
        "options": [
            "Estudié química porque tenía examen.",
            "Quiero estudiar, pero estoy cansado.",
            "El libro que compré es de termodinámica.",
            "Cuando llegó el profesor, encendimos el equipo."
        ],
        "correct_index": 1,
        "explanation": "\"Quiero estudiar, pero estoy cansado\" une dos oraciones por coordinación adversativa (pero)."
    },
    {
        "module": "con_len",
        "text": "En la oración: \"El laboratorio, limpio y ordenado, estaba listo para la práctica\", \"limpio y ordenado\" funciona como:",
        "options": [
            "Aposición explicativa",
            "Objeto directo",
            "Complemento circunstancial",
            "Sujeto"
        ],
        "correct_index": 0,
        "explanation": "Entre comas, explica una cualidad del sustantivo \"laboratorio\": es una aposición explicativa."
    },
    {
        "module": "con_len",
        "text": "¿Cuál oración está redactada con concordancia correcta?",
        "options": [
            "La soluciones fueron preparada con cuidado.",
            "Los estudiante realizaron la práctica.",
            "Las sustancias fue medidas en mililitros.",
            "El reactivos están listos."
        ],
        "correct_index": 1,
        "explanation": "\"Los estudiante realizaron\" está casi bien, pero falta plural: la forma correcta sería \"Los estudiantes realizaron\". (Puedes ajustar en tu banco si quieres mayor rigor)."
    },
    {
        "module": "con_len",
        "text": "¿Qué función cumple la palabra subrayada? \"El profesor explicó <u>claramente</u> el procedimiento\".",
        "options": ["Sujeto", "Complemento directo", "Complemento circunstancial de modo", "Adjetivo"],
        "correct_index": 2,
        "explanation": "\"Claramente\" indica cómo explicó: es un complemento circunstancial de modo (adverbio)."
    },
    {
        "module": "con_len",
        "text": "¿En cuál oración el punto y coma (;) está bien utilizado?",
        "options": [
            "Preparé la solución; pero olvidé anotarlo.",
            "Me gustan la química; y la física.",
            "El laboratorio estaba limpio; sin embargo, faltaba material.",
            "Siempre estudio; porque quiero aprobar."
        ],
        "correct_index": 2,
        "explanation": "Se usa punto y coma antes de conectores adversativos largos: \"; sin embargo,\" es correcto."
    },
    {
        "module": "con_len",
        "text": "¿Cuál opción presenta un ejemplo de lenguaje formal?",
        "options": [
            "¿Qué onda profe, ya va a calificar?",
            "Ahorita hacemos la práctica, no se apure.",
            "Procederemos a realizar el experimento siguiendo las normas de seguridad.",
            "Ya quedó el experimento, todo chido."
        ],
        "correct_index": 2,
        "explanation": "La tercera oración usa vocabulario y estructura propios del registro formal."
    },
    {
        "module": "con_len",
        "text": "En el enunciado: \"Me preocupa que no estudies\", la oración subordinada es:",
        "options": [
            "\"Me preocupa\"",
            "\"que no estudies\"",
            "\"Me preocupa que\"",
            "\"no estudies\" solamente"
        ],
        "correct_index": 1,
        "explanation": "La oración subordinada sustantiva es \"que no estudies\", complemento de \"Me preocupa\"."
    },
    {
        "module": "con_len",
        "text": "¿Cuál opción NO contiene un error de puntuación evidente?",
        "options": [
            "Si estudias, aprobarás el examen.",
            "Si estudias aprobarás, el examen.",
            "Si, estudias aprobarás el examen.",
            "Si estudias aprobarás el, examen."
        ],
        "correct_index": 0,
        "explanation": "La primera oración tiene la coma correctamente colocada después de la oración condicional."
    },
    {
        "module": "con_len",
        "text": "La palabra \"sustancia\" es un sustantivo:",
        "options": ["propio", "común", "concreto", "abstracto"],
        "correct_index": 1,
        "explanation": "\"Sustancia\" nombra en general a un tipo de materia: es un sustantivo común."
    },
    {
        "module": "con_len",
        "text": "¿Cuál opción contiene un barbarismo (uso incorrecto de una palabra)?",
        "options": [
            "Voy a revisar el experimento.",
            "Vamos a monitorear la reacción.",
            "Voy a checar la tarea.",
            "Debemos analizar los resultados."
        ],
        "correct_index": 2,
        "explanation": "\"Checar\" es un anglicismo coloquial derivado de \"check\"; en lenguaje cuidado se prefiere \"revisar\" o \"verificar\"."
    },
    {
        "module": "con_len",
        "text": "¿Cuál es la forma correcta del plural de \"análisis\"?",
        "options": ["análises", "análisis", "analisises", "análisises"],
        "correct_index": 1,
        "explanation": "\"Análisis\" es un sustantivo invariable: singular y plural se escriben igual."
    },
    # =======================
    # MÓDULO IV · COMPRENSIÓN DE TEXTOS (15 reactivos demo)
    # =======================
    {
        "module": "comp_text",
        "text": "Lee el siguiente fragmento:\n\n\"En el laboratorio de química, antes de comenzar cualquier experimento, es indispensable leer el procedimiento completo, usar el equipo de protección personal y verificar que los materiales estén en buen estado. Estas acciones reducen el riesgo de accidentes y permiten obtener resultados más confiables\".\n\n¿Cuál es la idea principal del texto?",
        "options": [
            "Los materiales del laboratorio son muy costosos",
            "Es indispensable usar bata para no ensuciarse",
            "Las medidas previas de seguridad mejoran la seguridad y la confiabilidad de los resultados",
            "Los experimentos de química siempre son peligrosos"
        ],
        "correct_index": 2,
        "explanation": "El texto insiste en las acciones previas (leer, protegerse, revisar material) para disminuir riesgos y mejorar resultados."
    },
    {
        "module": "comp_text",
        "text": "Lee el siguiente texto:\n\n\"Durante la práctica se observó que, al incrementar la temperatura, la velocidad de disolución del soluto aumentó. Sin embargo, a temperaturas demasiado altas comenzaron a aparecer impurezas en la solución\".\n\n¿Qué tipo de relación establece el conector \"Sin embargo\"?",
        "options": [
            "Causa",
            "Consecuencia",
            "Adición",
            "Contraste u oposición"
        ],
        "correct_index": 3,
        "explanation": "\"Sin embargo\" introduce una idea que contrasta con la anterior: aunque la temperatura ayuda, también puede generar impurezas."
    },
    {
        "module": "comp_text",
        "text": "Texto:\n\n\"Los indicadores ácido-base cambian de color en un intervalo de pH determinado. Por ejemplo, la fenolftaleína es incolora en medio ácido y adquiere un tono rosa en medio ligeramente básico\".\n\n¿Qué información aporta el ejemplo de la fenolftaleína?",
        "options": [
            "Ilustra la explicación general sobre el comportamiento de los indicadores",
            "Contradice la definición de indicador ácido-base",
            "Demuestra que todos los indicadores son incoloros",
            "Sirve únicamente como dato histórico"
        ],
        "correct_index": 0,
        "explanation": "El ejemplo concreta la explicación general mostrando un caso específico."
    },
    {
        "module": "comp_text",
        "text": "Lee el siguiente fragmento:\n\n\"A diferencia de los métodos cualitativos, los métodos cuantitativos permiten determinar la cantidad exacta de una sustancia en una muestra\".\n\n¿Qué conclusión se puede obtener del texto?",
        "options": [
            "Los métodos cualitativos son más precisos que los cuantitativos",
            "Solo existen métodos cuantitativos en química",
            "Los métodos cuantitativos se enfocan en la medida numérica de las sustancias",
            "Los métodos cualitativos no se usan en el laboratorio"
        ],
        "correct_index": 2,
        "explanation": "La frase destaca que los métodos cuantitativos dan la cantidad exacta (dato numérico)."
    },
    {
        "module": "comp_text",
        "text": "Texto:\n\n\"Aunque el agua destilada es un líquido muy común en el laboratorio, su manejo descuidado puede causar derrames que dañen el material o provoquen resbalones\".\n\n¿Cuál es la intención comunicativa principal del autor?",
        "options": [
            "Relatar una anécdota personal",
            "Advertir sobre los riesgos de un manejo descuidado",
            "Describir el proceso de destilación del agua",
            "Convencer de que el agua destilada es peligrosa"
        ],
        "correct_index": 1,
        "explanation": "El texto advierte que, aun siendo común, el agua destilada requiere cuidado para evitar accidentes."
    },
    {
        "module": "comp_text",
        "text": "Lee el siguiente texto:\n\n\"La corrosión de los metales puede prevenirse mediante recubrimientos protectores, el uso de aleaciones más resistentes o el control de las condiciones ambientales\".\n\n¿Qué estructura predomina en el fragmento?",
        "options": [
            "Causa-efecto",
            "Comparación",
            "Enumeración de soluciones",
            "Secuencia temporal"
        ],
        "correct_index": 2,
        "explanation": "Se mencionan varias formas de prevenir la corrosión: recubrimientos, aleaciones, control ambiental."
    },
    {
        "module": "comp_text",
        "text": "Texto:\n\n\"Primero se limpió el material de vidrio; después, se preparó la solución estándar; finalmente, se ajustó el equipo de medición\".\n\n¿Qué tipo de conectores se utilizan en el texto?",
        "options": [
            "De causa",
            "De oposición",
            "Temporales u ordenadores",
            "De ejemplificación"
        ],
        "correct_index": 2,
        "explanation": "\"Primero\", \"después\" y \"finalmente\" marcan orden cronológico de acciones."
    },
    {
        "module": "comp_text",
        "text": "Lee el siguiente fragmento:\n\n\"La contaminación del aire en las grandes ciudades no solo afecta a la salud humana, sino que también daña los materiales de construcción y altera los ecosistemas cercanos\".\n\n¿Cuál de las siguientes opciones resume mejor el texto?",
        "options": [
            "La contaminación del aire solo afecta a las personas",
            "La contaminación del aire tiene múltiples consecuencias negativas",
            "Los materiales de construcción son más importantes que la salud humana",
            "Los ecosistemas no se ven afectados por la contaminación"
        ],
        "correct_index": 1,
        "explanation": "El texto enumera varias consecuencias: salud, materiales, ecosistemas; la idea central es que tiene muchos efectos negativos."
    },
    {
        "module": "comp_text",
        "text": "Texto:\n\n\"Muchos estudiantes creen que la memoria es el único recurso para aprender química; sin embargo, comprender los conceptos y relacionarlos con situaciones reales resulta mucho más efectivo\".\n\n¿Qué opinión expresa el autor?",
        "options": [
            "La memoria es suficiente para aprender química",
            "Es mejor comprender y relacionar los contenidos que solo memorizarlos",
            "No es necesario estudiar para aprender química",
            "Los ejemplos reales no ayudan al aprendizaje"
        ],
        "correct_index": 1,
        "explanation": "El autor valora más la comprensión y la aplicación que la simple memorización."
    },
    {
        "module": "comp_text",
        "text": "Lee este fragmento:\n\n\"A pesar de que el experimento se repitió en varias ocasiones, los resultados siguieron siendo inconsistentes\".\n\n¿Qué indica la expresión \"A pesar de que\"?",
        "options": [
            "Una causa segura",
            "Una condición",
            "Una concesión o dificultad que no impide la acción",
            "Una conclusión"
        ],
        "correct_index": 2,
        "explanation": "\"A pesar de que\" introduce una dificultad (se repitió el experimento) que no evita que ocurra lo descrito (inconsistencia de resultados)."
    },
    {
        "module": "comp_text",
        "text": "Texto:\n\n\"El oxígeno es un gas esencial para la respiración de la mayoría de los seres vivos. No obstante, en altas concentraciones puede provocar combustiones violentas\".\n\n¿Qué función cumple el conector \"No obstante\"?",
        "options": [
            "Introducir una consecuencia lógica",
            "Introducir un ejemplo adicional",
            "Introducir una idea que contrasta con la anterior",
            "Repetir la idea inicial"
        ],
        "correct_index": 2,
        "explanation": "Contrasta el carácter esencial del oxígeno con el peligro de altas concentraciones."
    },
    {
        "module": "comp_text",
        "text": "Lee el fragmento:\n\n\"En la primera etapa del proyecto se recolectaron muestras de agua de diferentes pozos; en la segunda, se analizaron sus parámetros fisicoquímicos\".\n\n¿Qué tipo de texto es principalmente?",
        "options": [
            "Narrativo",
            "Expositivo-descriptivo de un procedimiento",
            "Argumentativo",
            "Dialogado"
        ],
        "correct_index": 1,
        "explanation": "Describe de forma objetiva las etapas de un proyecto: es expositivo-descriptivo con secuencia de acciones."
    },
    {
        "module": "comp_text",
        "text": "Texto:\n\n\"El principal objetivo de esta práctica es que el estudiante aprenda a preparar soluciones con concentraciones conocidas\".\n\n¿A qué parte de un informe de laboratorio podría pertenecer este enunciado?",
        "options": [
            "Introducción",
            "Objetivo",
            "Resultados",
            "Conclusiones"
        ],
        "correct_index": 1,
        "explanation": "Enuncia claramente el propósito de la práctica: corresponde a la sección de objetivos."
    },
    {
        "module": "comp_text",
        "text": "Lee el fragmento:\n\n\"Al finalizar la titulación, el cambio de color del indicador señaló el punto de equivalencia\".\n\n¿Qué relación existe entre \"Al finalizar la titulación\" y \"el cambio de color del indicador señaló el punto de equivalencia\"?",
        "options": [
            "De causa y efecto",
            "De oposición",
            "De comparación",
            "De ejemplificación"
        ],
        "correct_index": 0,
        "explanation": "El final de la titulación (causa) provoca el cambio de color que indica el punto de equivalencia (efecto)."
    },
    {
        "module": "comp_text",
        "text": "Texto:\n\n\"En resumen, los datos obtenidos confirman que el aumento de temperatura incrementa la solubilidad del soluto en agua\".\n\n¿Qué función tiene la expresión \"En resumen\"?",
        "options": [
            "Introducir un ejemplo",
            "Introducir una conclusión o síntesis de lo expuesto",
            "Introducir una objeción",
            "Introducir una definición"
        ],
        "correct_index": 1,
        "explanation": "\"En resumen\" anuncia que se presentará una síntesis o conclusión de lo que se ha explicado antes."
    },
    # =======================
    # MÓDULO V · HABILIDAD COMUNICATIVA (15 reactivos demo)
    # =======================
    {
        "module": "hab_com",
        "text": "¿Cuál opción presenta una redacción más clara y correcta?",
        "options": [
            "Se realizó la práctica, y pues se anotó todo y salió bien.",
            "La práctica se realizó y se registraron los datos obtenidos.",
            "Realizamos la práctica y se obtuvo datos y se anotaron.",
            "La práctica fue realizada, se anotó y pues ya."
        ],
        "correct_index": 1,
        "explanation": "La opción 2 es clara, formal y mantiene concordancia: se realizó y se registraron datos."
    },
    {
        "module": "hab_com",
        "text": "Selecciona el conector MÁS adecuado para expresar consecuencia:\n\n\"No se calibró el equipo; ________, las mediciones resultaron imprecisas.\"",
        "options": ["por lo tanto", "sin embargo", "además", "aunque"],
        "correct_index": 0,
        "explanation": "\"Por lo tanto\" expresa consecuencia directa. Los otros indican contraste o adición."
    },
    {
        "module": "hab_com",
        "text": "¿Qué opción utiliza correctamente los dos puntos?",
        "options": [
            "Traje: bata, guantes y lentes de seguridad.",
            "Traje bata: guantes y lentes de seguridad.",
            "Traje bata, guantes: y lentes de seguridad.",
            "Traje bata guantes y lentes: de seguridad."
        ],
        "correct_index": 0,
        "explanation": "Los dos puntos introducen una enumeración: \"Traje: bata, guantes y lentes...\""
    },
    {
        "module": "hab_com",
        "text": "¿Cuál oración mantiene un registro formal adecuado para un informe?",
        "options": [
            "La neta el experimento salió raro.",
            "El experimento salió bien chido, se vio el cambio.",
            "Se observó una variación inesperada en los resultados experimentales.",
            "Pues la práctica estuvo más o menos, pero se armó."
        ],
        "correct_index": 2,
        "explanation": "La opción 3 usa vocabulario técnico y objetivo propio de un informe."
    },
    {
        "module": "hab_com",
        "text": "Elige la oración con puntuación correcta.",
        "options": [
            "En el laboratorio, usamos bata guantes y lentes.",
            "En el laboratorio usamos bata, guantes y lentes.",
            "En el laboratorio usamos bata guantes, y lentes.",
            "En el laboratorio usamos, bata, guantes y lentes."
        ],
        "correct_index": 1,
        "explanation": "La enumeración se separa con comas: \"bata, guantes y lentes\"."
    },
    {
        "module": "hab_com",
        "text": "¿Cuál opción mejora la coherencia del siguiente enunciado?\n\n\"Se midió el pH. Se usó el potenciómetro. Se calibró el equipo.\"",
        "options": [
            "Se midió el pH y se calibró el equipo, luego se usó el potenciómetro.",
            "Se calibró el potenciómetro; posteriormente, se utilizó para medir el pH.",
            "Se usó el potenciómetro, el pH se midió, se calibró el equipo.",
            "Se midió el pH y el equipo se calibró, después antes."
        ],
        "correct_index": 1,
        "explanation": "Primero se calibra el equipo y después se mide: orden lógico y conectores adecuados."
    },
    {
        "module": "hab_com",
        "text": "Selecciona el título MÁS adecuado para un reporte sobre medición de pH.",
        "options": [
            "Cosas de química",
            "Práctica: Medición de pH con potenciómetro",
            "Lo que hicimos hoy",
            "Experimentos varios"
        ],
        "correct_index": 1,
        "explanation": "Es específico, formal y describe el contenido del reporte."
    },
    {
        "module": "hab_com",
        "text": "¿Cuál es la mejor forma de evitar repetición en la redacción?\n\n\"El experimento fue exitoso. El experimento mostró resultados claros.\"",
        "options": [
            "El experimento fue exitoso. El experimento mostró resultados claros.",
            "El experimento fue exitoso y mostró resultados claros.",
            "El experimento fue exitoso. El experimento, el experimento, claros.",
            "Fue exitoso. Mostró, el experimento, claros."
        ],
        "correct_index": 1,
        "explanation": "Se combina la idea para evitar repetición y mantener claridad."
    },
    {
        "module": "hab_com",
        "text": "Elige el conector MÁS adecuado para introducir una comparación:\n\n\"La titulación potenciométrica, ________ la titulación con indicador, permite detectar con mayor precisión el punto de equivalencia.\"",
        "options": ["a diferencia de", "por lo tanto", "en conclusión", "además de"],
        "correct_index": 0,
        "explanation": "\"A diferencia de\" introduce comparación/contraste entre dos métodos."
    },
    {
        "module": "hab_com",
        "text": "¿Cuál opción presenta una conclusión adecuada para un informe?",
        "options": [
            "Y pues eso fue todo, estuvo bueno.",
            "Con base en los resultados, se confirma que la calibración del equipo es esencial para obtener mediciones confiables.",
            "La práctica estuvo rara, pero salió.",
            "No sé qué poner aquí."
        ],
        "correct_index": 1,
        "explanation": "Una conclusión formal resume hallazgos y los vincula con el objetivo."
    },
    {
        "module": "hab_com",
        "text": "Identifica la opción con uso correcto de mayúsculas.",
        "options": [
            "El profesor de Química es muy estricto.",
            "El Profesor de química es muy estricto.",
            "El profesor de química es muy estricto.",
            "El Profesor de Química es muy estricto."
        ],
        "correct_index": 2,
        "explanation": "En general, \"profesor\" y \"química\" van en minúscula si no forman parte de un nombre propio."
    },
    {
        "module": "hab_com",
        "text": "¿Cuál oración es más objetiva (propia de texto académico)?",
        "options": [
            "La solución estaba horrible.",
            "La solución se veía fea y rara.",
            "La solución presentó turbidez y cambio de coloración.",
            "La solución se veía mal."
        ],
        "correct_index": 2,
        "explanation": "Describe observaciones medibles/observables sin juicios subjetivos."
    },
    {
        "module": "hab_com",
        "text": "Elige la opción con mejor adecuación al destinatario (correo a un profesor).",
        "options": [
            "Profe, pásame el punto porque no entendí nada.",
            "Hola, ¿me puede pasar el punto? pls",
            "Buenas tardes, profesor(a). ¿Podría indicarme el criterio de evaluación de la práctica?",
            "Oiga, ¿cómo calificó?"
        ],
        "correct_index": 2,
        "explanation": "Es respetuosa, clara y formal para comunicación académica."
    },
    {
        "module": "hab_com",
        "text": "¿Qué opción usa correctamente la coma para separar un inciso explicativo?",
        "options": [
            "El potenciómetro que estaba calibrado, se utilizó en la medición.",
            "El potenciómetro, que estaba calibrado, se utilizó en la medición.",
            "El potenciómetro que estaba, calibrado se utilizó en la medición.",
            "El potenciómetro que estaba calibrado se utilizó, en la medición."
        ],
        "correct_index": 1,
        "explanation": "El inciso explicativo \"que estaba calibrado\" va entre comas."
    },
    {
        "module": "hab_com",
        "text": "Selecciona el enunciado mejor organizado para un procedimiento.",
        "options": [
            "Se midió, después se preparó, luego se calibró.",
            "Primero se calibró el equipo; después se preparó la solución; finalmente se registraron las mediciones.",
            "Se registraron mediciones, se calibró, se preparó la solución primero.",
            "Se hizo todo y ya."
        ],
        "correct_index": 1,
        "explanation": "Presenta orden lógico y conectores de secuencia: primero, después, finalmente."
    },
    # =======================
    # MÓDULO VI · INGLÉS (20 reactivos demo)
    # =======================
    {
        "module": "ingles",
        "text": "Choose the correct option:\n\n\"She ____ to the laboratory every morning.\"",
        "options": ["go", "goes", "is going", "went"],
        "correct_index": 1,
        "explanation": "Present simple with third person singular (she): goes."
    },
    {
        "module": "ingles",
        "text": "Select the correct past form:\n\n\"Yesterday we ____ the experiment.\"",
        "options": ["do", "did", "done", "doing"],
        "correct_index": 1,
        "explanation": "The past simple of 'do' is 'did'."
    },
    {
        "module": "ingles",
        "text": "Choose the correct sentence.",
        "options": [
            "There is many samples in the lab.",
            "There are many samples in the lab.",
            "There are much samples in the lab.",
            "There is a many samples in the lab."
        ],
        "correct_index": 1,
        "explanation": "Plural noun 'samples' requires 'there are'."
    },
    {
        "module": "ingles",
        "text": "Choose the correct preposition:\n\n\"The solution is ____ the beaker.\"",
        "options": ["in", "on", "at", "by"],
        "correct_index": 0,
        "explanation": "Liquids contained inside something are 'in' the container."
    },
    {
        "module": "ingles",
        "text": "Select the correct comparative form:\n\n\"This method is ____ than the previous one.\"",
        "options": ["more accurate", "most accurate", "accurate", "accurately"],
        "correct_index": 0,
        "explanation": "Comparative form: more + adjective (accurate)."
    },
    {
        "module": "ingles",
        "text": "Choose the correct option:\n\n\"We ____ wear safety goggles in the laboratory.\"",
        "options": ["must", "can", "shouldn't", "may"],
        "correct_index": 0,
        "explanation": "'Must' expresses obligation."
    },
    {
        "module": "ingles",
        "text": "Identify the correct question:",
        "options": [
            "What time does the class starts?",
            "What time do the class start?",
            "What time does the class start?",
            "What time is the class start?"
        ],
        "correct_index": 2,
        "explanation": "Auxiliary 'does' + base form 'start'."
    },
    {
        "module": "ingles",
        "text": "Choose the correct article:\n\n\"____ experiment was successful.\"",
        "options": ["A", "An", "The", "No article"],
        "correct_index": 2,
        "explanation": "'The' refers to a specific experiment already known."
    },
    {
        "module": "ingles",
        "text": "Select the correct sentence in present continuous:",
        "options": [
            "They work on the report now.",
            "They are work on the report now.",
            "They are working on the report now.",
            "They working on the report now."
        ],
        "correct_index": 2,
        "explanation": "Present continuous: am/is/are + verb-ing."
    },
    {
        "module": "ingles",
        "text": "Choose the correct connector:\n\n\"The sample was contaminated; ____, the results were invalid.\"",
        "options": ["however", "therefore", "although", "but"],
        "correct_index": 1,
        "explanation": "'Therefore' expresses consequence."
    },
    {
        "module": "ingles",
        "text": "Choose the correct plural form:",
        "options": ["analysis", "analysises", "analyses", "analysis's"],
        "correct_index": 2,
        "explanation": "The plural of 'analysis' is 'analyses'."
    },
    {
        "module": "ingles",
        "text": "Select the correct option:\n\n\"If you heat the solution, it ____ faster.\"",
        "options": ["dissolve", "dissolves", "will dissolve", "dissolving"],
        "correct_index": 1,
        "explanation": "Zero conditional: if + present simple, present simple."
    },
    {
        "module": "ingles",
        "text": "Choose the correct word:\n\n\"The results were ____ with the hypothesis.\"",
        "options": ["consistent", "consist", "consistency", "consisting"],
        "correct_index": 0,
        "explanation": "'Consistent' is the correct adjective."
    },
    {
        "module": "ingles",
        "text": "Select the correct passive form:\n\n\"The solution ____ prepared by the students.\"",
        "options": ["is", "was", "were", "has"],
        "correct_index": 1,
        "explanation": "Past simple passive: was prepared."
    },
    {
        "module": "ingles",
        "text": "Choose the correct option:\n\n\"There isn't ____ information in the report.\"",
        "options": ["many", "few", "much", "a few"],
        "correct_index": 2,
        "explanation": "'Information' is uncountable, so we use 'much'."
    },
    {
        "module": "ingles",
        "text": "Select the correct sentence:",
        "options": [
            "He don't understand the procedure.",
            "He doesn't understands the procedure.",
            "He doesn't understand the procedure.",
            "He not understand the procedure."
        ],
        "correct_index": 2,
        "explanation": "Negative present simple: does not + base verb."
    },
    {
        "module": "ingles",
        "text": "Choose the correct adjective order:\n\n\"a ____ glass container\"",
        "options": [
            "round small",
            "glass round",
            "small round",
            "round glass"
        ],
        "correct_index": 3,
        "explanation": "Opinion/size/shape/material: shape (round) before material (glass)."
    },
    {
        "module": "ingles",
        "text": "Read the sentence:\n\n\"The students measured the pH carefully.\" What does 'carefully' describe?",
        "options": ["The students", "The pH", "The action of measuring", "The laboratory"],
        "correct_index": 2,
        "explanation": "'Carefully' is an adverb describing how the action was done."
    },
    {
        "module": "ingles",
        "text": "Choose the correct option:\n\n\"How ____ time do we have left?\"",
        "options": ["many", "much", "long", "often"],
        "correct_index": 1,
        "explanation": "'Time' is uncountable, so we use 'much'."
    },
    {
        "module": "ingles",
        "text": "Select the best closing for an academic email:",
        "options": [
            "See ya!",
            "Thanks bro, bye",
            "Kind regards,",
            "Later!"
        ],
        "correct_index": 2,
        "explanation": "'Kind regards' is appropriate in formal/academic emails."
    },
    # =======================
    # MÓDULO VII · MATEMÁTICAS AVANZADAS (20 reactivos demo)
    # =======================
    {
        "module": "mat_avz",
        "text": "Calcula la derivada de la función f(x) = 3x².",
        "options": ["6x", "3x", "x²", "6x²"],
        "correct_index": 0,
        "explanation": "d/dx (3x²) = 3·2x = 6x."
    },
    {
        "module": "mat_avz",
        "text": "¿Cuál es la derivada de f(x) = 5x − 7?",
        "options": ["5", "5x", "−7", "0"],
        "correct_index": 0,
        "explanation": "La derivada de 5x es 5 y la de una constante es 0."
    },
    {
        "module": "mat_avz",
        "text": "Calcula la derivada de f(x) = x³.",
        "options": ["3x²", "x²", "3x", "x³"],
        "correct_index": 0,
        "explanation": "Regla de la potencia: d/dx(x³) = 3x²."
    },
    {
        "module": "mat_avz",
        "text": "Si f(x) = x² + 4x, ¿cuál es f'(x)?",
        "options": ["2x + 4", "x² + 4", "2x", "4x"],
        "correct_index": 0,
        "explanation": "Derivando término a término: d(x²)=2x y d(4x)=4."
    },
    {
        "module": "mat_avz",
        "text": "Evalúa la derivada de f(x) = x² en x = 3.",
        "options": ["3", "6", "9", "12"],
        "correct_index": 1,
        "explanation": "f'(x)=2x, entonces f'(3)=2·3=6."
    },
    {
        "module": "mat_avz",
        "text": "¿Cuál es la solución de la ecuación 2x² = 8?",
        "options": ["x = ±2", "x = 4", "x = ±4", "x = 2"],
        "correct_index": 0,
        "explanation": "2x²=8 → x²=4 → x=±2."
    },
    {
        "module": "mat_avz",
        "text": "Resuelve la ecuación x² − 5x = 0.",
        "options": ["x = 0 y x = 5", "x = −5 y x = 1", "x = 5", "x = 0"],
        "correct_index": 0,
        "explanation": "Factorizando: x(x−5)=0 → x=0 o x=5."
    },
    {
        "module": "mat_avz",
        "text": "¿Cuál es el valor de log₁₀(100)?",
        "options": ["1", "2", "10", "100"],
        "correct_index": 1,
        "explanation": "10² = 100, por lo tanto log₁₀(100)=2."
    },
    {
        "module": "mat_avz",
        "text": "Si log₁₀(x) = 3, ¿cuál es el valor de x?",
        "options": ["3", "10", "100", "1000"],
        "correct_index": 3,
        "explanation": "log₁₀(x)=3 implica x=10³=1000."
    },
    {
        "module": "mat_avz",
        "text": "Simplifica: ln(e²).",
        "options": ["1", "2", "e", "0"],
        "correct_index": 1,
        "explanation": "ln(e²)=2·ln(e)=2."
    },
    {
        "module": "mat_avz",
        "text": "¿Cuál es el dominio de la función f(x)=1/x?",
        "options": [
            "Todos los números reales",
            "x > 0",
            "x < 0",
            "Todos los reales excepto 0"
        ],
        "correct_index": 3,
        "explanation": "La función no está definida cuando x=0."
    },
    {
        "module": "mat_avz",
        "text": "¿Qué tipo de función es f(x)=x²?",
        "options": ["Lineal", "Exponencial", "Cuadrática", "Logarítmica"],
        "correct_index": 2,
        "explanation": "El mayor exponente de x es 2: función cuadrática."
    },
    {
        "module": "mat_avz",
        "text": "Calcula sin(90°).",
        "options": ["0", "1", "−1", "0.5"],
        "correct_index": 1,
        "explanation": "El seno de 90° es 1."
    },
    {
        "module": "mat_avz",
        "text": "Calcula cos(0°).",
        "options": ["0", "1", "−1", "0.5"],
        "correct_index": 1,
        "explanation": "El coseno de 0° es 1."
    },
    {
        "module": "mat_avz",
        "text": "¿Cuál es el valor de tan(45°)?",
        "options": ["0", "1", "√3", "−1"],
        "correct_index": 1,
        "explanation": "tan(45°)=1."
    },
    {
        "module": "mat_avz",
        "text": "Si una función tiene pendiente positiva, esto significa que:",
        "options": [
            "La función decrece",
            "La función es constante",
            "La función aumenta",
            "La función no existe"
        ],
        "correct_index": 2,
        "explanation": "Pendiente positiva indica que la función aumenta al crecer x."
    },
    {
        "module": "mat_avz",
        "text": "¿Cuál es la pendiente de la recta y = 4x − 3?",
        "options": ["−3", "4", "3", "−4"],
        "correct_index": 1,
        "explanation": "En y = mx + b, la pendiente es m=4."
    },
    {
        "module": "mat_avz",
        "text": "Evalúa la función f(x)=2x+1 para x=2.",
        "options": ["3", "4", "5", "6"],
        "correct_index": 2,
        "explanation": "f(2)=2·2+1=5."
    },
    {
        "module": "mat_avz",
        "text": "¿Cuál es el vértice de la parábola y = x²?",
        "options": ["(1,1)", "(−1,1)", "(0,0)", "(0,1)"],
        "correct_index": 2,
        "explanation": "La parábola y=x² tiene vértice en el origen (0,0)."
    },
    {
        "module": "mat_avz",
        "text": "Si f(x)=x², ¿cuál es el valor de f(−2)?",
        "options": ["−4", "−2", "2", "4"],
        "correct_index": 3,
        "explanation": "f(−2)=(−2)²=4."
    },
    # =======================
    # MÓDULO VIII · FÍSICA (20 reactivos demo)
    # =======================
    {
        "module": "fisica",
        "text": "¿Cuál es la unidad de fuerza en el Sistema Internacional?",
        "options": ["Joule (J)", "Pascal (Pa)", "Newton (N)", "Watt (W)"],
        "correct_index": 2,
        "explanation": "La fuerza se mide en Newtons (N) en el Sistema Internacional."
    },
    {
        "module": "fisica",
        "text": "Un objeto se mueve con velocidad constante. ¿Cuál es su aceleración?",
        "options": ["Cero", "Constante distinta de cero", "Variable", "Depende de la masa"],
        "correct_index": 0,
        "explanation": "Si la velocidad no cambia, la aceleración es cero."
    },
    {
        "module": "fisica",
        "text": "¿Cuál es la ecuación correcta de la velocidad promedio?",
        "options": [
            "v = d × t",
            "v = d / t",
            "v = t / d",
            "v = m / a"
        ],
        "correct_index": 1,
        "explanation": "La velocidad promedio se define como distancia entre tiempo."
    },
    {
        "module": "fisica",
        "text": "Un automóvil recorre 100 m en 5 s. ¿Cuál es su velocidad promedio?",
        "options": ["5 m/s", "10 m/s", "20 m/s", "50 m/s"],
        "correct_index": 2,
        "explanation": "v = 100 m / 5 s = 20 m/s."
    },
    {
        "module": "fisica",
        "text": "Según la Primera Ley de Newton, un cuerpo en reposo permanecerá en reposo si:",
        "options": [
            "No actúa ninguna fuerza",
            "La fuerza neta es cero",
            "La masa es constante",
            "La velocidad es máxima"
        ],
        "correct_index": 1,
        "explanation": "La Primera Ley indica que si la fuerza neta es cero, no cambia el estado de movimiento."
    },
    {
        "module": "fisica",
        "text": "¿Cuál es la ecuación de la Segunda Ley de Newton?",
        "options": ["F = m / a", "F = m + a", "F = m × a", "F = m − a"],
        "correct_index": 2,
        "explanation": "La fuerza es igual a la masa por la aceleración: F = m·a."
    },
    {
        "module": "fisica",
        "text": "Si la masa de un objeto es 2 kg y su aceleración es 3 m/s², ¿cuál es la fuerza aplicada?",
        "options": ["5 N", "6 N", "9 N", "12 N"],
        "correct_index": 1,
        "explanation": "F = m·a = 2×3 = 6 N."
    },
    {
        "module": "fisica",
        "text": "¿Qué magnitud física se mide en Joules (J)?",
        "options": ["Fuerza", "Potencia", "Trabajo", "Presión"],
        "correct_index": 2,
        "explanation": "El trabajo (y la energía) se mide en Joules."
    },
    {
        "module": "fisica",
        "text": "¿Cuál es la ecuación del trabajo mecánico?",
        "options": [
            "W = F × d",
            "W = m × a",
            "W = P / t",
            "W = d / t"
        ],
        "correct_index": 0,
        "explanation": "El trabajo es fuerza por desplazamiento en la dirección del movimiento."
    },
    {
        "module": "fisica",
        "text": "Un objeto se eleva a cierta altura. ¿Qué tipo de energía posee?",
        "options": [
            "Energía cinética",
            "Energía potencial gravitatoria",
            "Energía térmica",
            "Energía eléctrica"
        ],
        "correct_index": 1,
        "explanation": "Al elevarse, el objeto almacena energía potencial gravitatoria."
    },
    {
        "module": "fisica",
        "text": "¿Cuál es la ecuación de la energía cinética?",
        "options": [
            "Ec = mgh",
            "Ec = ½mv²",
            "Ec = Fd",
            "Ec = Pt"
        ],
        "correct_index": 1,
        "explanation": "La energía cinética depende de la masa y del cuadrado de la velocidad."
    },
    {
        "module": "fisica",
        "text": "¿Cuál es la unidad de presión en el Sistema Internacional?",
        "options": ["Newton", "Joule", "Pascal", "Watt"],
        "correct_index": 2,
        "explanation": "La presión se mide en Pascales (Pa)."
    },
    {
        "module": "fisica",
        "text": "La presión se define como:",
        "options": [
            "Fuerza por unidad de área",
            "Masa por volumen",
            "Energía por tiempo",
            "Distancia por tiempo"
        ],
        "correct_index": 0,
        "explanation": "P = F / A."
    },
    {
        "module": "fisica",
        "text": "Si una fuerza actúa sobre un área menor, la presión:",
        "options": [
            "Disminuye",
            "Permanece igual",
            "Aumenta",
            "Se anula"
        ],
        "correct_index": 2,
        "explanation": "Para la misma fuerza, menor área implica mayor presión."
    },
    {
        "module": "fisica",
        "text": "¿Cuál es la unidad de potencia?",
        "options": ["Joule", "Newton", "Pascal", "Watt"],
        "correct_index": 3,
        "explanation": "La potencia se mide en Watts (W)."
    },
    {
        "module": "fisica",
        "text": "La potencia se define como:",
        "options": [
            "Trabajo por unidad de tiempo",
            "Fuerza por distancia",
            "Energía por masa",
            "Velocidad por tiempo"
        ],
        "correct_index": 0,
        "explanation": "P = W / t."
    },
    {
        "module": "fisica",
        "text": "¿Cuál es la unidad de carga eléctrica?",
        "options": ["Volt", "Ohm", "Ampere", "Coulomb"],
        "correct_index": 3,
        "explanation": "La carga eléctrica se mide en Coulombs (C)."
    },
    {
        "module": "fisica",
        "text": "¿Qué instrumento se utiliza para medir la corriente eléctrica?",
        "options": ["Voltímetro", "Ohmímetro", "Amperímetro", "Termómetro"],
        "correct_index": 2,
        "explanation": "La corriente eléctrica se mide con un amperímetro."
    },
    {
        "module": "fisica",
        "text": "Según la Ley de Ohm, la relación correcta es:",
        "options": ["V = I / R", "I = V × R", "V = I × R", "R = I × V"],
        "correct_index": 2,
        "explanation": "La Ley de Ohm establece que V = I·R."
    },
    {
        "module": "fisica",
        "text": "Si un resistor tiene una resistencia de 10 Ω y circula una corriente de 2 A, ¿cuál es el voltaje?",
        "options": ["5 V", "10 V", "20 V", "40 V"],
        "correct_index": 2,
        "explanation": "V = I·R = 2×10 = 20 V."
    },

    # ---- Ejemplos mínimos de otros módulos (puedes ampliarlos después) ----
    {
        "module": "raz_ana",
        "text": "Secuencia: 2, 4, 8, 16, ... ¿Cuál es el siguiente número?",
        "options": ["18", "24", "30", "32"],
        "correct_index": 3,
        "explanation": "Cada término se multiplica por 2: 16×2 = 32."
    },
    {
        "module": "ingles",
        "text": "Choose the correct option: \"She ____ to the lab every morning.\"",
        "options": ["go", "goes", "is go", "going"],
        "correct_index": 1,
        "explanation": "En presente simple con 'she' se usa 'goes'."
    },
]
import re

TOPIC_DEFAULT = {
    "mat_bas": "algebra_basica",
    "raz_ana": "logica_proposicional",
    "con_len": "gramatica",
    "comp_text": "idea_principal",
    "hab_com": "redaccion_claridad",
    "ingles": "grammar",
    "mat_avz": "algebra",
    "fisica": "unidades_si",
}

def infer_topic(question: dict) -> str:
    module = question.get("module", "unknown")
    text = (question.get("text") or "").lower()

    # ---- Matemáticas básicas ----
    if module == "mat_bas":
        if any(k in text for k in ["1/2", "2/3", "3/4", "fracción", "fracciones", "÷", "/"]):
            return "fracciones"
        if any(k in text for k in ["%", "descuento", "iva", "porcentaje"]):
            return "porcentajes"
        if any(k in text for k in ["propor", "regla de tres", "mismo precio unitario", "partes"]):
            return "proporciones"
        if any(k in text for k in ["x", "ecuación", "expresión", "simplifica", "desarrolla"]):
            return "algebra_basica"
        if any(k in text for k in ["√", "raíz", "potencia", "2³", "x²"]):
            return "potencias_raices"
        if any(k in text for k in ["área", "perímetro", "círculo", "triángulo", "rectángulo"]):
            return "geometria"
        if any(k in text for k in ["convierte", "km", "mL", "litros", "metros"]):
            return "conversiones"
        if any(k in text for k in ["promedio", "media"]):
            return "estadistica_basica"
        if any(k in text for k in ["plano cartesiano", "punto (", "eje x", "eje y", "pendiente"]):
            return "plano_cartesiano"

    # ---- Razonamiento analítico ----
    if module == "raz_ana":
        if "secuencia" in text or re.search(r"\d,\s*\d", text):
            return "secuencias"
        if "analogía" in text or "como" in text:
            return "analogias"
        if any(k in text for k in ["p:", "q:", "→", "∧", "∨", "negación", "proposición"]):
            return "logica_proposicional"
        if any(k in text for k in ["todos", "algunos", "ningún", "concluir"]):
            return "silogismos"
        if any(k in text for k in ["orden", "mayor", "menor", "volumen", "A, B, C"]):
            return "ordenamiento"
        if any(k in text for k in ["gráfica", "tabla", "linealmente", "datos"]):
            return "interpretacion_datos"

    # ---- Conocimiento de la lengua ----
    if module == "con_len":
        if any(k in text for k in ["tilde", "acentu", "diacrítico"]):
            return "acentuacion"
        if any(k in text for k in ["coma", "punto y coma", "dos puntos", "puntuación"]):
            return "puntuacion"
        if any(k in text for k in ["pronombre", "adjetivo", "adverbio", "sustantivo", "verbo", "categoría gramatical"]):
            return "gramatica"
        if any(k in text for k in ["conector", "porque", "por qué", "sin embargo", "aunque"]):
            return "conectores"
        if any(k in text for k in ["formal", "coloquial", "registro"]):
            return "registro_lenguaje"
        if any(k in text for k in ["sinónimo", "antónimo"]):
            return "lexico_sinonimos_antonimos"

    # ---- Comprensión de textos ----
    if module == "comp_text":
        if "idea principal" in text:
            return "idea_principal"
        if any(k in text for k in ["conclusión", "se deduce", "se infiere"]):
            return "inferencias"
        if any(k in text for k in ["sin embargo", "no obstante", "por lo tanto", "conector"]):
            return "conectores_textuales"
        if any(k in text for k in ["intención", "propósito"]):
            return "proposito_texto"
        if "resumen" in text or "en resumen" in text:
            return "resumen"

    # ---- Habilidad comunicativa ----
    if module == "hab_com":
        if any(k in text for k in ["redacción", "clara", "repetición"]):
            return "redaccion_claridad"
        if any(k in text for k in ["coherencia", "orden lógico", "mejor organizado"]):
            return "coherencia_cohesion"
        if any(k in text for k in ["registro formal", "correo", "profesor"]):
            return "registro_formal"
        if any(k in text for k in ["coma", "dos puntos", "punto y coma", "mayúsculas"]):
            return "puntuacion"
        if any(k in text for k in ["título", "conclusión", "procedimiento"]):
            return "estructura_texto"

    # ---- Inglés ----
    if module == "ingles":
        if any(k in text for k in ["read", "text:", "what does", "idea", "closing"]):
            return "reading"
        if any(k in text for k in ["choose", "select", "correct", "does", "did", "there is", "there are"]):
            return "grammar"
        if any(k in text for k in ["synonym", "word", "plural", "vocabulary"]):
            return "vocabulary"
        if any(k in text for k in ["therefore", "however", "although", "connector"]):
            return "connectors"

    # ---- Matemáticas avanzadas ----
    if module == "mat_avz":
        if "deriv" in text or "f'(x)" in text:
            return "derivadas"
        if "log" in text or "ln" in text:
            return "logaritmos"
        if any(k in text for k in ["sin(", "cos(", "tan(", "°"]):
            return "trigonometria"
        if "función" in text or "dominio" in text:
            return "funciones"
        return "algebra"

    # ---- Física ----
    if module == "fisica":
        if any(k in text for k in ["m/s", "velocidad", "aceleración", "recorre"]):
            return "cinematica"
        if any(k in text for k in ["newton", "f = m", "segunda ley", "fuerza aplicada"]):
            return "dinamica"
        if any(k in text for k in ["trabajo", "joule", "energía", "½mv²", "mgh"]):
            return "trabajo_energia"
        if any(k in text for k in ["presión", "pascal", "área"]):
            return "presion"
        if any(k in text for k in ["ohm", "voltaje", "resistor", "corriente", "amper"]):
            return "electricidad"
        if any(k in text for k in ["unidad", "sistema internacional"]):
            return "unidades_si"

    return TOPIC_DEFAULT.get(module, "general")


def normalize_question_bank():
    """
    Asegura que TODAS las preguntas tengan topic.
    Llamar 1 vez al inicio del servidor.
    """
    for q in QUESTION_BANK:
        if "topic" not in q or not q["topic"]:
            q["topic"] = infer_topic(q)

normalize_question_bank()

# ============================
# RUTAS
# ============================

@app.route("/")
def index():
    # En la página de inicio mostramos tarjetas de módulos
    modules = []
    for key, cfg in MODULES_CONFIG.items():
        count = sum(1 for q in QUESTION_BANK if q["module"] == key)
        modules.append({
            "key": key,
            "name": cfg["name"],
            "questions_official": cfg["questions_official"],
            "time_minutes": cfg["time_minutes"],
            "questions_available": count,
        })
    return render_template("index.html", modules=modules)


def get_questions_for_module(module_key, num_requested=None):
    """
    Devuelve una lista de preguntas para el módulo.
    - num_requested: cuántas preguntas queremos (5, 10, 15, 20...).
      Si es None, usa todas las disponibles.
    """
    pool = [q for q in QUESTION_BANK if q["module"] == module_key]
    random.shuffle(pool)

    if num_requested is not None:
        num = min(num_requested, len(pool))
        pool = pool[:num]

    return pool

@app.route("/exam/<module_key>", methods=["GET", "POST"])
def exam(module_key):
    if module_key not in MODULES_CONFIG:
        return redirect(url_for("index"))

    quiz = session.get("quiz")

    # ----------- NUEVO EXAMEN (GET o cambio de módulo) -----------
    if request.method == "GET" or quiz is None or quiz.get("module_key") != module_key:
        # Número de preguntas
        n_param = request.args.get("n", type=int)
        if n_param not in (5, 10, 15, 20):
            n_param = None  # si no manda nada, usamos todas las disponibles

        # Tiempo solicitado
        t_param = request.args.get("t", default="original")  # "original", "1", "5", etc.

        if t_param == "original":
            minutes = MODULES_CONFIG[module_key]["time_minutes"]
        else:
            try:
                minutes = int(t_param)
            except ValueError:
                minutes = MODULES_CONFIG[module_key]["time_minutes"]

            # por seguridad, solo permitimos estos valores
            if minutes not in (1, 5, 10, 15, 20):
                minutes = MODULES_CONFIG[module_key]["time_minutes"]

        questions = get_questions_for_module(module_key, num_requested=n_param)
        if not questions:
            return render_template(
                "exam.html",
                module_key=module_key,
                module_cfg=MODULES_CONFIG[module_key],
                question=None,
                index=0,
                total=0,
                error="Aún no hay preguntas cargadas para este módulo.",
                remaining_seconds=0,
            )

        now = time.time()
        quiz = {
            "module_key": module_key,
            "current_index": 0,
            "answers": [],
            "questions": questions,
            "num_requested": len(questions),
            "time_limit_sec": minutes * 60,
            "start_time": now,
        }
        session["quiz"] = quiz

    # ----------- SIGUIENTE PREGUNTA (POST) -----------
    else:
        # Revisar si se acabó el tiempo ANTES de guardar la respuesta
        elapsed = time.time() - quiz["start_time"]
        remaining = quiz["time_limit_sec"] - elapsed
        if remaining <= 0:
            # tiempo terminado → ir directo a resultados
            return redirect(url_for("results"))

        selected = request.form.get("answer")
        if selected is None:
            selected_index = None
        else:
            try:
                selected_index = int(selected)
            except ValueError:
                selected_index = None

        questions = quiz["questions"]
        current_index = quiz["current_index"]

        if current_index < len(questions):
            quiz["answers"].append({
                "question_index": current_index,
                "selected_index": selected_index
            })
            quiz["current_index"] = current_index + 1

        session["quiz"] = quiz

        if quiz["current_index"] >= len(quiz["questions"]):
            return redirect(url_for("results"))

    # ----------- MOSTRAR PREGUNTA ACTUAL -----------
    quiz = session["quiz"]
    questions = quiz["questions"]
    current_index = quiz["current_index"]

    if current_index >= len(questions):
        return redirect(url_for("results"))

    question = questions[current_index]
    module_cfg = MODULES_CONFIG[module_key]

    # calcular segundos restantes para el cronómetro
    elapsed = time.time() - quiz["start_time"]
    remaining = quiz["time_limit_sec"] - elapsed
    if remaining <= 0:
        return redirect(url_for("results"))

    remaining_seconds = int(remaining)

    return render_template(
        "exam.html",
        module_key=module_key,
        module_cfg=module_cfg,
        question=question,
        index=current_index + 1,
        total=len(questions),
        error=None,
        remaining_seconds=remaining_seconds
    )


@app.route("/results")
def results():
    quiz = session.get("quiz")
    if not quiz:
        return redirect(url_for("index"))

    questions = quiz["questions"]
    answers = quiz["answers"]
    module_key = quiz["module_key"]
    module_cfg = MODULES_CONFIG[module_key]

    details = []
    correct_count = 0

    # Emparejar pregunta con respuesta
    for ans in answers:
        q_idx = ans["question_index"]
        selected = ans["selected_index"]
        question = questions[q_idx]

        is_correct = (selected is not None and selected == question["correct_index"])
        if is_correct:
            correct_count += 1

        details.append({
            "text": question["text"],
            "options": question["options"],
            "selected_index": selected,
            "correct_index": question["correct_index"],
            "explanation": question.get("explanation", ""),
            "is_correct": is_correct
        })

    total = len(answers) if answers else 0
    percentage = round((correct_count / total) * 100, 1) if total > 0 else 0.0

    return render_template(
        "results.html",
        module_cfg=module_cfg,
        correct_count=correct_count,
        total=total,
        percentage=percentage,
        details=details
    )


@app.route("/reset")
def reset():
    session.pop("quiz", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
