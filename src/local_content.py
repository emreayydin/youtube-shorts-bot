"""Deterministische, quellenmarkierte Inhalte fuer den Offline-Modus.

Die Trivia-Lane darf keinen Textdienst benoetigen. Diese kleine, kuratierte
Faktenbank ist bewusst konservativ: jeder Eintrag hat eine klare Quelle und
eine fertige Sprecherfassung. Der Finanzmodus bleibt weiterhin voll
datengetrieben in ``finance_ranking.py``.
"""
from copy import deepcopy


class KeineNeuenInhalte(RuntimeError):
    """Es gibt keinen Fakt, der noch nicht gepostet wurde."""


VISUALS = [
    "cinematic scientific illustration, clean composition, no text",
    "macro documentary photography style, soft studio light, no text",
    "cinematic nature scene, realistic, high detail, no text",
    "minimal educational illustration, rich colors, no text",
]


FACTS = [
    {
        "category": "Astronomie",
        "title": "Ein Tag auf der Venus dauert länger als ihr Jahr",
        "hook": "Auf diesem Planeten ist ein Tag länger als ein Jahr",
        "body": "Auf der Venus dreht sich der Planet extrem langsam um die eigene Achse. Eine Drehung dauert länger als ein Umlauf um die Sonne. Deshalb ist ein Venustag länger als ein Venusjahr. Die Venus ist außerdem heißer als Merkur, obwohl Merkur näher an der Sonne liegt. Der Grund ist ihre dichte Atmosphäre, die Wärme festhält. Ein scheinbar vertrautes Wort wie Tag kann im All also etwas völlig anderes bedeuten.",
        "cta": "Welchen Planeten sollen wir als Nächstes testen?",
        "tags": ["Astronomie", "Venus", "Weltraum", "Wissenschaft", "Planeten"],
        "sources": ["NASA Solar System Exploration: Venus"],
    },
    {
        "category": "Astronomie",
        "title": "Ein Teelöffel Neutronenstern wäre unfassbar schwer",
        "hook": "Ein Teelöffel davon würde eine Milliarde Tonnen wiegen",
        "body": "Wenn ein massereicher Stern stirbt, kann sein Kern zu einem Neutronenstern kollabieren. Dabei wird Materie so dicht gepackt, dass ein winziges Stück davon auf der Erde unvorstellbar schwer wäre. Ein Teelöffel Neutronensternmaterie wird oft mit ungefähr einer Milliarde Tonnen verglichen. Das ist keine normale feste Oberfläche wie bei einem Planeten, sondern Materie unter extremem Druck. Ein Stern kann am Ende also kleiner als eine Stadt sein und trotzdem mehr Masse als die Sonne enthalten.",
        "cta": "Mehr kurze Fakten aus dem All gibt es täglich.",
        "tags": ["Astronomie", "Neutronenstern", "Weltraum", "Sterne", "Wissen"],
        "sources": ["NASA: Neutron Stars"],
    },
    {
        "category": "Wissenschaft",
        "title": "Blitze sind heißer als die Sonnenoberfläche",
        "hook": "Dieser Blitz ist heißer als die Oberfläche der Sonne",
        "body": "Ein Blitz erhitzt die Luft in seinem Kanal für einen winzigen Moment auf ungefähr 30.000 Kelvin. Die sichtbare Oberfläche der Sonne ist dagegen rund 5.800 Kelvin heiß. Genau diese plötzliche Erwärmung lässt die Luft explosionsartig ausdehnen. Der Knall, den wir als Donner hören, entsteht durch diese Druckwelle. Der Blitz ist also nicht nur hell: Er verändert die Luft so schnell, dass daraus ein Geräusch entsteht, das kilometerweit zu hören sein kann.",
        "cta": "Speichere den Fakt für den nächsten Gewittertag.",
        "tags": ["Wissenschaft", "Blitz", "Gewitter", "Physik", "Natur"],
        "sources": ["NOAA National Severe Storms Laboratory: Lightning"],
    },
    {
        "category": "Natur",
        "title": "Oktopusse haben drei Herzen",
        "hook": "Dieses Tier hat drei Herzen und blaues Blut",
        "body": "Ein Oktopus hat drei Herzen. Zwei davon pumpen Blut zu den Kiemen, das dritte versorgt den restlichen Körper. Sein Blut wirkt blau, weil es statt Hämoglobin das kupferhaltige Hämocyanin nutzt. Das hilft in kaltem, sauerstoffarmem Wasser. Beim Schwimmen wird das Körperherz weniger aktiv, weshalb viele Oktopusse lieber über den Meeresboden kriechen. Ausgerechnet die Fortbewegung, die spektakulär aussieht, ist für sie besonders anstrengend.",
        "cta": "Welches Tier sollen wir als Nächstes erklären?",
        "tags": ["Natur", "Oktopus", "Meer", "Tierwissen", "Biologie"],
        "sources": ["Smithsonian Ocean: Octopus Biology"],
    },
    {
        "category": "Natur",
        "title": "Honig kann sehr lange haltbar bleiben",
        "hook": "Dieses Lebensmittel kann praktisch nicht verderben",
        "body": "Honig enthält sehr wenig Wasser und ist von Natur aus sauer. Diese Kombination macht es vielen Mikroorganismen schwer, darin zu wachsen. Deshalb kann gut verschlossener Honig extrem lange haltbar bleiben. Er kann kristallisieren oder dunkler werden, ohne automatisch verdorben zu sein. Wichtig ist trotzdem: Feuchtigkeit und Verunreinigungen können die Haltbarkeit verändern. Die erstaunliche Eigenschaft kommt nicht von Magie, sondern von Chemie, Wassergehalt und dem Verhalten von Mikroorganismen.",
        "cta": "Folge für mehr überraschende Alltagsfakten.",
        "tags": ["Natur", "Honig", "Biologie", "Lebensmittel", "Wissen"],
        "sources": ["Smithsonian: Why Honey Does Not Spoil"],
    },
    {
        "category": "Biologie",
        "title": "Bananen sind botanisch Beeren",
        "hook": "Die Banane ist eine Beere, die Erdbeere nicht",
        "body": "In der Botanik zählt nicht der Geschmack, sondern der Aufbau der Frucht. Eine Beere entsteht aus einem einzigen Fruchtknoten und enthält Samen im Inneren. Die Banane erfüllt diese Definition. Die Erdbeere sieht zwar nach Beere aus, ist botanisch aber eine Sammelfrucht: Die kleinen Punkte außen sind die eigentlichen Einzelfrüchte. Alltagssprache und Botanik benutzen dasselbe Wort also für zwei sehr unterschiedliche Dinge.",
        "cta": "Schreib in die Kommentare, welcher Fakt dich überrascht hat.",
        "tags": ["Biologie", "Banane", "Erdbeere", "Botanik", "Natur"],
        "sources": ["Encyclopaedia Britannica: Berry"],
    },
    {
        "category": "Biologie",
        "title": "Bärtierchen überleben extreme Bedingungen",
        "hook": "Dieses winzige Tier kann fast alles einfrieren",
        "body": "Bärtierchen sind winzige Tiere, die in einen besonderen Ruhezustand wechseln können. Dabei verlieren sie fast ihr gesamtes Körperwasser und verlangsamen ihren Stoffwechsel extrem. In diesem Zustand überstehen manche Arten starke Kälte, Trockenheit und andere Belastungen. Das bedeutet nicht, dass sie unsterblich sind. Es bedeutet: Ihr Körper kann für eine Zeit auf fast Pause schalten und später wieder aktiv werden, wenn die Bedingungen besser sind.",
        "cta": "Mehr Biologie ohne unnötige Fachbegriffe gibt es hier.",
        "tags": ["Biologie", "Bärtierchen", "Mikrotiere", "Natur", "Wissenschaft"],
        "sources": ["NASA: Tardigrades"],
    },
    {
        "category": "Geschichte",
        "title": "Oxford ist älter als das Aztekenreich",
        "hook": "Diese Universität ist älter als das Aztekenreich",
        "body": "An der Universität Oxford wurde spätestens im frühen 12. Jahrhundert gelehrt. Das Aztekenreich in Zentralmexiko entstand erst viele Jahrhunderte später, im 15. Jahrhundert. Der Vergleich wirkt erstaunlich, weil beides in unserem Kopf einfach als alte Geschichte erscheint. Zeiträume werden greifbarer, wenn man sie miteinander verbindet: Während in Oxford bereits gelehrt wurde, lagen viele bekannte Reiche und Bauwerke der späteren Weltgeschichte noch weit in der Zukunft.",
        "cta": "Welche historischen Zeitvergleiche sollen wir prüfen?",
        "tags": ["Geschichte", "Oxford", "Azteken", "Historie", "Wissen"],
        "sources": ["University of Oxford: History of the University"],
    },
    {
        "category": "Geschichte",
        "title": "Cleopatra lebte näher an der Mondlandung",
        "hook": "Cleopatra lebte näher an uns als an den Pyramiden",
        "body": "Cleopatra lebte ungefähr zweieinhalb Jahrtausende nach dem Bau der großen Pyramide von Gizeh. Gleichzeitig trennen sie von der Mondlandung 1969 nur rund zweitausend Jahre. Der Abstand zwischen den Ereignissen war in ihrer Zeit also nicht gleichmäßig verteilt: Die Pyramiden waren für Cleopatra bereits uralte Geschichte. Dieser Vergleich zeigt, wie lang unsere Vorstellung von 'altem Ägypten' eigentlich ist.",
        "cta": "Speichere den Vergleich für den nächsten Geschichts-Quizabend.",
        "tags": ["Geschichte", "Cleopatra", "Ägypten", "Pyramiden", "Wissen"],
        "sources": ["Encyclopaedia Britannica: Cleopatra; Giza"],
    },
    {
        "category": "Technologie",
        "title": "Der Eiffelturm wächst im Sommer",
        "hook": "Im Sommer wird dieser Turm tatsächlich größer",
        "body": "Metall dehnt sich bei Wärme aus und zieht sich bei Kälte zusammen. Beim Eiffelturm kann dieser Effekt die Höhe im Sommer um mehrere Zentimeter verändern. Das Gebäude wird nicht umgebaut und bekommt auch keine neue Spitze: Die Eisenkonstruktion reagiert einfach auf die Temperatur. Ingenieure müssen solche Bewegungen bei großen Bauwerken einplanen, damit Material und Verbindungen die ständige Ausdehnung sicher mitmachen.",
        "cta": "Folge für weitere Fakten, die man draußen beobachten kann.",
        "tags": ["Technologie", "Eiffelturm", "Physik", "Paris", "Wissen"],
        "sources": ["Tour Eiffel: The Eiffel Tower and temperature"],
    },
    {
        "category": "Natur",
        "title": "Wombats machen würfelförmigen Kot",
        "hook": "Dieses Tier produziert kleine Würfel",
        "body": "Wombats hinterlassen tatsächlich würfelförmigen Kot. Die Würfel entstehen nicht erst draußen, sondern durch unterschiedliche Spannungen in verschiedenen Bereichen ihres Darms. Die Form hilft vermutlich dabei, die Markierungen auf Felsen und Baumstämmen zu stapeln, ohne dass sie wegrollen. Es ist ein ungewöhnliches Beispiel dafür, wie der Körper eines Tieres eine praktische Aufgabe mit einem Ergebnis löst, das für uns fast erfunden klingt.",
        "cta": "Mehr seltsame, aber echte Tierfakten folgen.",
        "tags": ["Natur", "Wombat", "Tierwissen", "Biologie", "Australien"],
        "sources": ["Australian Museum: Wombat biology"],
    },
    {
        "category": "Wissenschaft",
        "title": "Haie sind älter als Bäume",
        "hook": "Haie schwammen schon vor den ersten Bäumen",
        "body": "Die ältesten Vorfahren der Haie lebten bereits Hunderte Millionen Jahre vor heute. Viele Hai-Linien sind damit älter als die ersten großen Wälder an Land. Das heißt nicht, dass ein heutiger Hai unverändert aus dieser Zeit stammt. Es bedeutet, dass seine evolutionäre Linie sehr weit zurückreicht. Während sich Kontinente, Meere und Arten veränderten, blieb der Grundbauplan dieser Tiere erstaunlich erfolgreich.",
        "cta": "Welches Tier hat die älteste Geschichte? Schreib deine Vermutung.",
        "tags": ["Natur", "Haie", "Evolution", "Ozean", "Wissenschaft"],
        "sources": ["Smithsonian Ocean: Sharks through time"],
    },
]


