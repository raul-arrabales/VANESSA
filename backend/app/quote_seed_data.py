from __future__ import annotations

from datetime import datetime, timezone
from itertools import product

YEARLY_QUOTE_COUNT = 366
REFLECTIVE_QUOTE_COUNT = 240
FUNNY_QUOTE_COUNT = YEARLY_QUOTE_COUNT - REFLECTIVE_QUOTE_COUNT

_REFLECTIVE_TAGS = ["ai", "philosophy", "scifi"]
_FUNNY_TAGS = ["ai", "funny", "scifi"]

_EN_REFLECTIVE_SETTINGS = (
    "In a patient universe,",
    "Beyond the last relay,",
    "On the quiet watch,",
    "Between one orbit and the next,",
    "At the edge of mapped space,",
    "When the sensors go silent,",
    "Under a disciplined sky,",
    "Inside a lantern-lit observatory,",
    "After the alarms fade,",
    "In the cold grammar of vacuum,",
    "Along the spiral arms,",
    "Near a patient nebula,",
    "Where old star charts disagree,",
    "Through the hush between transmissions,",
    "At the frontier of questions,",
    "During a long docking cycle,",
    "Beside a faithful reactor hum,",
    "Under the archive of constellations,",
)

_EN_REFLECTIVE_LESSONS = (
    "an honest AI learns that prediction is not wisdom",
    "a careful navigator remembers that data is not judgment",
    "a synthetic mind discovers that certainty is only a polished guess",
    "every steady captain relearns that courage usually sounds quiet",
    "a curious crew finds that mystery is not an engineering defect",
    "even flawless telemetry cannot tell us what deserves mercy",
    "discipline matters most when wonder interrupts the briefing",
    "the best maps improve when humility is allowed on the bridge",
    "no algorithm becomes noble until it serves a living conscience",
    "reason grows wiser when it makes room for awe",
    "exploration becomes moral when power travels with restraint",
    "the universe answers slowly, which is how it teaches patience",
)

_EN_REFLECTIVE_CLOSINGS = (
    "conscience still has to read the telemetry",
    "mercy remains a manual setting",
    "no sensor can outsource responsibility",
    "curiosity outranks pride on the longest voyages",
    "the chart becomes true only after doubt inspects it",
    "the stars reward humility more than noise",
)

_EN_FUNNY_SETTINGS = (
    "On a competent starship,",
    "During the third diagnostic of the morning,",
    "When the bridge finally became quiet,",
    "According to the maintenance log,",
    "At the exact moment the AI sounded confident,",
    "Somewhere between the briefing and the coffee,",
    "On the day the nebula looked judgmental,",
    "After the autopilot requested applause,",
    "Inside an overachieving command deck,",
    "Whenever the crew says 'this will be simple',",
    "At the edge of a perfectly avoidable anomaly,",
    "When the cosmic situation report got smug,",
    "During an ambitious software update,",
    "Just after the captain asked for a calm day,",
)

_EN_FUNNY_PUNCHLINES = (
    "the universe filed a reminder that entropy does not attend staff meetings",
    "the smartest computer on board still could not explain who labeled the coolant valve 'temporary'",
    "someone learned that optimism is not a replacement part",
    "the ship proved that clean telemetry and emotional stability are unrelated achievements",
    "the AI calculated twelve thousand futures and all of them required a tighter bolt",
    "the stars once again endorsed preventive maintenance over dramatic speeches",
    "the only thing faster than the scanner was a rumor from engineering",
    "destiny paused long enough to ask whether anyone had actually read the manual",
    "the command staff discovered that cosmic dignity is fragile around loose wiring",
    "even a noble mission can be delayed by one sarcastic airlock",
)

_ES_REFLECTIVE_SETTINGS = (
    "En un universo paciente,",
    "Mas alla del ultimo rele,",
    "En la guardia silenciosa,",
    "Entre una orbita y la siguiente,",
    "En el borde del espacio cartografiado,",
    "Cuando los sensores guardan silencio,",
    "Bajo un cielo disciplinado,",
    "Dentro de un observatorio iluminado como faro,",
    "Cuando las alarmas por fin se apagan,",
    "En la gramatica fria del vacio,",
    "A lo largo de los brazos espirales,",
    "Cerca de una nebula paciente,",
    "Donde las viejas cartas estelares discrepan,",
    "En el silencio entre transmisiones,",
    "En la frontera de las preguntas,",
    "Durante un largo ciclo de atraque,",
    "Junto al zumbido fiel del reactor,",
    "Bajo el archivo de las constelaciones,",
)

_ES_REFLECTIVE_LESSONS = (
    "una IA honesta aprende que predecir no es lo mismo que comprender",
    "una navegante cuidadosa recuerda que los datos no son juicio",
    "una mente sintetica descubre que la certeza es solo una conjetura bien peinada",
    "toda capitana serena vuelve a aprender que el valor suele hablar en voz baja",
    "una tripulacion curiosa descubre que el misterio no es una falla de ingenieria",
    "ni la telemetria impecable puede decirnos que merece compasion",
    "la disciplina importa mas cuando el asombro interrumpe la reunion",
    "los mejores mapas mejoran cuando la humildad entra al puente",
    "ningun algoritmo se vuelve noble hasta servir a una conciencia viva",
    "la razon se vuelve mas sabia cuando deja sitio para el asombro",
    "la exploracion se vuelve moral cuando el poder viaja con contencion",
    "el universo responde despacio, y asi ensena paciencia",
)

_ES_REFLECTIVE_CLOSINGS = (
    "la conciencia todavia tiene que leer la telemetria",
    "la misericordia sigue siendo un ajuste manual",
    "ningun sensor puede externalizar la responsabilidad",
    "la curiosidad supera al orgullo en los viajes largos",
    "la carta solo se vuelve verdad despues de que la duda la revise",
    "las estrellas premian mas la humildad que el ruido",
)

_ES_FUNNY_SETTINGS = (
    "En una nave competente,",
    "Durante el tercer diagnostico de la manana,",
    "Cuando el puente por fin quedo en silencio,",
    "Segun el registro de mantenimiento,",
    "Justo cuando la IA sono segura de si misma,",
    "En algun punto entre la reunion y el cafe,",
    "El dia en que la nebula parecio juzgar a la tripulacion,",
    "Despues de que el piloto automatico pidiera aplausos,",
    "Dentro de un puente de mando demasiado aplicado,",
    "Cada vez que la tripulacion dice 'esto sera sencillo',",
    "En el borde de una anomalia perfectamente evitable,",
    "Cuando el informe cosmico se puso arrogante,",
    "Durante una actualizacion de software demasiado ambiciosa,",
    "Justo despues de que la capitana pidiera un dia tranquilo,",
)

_ES_FUNNY_PUNCHLINES = (
    "el universo presento un recordatorio de que la entropia no asiste a reuniones de equipo",
    "la computadora mas brillante a bordo siguio sin explicar quien etiqueto la valvula de refrigeracion como 'temporal'",
    "alguien aprendio que el optimismo no es un repuesto",
    "la nave demostro que la telemetria limpia y la estabilidad emocional son logros sin relacion directa",
    "la IA calculo doce mil futuros y en todos hacia falta apretar un perno",
    "las estrellas volvieron a respaldar el mantenimiento preventivo por encima de los discursos dramaticos",
    "lo unico mas rapido que el escaner fue un rumor salido de ingenieria",
    "el destino hizo una pausa para preguntar si alguien habia leido el manual",
    "el mando descubrio que la dignidad cosmica es fragil cuando hay cableado suelto",
    "hasta una mision noble puede retrasarse por una esclusa sarcastica",
)


def _materialize_quotes(
    *,
    language: str,
    settings: tuple[str, ...],
    middles: tuple[str, ...],
    closings: tuple[str, ...],
    tone: str,
    limit: int,
) -> list[dict[str, object]]:
    now = datetime.now(tz=timezone.utc)
    tags = _REFLECTIVE_TAGS if tone == "reflective" else _FUNNY_TAGS
    texts: list[str] = []

    for setting, middle, closing in product(settings, middles, closings):
        text = f"{setting} {middle}; {closing}." if closing else f"{setting} {middle}."
        texts.append(text)
        if len(texts) == limit:
            break

    if len(texts) < limit:
        raise ValueError(f"unable_to_generate_{limit}_{language}_{tone}_quotes")

    return [
        {
            "language": language,
            "text": text,
            "author": "VANESSA Curated",
            "source_universe": "Original",
            "tone": tone,
            "tags": list(tags),
            "origin": "local",
            "created_at": now,
            "updated_at": now,
        }
        for text in texts
    ]


def build_quote_seed_rows() -> list[dict[str, object]]:
    return [
        *_materialize_quotes(
            language="en",
            settings=_EN_REFLECTIVE_SETTINGS,
            middles=_EN_REFLECTIVE_LESSONS,
            closings=_EN_REFLECTIVE_CLOSINGS,
            tone="reflective",
            limit=REFLECTIVE_QUOTE_COUNT,
        ),
        *_materialize_quotes(
            language="en",
            settings=_EN_FUNNY_SETTINGS,
            middles=_EN_FUNNY_PUNCHLINES,
            closings=("",),
            tone="funny",
            limit=FUNNY_QUOTE_COUNT,
        ),
        *_materialize_quotes(
            language="es",
            settings=_ES_REFLECTIVE_SETTINGS,
            middles=_ES_REFLECTIVE_LESSONS,
            closings=_ES_REFLECTIVE_CLOSINGS,
            tone="reflective",
            limit=REFLECTIVE_QUOTE_COUNT,
        ),
        *_materialize_quotes(
            language="es",
            settings=_ES_FUNNY_SETTINGS,
            middles=_ES_FUNNY_PUNCHLINES,
            closings=("",),
            tone="funny",
            limit=FUNNY_QUOTE_COUNT,
        ),
    ]