# Die grosse, gepruefte Sammlung (seit 01.10.2026, wird woechentlich vom
# Kanal-Agenten ergaenzt). Doppelte Titel zaehlen nur einmal.
from faktenbank import FAKTENBANK  # noqa: E402

try:  # von Gemini montags nachgefuellt (scripts/faktenbank_nachfuellen.py)
    from faktenbank_neu import NEU as _NEU  # noqa: E402
except ImportError:
    _NEU = []

_bekannt = {x["title"].lower() for x in FACTS}
for _x in FAKTENBANK + _NEU:
    if _x["title"].lower() not in _bekannt:
        FACTS.append(_x)
        _bekannt.add(_x["title"].lower())


def _available(category: str | None, avoid: list[str]) -> list[dict]:
    avoid_set = {str(x).strip().lower() for x in (avoid or [])}
    exact = [x for x in FACTS if category and x["category"].lower() == category.lower()]
    pool = exact or list(FACTS)
    fresh = [x for x in pool if x["title"].lower() not in avoid_set]
    if not fresh and exact:
        fresh = [x for x in FACTS if x["title"].lower() not in avoid_set]
    if not fresh:
        # Frueher: "fresh or pool" - also einfach von vorne. Eine Wiederholung
        # kostet mehr als ein ausgefallener Slot (YouTube drueckt sie, und fuer
        # das Partnerprogramm gilt sie als wiederholender Inhalt).
        raise KeineNeuenInhalte("Lokale Faktenbank ist aufgebraucht")
    return fresh


def generate_fact(category: str | None = None, avoid: list[str] | None = None) -> dict:
    pool = _available(category, avoid or [])
    item = pool[len(avoid or []) % len(pool)]
    data = deepcopy(item)
    data["image_prompts"] = list(item.get("image_prompts") or VISUALS)
    data["sources"] = list(item["sources"])
    return data


def generate_compilation(category: str | None = None,
                         avoid: list[str] | None = None) -> dict:
    avoid_set = {str(x).strip().lower() for x in (avoid or [])}
    pool = [x for x in FACTS if x["title"].lower() not in avoid_set]
    pool = pool or list(FACTS)
    selected = [pool[i % len(pool)] for i in range(10)]
    facts = [{
        "headline": item["title"][:40],
        "text": item["body"],
        "source": item["sources"][0],
        "image_prompt": VISUALS[0],
    } for item in selected]
    topic = category or "Faszinierende Fakten"
    return {
        "title": f"10 erstaunliche Fakten über {topic}",
        "topic": topic,
        "intro": "Manche Fakten klingen erfunden, sind aber gut belegt. Hier kommen zehn Beispiele, die unsere Sicht auf Natur, Geschichte und Wissenschaft verändern.",
        "hook_visual": VISUALS[0],
        "facts": facts,
        "outro": "Welcher Fakt war für dich neu? Schreib ihn in die Kommentare und abonniere für die nächste Folge.",
        "tags": ["Fakten", "Wissen", "Trivia", "Wissenschaft", "Geschichte"],
        "visual_tags": ["nature", "sky", "mountains", "scientific illustration"],
        "category": topic,
    }
