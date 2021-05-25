from __future__ import annotations

import discord
import yaml
import os
import argparse

from datetime import datetime
from typing import *
from random import choice, randint, uniform
from dataclasses import dataclass
from enum import Enum, auto
from functools import partial


script_path = os.path.dirname(os.path.abspath(__file__))
backup_path = os.path.join(script_path, "backup")


# slovník dat pro všechny teamy
# klíč je vždy ID kanálu daného teamu
data = { }
channels = { }
org_channel = None

started = False
last_save_time = datetime.now()

async def save():
    """Uloží stav hry."""
    global data, org_channel

    if not os.path.exists(backup_path):
        os.mkdir(backup_path)

    backup_name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".yaml"

    with open(os.path.join(backup_path, backup_name), "w") as f:
        yaml.dump(data, f)


def load():
    """Nahraje stav hry."""
    global data

    # žádný backup
    if len(os.listdir(backup_path)) == 0:
        return

    # nejnovější backup
    backup_name = sorted(os.listdir(backup_path))[-1]
    with open(os.path.join(backup_path, backup_name), "r") as f:
        data = yaml.safe_load(f)


# ---

class TicTacToe:

    def stripUnwanted(data):
        d = list(data)
        while len(d) != 0 and (not isinstance(d[0], int) or d[0] <= 0):
            d.pop(0)
        return d

    def show(data):
        """Display the board neatly."""
        data = TicTacToe.stripUnwanted(data)

        board = [
                [" ", " ", " "],
                [" ", " ", " "],
                [" ", " ", " "],
                ]

        for i in range(0, len(data), 2):
            i = data[i] - 1
            board[i // 3][i % 3] = "X"

        for i in range(1, len(data), 2):
            i = data[i] - 1
            board[i // 3][i % 3] = "O"

        result = f"```\n"
        for i, row in enumerate(board):
            result += "|".join(row) + "\n" + ("" if i == len(board) - 1 else "-----\n")

        return result + "```"

    def won(data):
        """0 if draw, 1 if p1 win, 2 if p2 win."""
        data = TicTacToe.stripUnwanted(data)

        p1 = [data[i] - 1 for i in range(0, len(data), 2)]
        p2 = [data[i] - 1 for i in range(1, len(data), 2)]

        wins = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))

        # p1 wins
        for win in wins:
            for tile in win:
                if tile not in p1:
                    break
            else:
                return 1

        # p2 wins
        for win in wins:
            for tile in win:
                if tile not in p2:
                    break
            else:
                return 2

        # draw
        return 0

    def valid_moves(data):
        """Valid moves for either player."""
        data = TicTacToe.stripUnwanted(data)

        return [i for i in range(1, 10) if i not in data]


# ---


client = discord.Client()

class Utilities:
    def get_data(id):
        global data
        return data[id]

    def get_location(id):
        return locations[Utilities.get_data(id)['location']]

    def set_location(id, location: Location):
        Utilities.get_data(id)['location'] = locations.index(location)

    def get_location_position(id):
        return Utilities.get_data(id)['location_position']

    def set_location_position(id, position):
        Utilities.get_data(id)['location_position'] = position

    def get_items(id):
        return Utilities.get_data(id)['items']

    def get_channel(id):
        global channels
        return channels[id]


class Action:
    """Akce, které mohou být na konci dialogů."""

    def obtainItem(item):
        """Získání daného itemu."""
        return partial(lambda i, id: Utilities.get_items(id).append(i.value), item)

    def moveToMinigame(id):
        """Přesun do minihry dané lokace."""
        Utilities.get_location_position(id).append(-1)


# ---------------------------------------- CONTENT ----------------------------------------

class Item(Enum):
    """Enum všech itemů."""
    vysano = "vysano"
    rozsviceno = "rozsviceno"
    zrychleno = "zrychleno"
    pametfix = "pametfix"
    zdrojporazen = "zdrojporazen"
    pametsofware = "pametsofware"
    mbinstruction = "mbinstruction"


class Special(Enum):
    """Speciální vlastnosti různých lokací."""
    darkness = auto()  # píše se ve spoilerech
    loud = auto()      # musí se řvát
    please = auto()      # musí se řvát


def no(item):
    """Parciální funkce na to, že team item nemá."""
    return partial(lambda x, y: x not in y, item)

def yes(item):
    """Parciální funkce na to, že team item má."""
    return partial(lambda x, y: x in y, item)


def format_remaining_time(s):
    if s >= 60 * 60 * 24 * 7:
        return f"Zbývá ~`{s // (60 * 60 * 24 * 7)}` týdnů."

    if s >= 60 * 60 * 24:
        return f"Zbývá ~`{s // (60 * 60 * 24)}` dnů."

    if s >= 60 * 60:
        return f"Zbývá ~`{s // (60 * 60)}` hodin."

    if s >= 60:
        return f"Zbývá ~`{s // (60)}` minut."

    return f"Zbývá ~`{s}` sekund."


@dataclass(frozen=True)
class Vysavac:
    name = "Vysavač"
    at = "u vysavače"
    to = "k vysavači"

    description = """Přes síťovou kartu se vám povedlo bit po bitu přenést se k vysavači. Měli jste pocit, že se cestou něco zadrhlo,
    tak jste si radši třikrát zkontrolovali své kontrolní součty. A opravdu, kus vám chybí!!! Co teď budete děla... Ah, počkat,
    poslední kus se právě přenesl. Uf, vypadá to v pořádku, díky tvůrcům za to, že jste se rozhodli přenést se pomocí TCP a ne jen UDP.

    Když jste se pořádně rozhlédli okolo, tak jste zjistili, že jste se asi dostali do obslužné stanice těsně vedle vysavače. Ten
    vedle vás spokojeně podřimuje a nevypadá to, že by vám chtěl věnovat jakoukoliv pozornost. Prozkoumali jste obvody obslužné stanice
    a zjistili jste, že můžete provádět nějaké akce.
    """

    dialogue = [
        (no(Item.vysano.value), [],
            [('zapojit', "Zkusit `zapojit` spící vysavač do zásuvky.", ["Jau, co děláš, já jsem na baterky!"],
                [('promiň', '`Promiň`, to nám nedošlo.', [], [])]
             ),
             ('popostrčit', "Zkusit vysavač `popostrčit`.", ["Co do mě strkáš?"],
                 [("povysávat", "Potřebujeme u počítače trochu `povysávat`, pomůžeš?", ["Pokud do mě už nebudete strkat, tak ano. Potřeboval bych ale navigovat."],
                     [('nanavigujeme', "Jasně, `nanavigujeme`!", [], Action.moveToMinigame),
                      ('ne', "Promiň, spíš `ne`, to zní komlikovaně.", [], []),
                     ]
                  ),
                 ]
             ),
            ]
        ),
        (yes(Item.vysano.value), ["Rrrrrrrrrrrrr.", "Rrrr.", "Rrrrrrr."], []
        )
    ]

    special = []


@dataclass(frozen=True)
class Sitovka:
    name = "Síťová karta"
    at = "u síťové karty"
    to = "k síťové kartě"

    description = """Okolo vás probíhá spousta komunikace, vypadá to tu jako na velmi rušné poště. Z velké temné chodby vybíhají velkou
    rychlostí pakety s velkým batůžkem dat na zádech, které si síťová karta prohlíží a podle čísel portů je posílá v počítači dál. Jak tak provoz
    pozorujete, tak si všimnete, že občas dorazí paket, který v ruce drží již úplně prázdné přesýpací hodiny. Před každým takovýmhle paketem
    se zjeví Paketový SMRŤ, výmluvně se na něj podívá, mávne bitovou kosou a paket se rozplyne. Otřesete se - snad existuje nějaké paketové nebe.

    Naopak na druhé straně si všímáte veliké antény, do které odvážně lezou jiné pakety s pilotní čepicí narvanou na hlavě. To je jen pro ty odvážné,
    ale na nějaké místa se jinak asi nedostanete.

    Ale každopádně, pokud chcete nějaká data, tak tady jste určitě na správném místě.
    """

    _zadani_ksp = (
        'ksp', "Chtěli bychom si stáhnout zadání `KSP`, dáš nám nějaké?",
        ["Dobře, ale vyberu pro vás to nejkratší, dejte mi chvilku.... Tak jo, tady ho máte: 33-5-X1: Toto je praktická open-data úloha. V odevzdávacím systému si necháte vygenerovat vstupy a odevzdáte příslušné výstupy. Záleží jen na vás, jak výstupy vyrobíte. Výše uvedené zadání úlohy je kompletní a přesně takové, jaké má být. Žádná část mu nechybí ani nepřebývá."], [("úžasně", "To zní naprosto `úžasně`, do toho rozhodně jdu!", [], [])]
    )

    dialogue = [
        (yes(Item.rozsviceno.value), ["Hej, zaslechla jsem teď <ještě další náhodný nezajímavý drb>."], []),
        (yes(Item.pametfix.value), ["Hej, zaslechla jsem teď <další náhodný nezajímavý drb>."],
            [('firmware', "Pamět je v pořádku, ale potřebujeme teď stáhnout nějaký další `firmware`, tentokrát pro LED světla k větráku?", ["Ok, jdeme na to."],
                [('ok', '`Ok`, jdeme.', [], Action.moveToMinigame)]
             ),
             _zadani_ksp,
            ]
        ),
        (yes(Item.pametsofware.value), ["Co tu ještě děláš? Utíkej!"], []),
        (no(Item.pametfix.value), ["Hej, zaslechla jsem teď <náhodný nezajímavý drb>."],
            [('firmware', "To je zajímavý. Každopádně potřebujeme stáhnout nějaký `firmware` pro paměť, pomůžeš?", ["Pomůžu, ale prakticky všechno v poslední době zapomíná. Doporučuji si pospíšit."],
                [('víme', '`Víme` o tom, pospíšíme.', [], Action.moveToMinigame)]
             ),
             _zadani_ksp,
            ]
        ),
    ]

    special = []


@dataclass(frozen=True)
class Motherboard:
    name = "Motherboard"
    at = "u motherboardu"
    to = "k motherboardu"

    description = """Motherboard, matka všech komponent v počítač, tedy aspoň těch, které za to stojí (kdo by se staral o nějaké nepotřebné periferie, že ano).
    Její kořeny skrze sběrnice sahají všude, blahodárně napájí všechny své součástky, stará se, aby si mezi sebou povídaly, a dohlíží i na to, aby nevznikaly nějaké
    problémy. Přesto si ve vzdáleném rohu desky všímáte, že tam je svět nějaký temnější a když oslovíte náhodné kolemjdoucí data putující po sběrnici, tak vás jen
    šeptem varují: "Tam nechoď, tam je velká zlá součástka. Nikdo neví, jak se tam dostala, ale umí otrávit všechna data, co k ní dojdou. Říká se, že je to špión... ale já ti to neřekl, jo. Nikdy jsme se neviděl, jasné?"

    Možná byste si s motheroardem měli promluvit. Vlastně vám není jasné, kde začít mluvit, ale máte takový pocit, že ať jste kdekoliv, tak vás uslyší.
    Přecijen byste ale mohli dojít do nějakého klidnějšího kouta a nestát uprostřed sběrnice.
    """

    _q = ["Co chceš?", "Všechno tu dělám sama.", "Ty moje děti jsou fakt spratci, ani si spolu beze mě nepovídají."]

    dialogue = [
        (yes(Item.mbinstruction.value), ["Tak, já jsem připravená poslat do škodlivé součástky proud, napájecí cesty jsou připravené. Jestli je teda zdroj ochotný dýt proud navíc, je to docela skrblík. Pokud to s ním máte domluvené, tak se vydejte za procesorem, aby to spustil. Pamatujte, je to napájecí instrukce `XC00P147`."], []),
        (no(Item.vysano.value), _q,
            [('přepneš', "V počítači je škodlivá součástka, kterou potřebujeme odpálit. `Přepneš` se prosím do režimu, abychom do ní mohli poslat více proudu?",
                ["Takhle špinavá rozhodně ne, podívejte na moje rozvodné obvody. Pošlu skrz ně víc proudu, zahřejí se, zapálí ten prach a všichni tady umřou. To chceš?"],
                [('ok', '`Ok`, zkusíme s tím něco udělat.', [], [])]
             ),
            ]
        ),
        (no(Item.pametfix.value), _q,
            [('přepneš', "S pomocí vysavače jsme všude okolo uklidili. `Přepneš` se teď?", ["Mohla bych, ale potřebuji instrukce, které jsou uložené někde v paměti. Zdá se ale, že paměť zapomněla, kde jsou..."],
                [('ok', '`Ok`, zkusíme paměti pomoct.', [], [])]
             ),
            ]
        ),
        (yes(Item.pametfix.value), _q,
            [('přepneš', "Paměti jsme aktualizovali firmware, už si vzpomněla! Přečteš instrukce a `přepneš` se?", ["Dobře, načítám instrukce... flashuji napájecí subprocesory... hotovo přepínám se."],
                [('ok', '`Ok`, moc díky!.', [], Action.obtainItem(Item.mbinstruction))]
             ),
            ]
        ),
    ]
    special = []


@dataclass(frozen=True)
class Pamet:
    name = "Paměť"
    at = "u paměti"
    to = "k paměti"

    description = """Když jste vešli do álejí paměti, tak se vám naskytl pohled na obrovskou kartotéku s miliony přihrádek po obou stranách.
    V kartotéce operovalo množství nakladačů, od malinkatých co najednou nesly jenom jednu přihrádku až po obrovská monstra, která najednou
    zvládla nabrat desítky přihrádek a poslat je po sběrnici pryč. Mezi nimi se proplétaly zase nakladače, které vybíraly jedničky a nuly ze sběrnic,
    balily je do krabic a do přihrádek ukládaly.

    Po chvíli pozorování jste si ale všimli zmatku. Některé nakladače zmateně jezdily sem a tam, jakoby nemohly přijít na to, do které části paměti
    některé z přihrádek uložily. Uprostřed paměťové áleje jste si všimli osamoceně sedící paměti. Dojdete k ní?
    """

    dialogue = [
        (yes(Item.pametfix.value), ["Tebe si pamatuju!"], []),
        (no(Item.pametsofware.value), ["Známe se? To je jedno; slyšela jsem teď super vtip. Chceš ho slyšet?"],
            [('nechci', 'Spíš `nechci`, docela spěchám.', [], []),
             ('chci', "Rozhodně `chci`, to zní skvěle!", ["Anglický nebo český?"],
                [('anglický', 'Klidně `anglický`.', ["The first computer bug actually involved Adam and Eve - their Apple only took one bite and it was a total disaster."],
                    [('aktualizuješ', 'To je skvělé. `Aktualizuješ` se prosím? Nový firmware by mohl pomoci tvému zapomínání', ["Žádný software si nepamatuji, že by mi síťová karta odříkávala. Kdy že to bylo?"],
                        [('ok', '`ok`, zkusíme nějaký firmware stáhnout...', [], [])]
                     ),
                    ],
                 ),
                 ('český', 'Spíše `český`.', ["Ťuk ťuk!\nKdo tam?\nRekurze.\nJaká rekurze?\nŤuk ťuk!"],
                    [('aktualizuješ', 'To je skvělé. `Aktualizuješ` se prosím? Nový firmware by mohl pomoci tvému zapomínání', ["Žádný software si nepamatuji, že by mi síťová karta odříkávala. Kdy že to bylo?"],
                        [('ok', '`ok`, zkusíme nějaký firmware stáhnout...', [], [])]
                     ),
                    ],
                 ),
                ],
             ),
            ]
        ),
        # ano, je to více-méně copy-paste toho nahoře
        # ano, je to fuj
        (yes(Item.pametsofware.value), ["Známe se? To je jedno; slyšela jsem teď super vtip. Chceš ho slyšet?"],
            [('nechci', 'Spíš `nechci`, docela spěchám.', [], []),
             ('chci', "Rozhodně `chci`, to zní skvěle!", ["Anglický nebo český?"],
                [('anglický', 'Klidně `anglický`.', ["The first computer bug actually involved Adam and Eve - their Apple only took one bite and it was a total disaster."],
                    [('aktualizuješ', 'To je skvělé. `Aktualizuješ` se prosím? Nový firmware by mohl pomoci tvému zapomínání', ["Na něco si vzpomínám! Jdu na to."],
                        [('ok', '`ok`, to se povedlo.', [], Action.obtainItem(Item.pametfix))]
                     ),
                    ],
                 ),
                 ('český', 'Spíše `český`.', ["Ťuk ťuk!\nKdo tam?\nRekurze.\nJaká rekurze?\nŤuk ťuk!"],
                    [('aktualizuješ', 'To je skvělé. `Aktualizuješ` se prosím? Nový firmware by mohl pomoci tvému zapomínání', ["Na něco si vzpomínám! Jdu na to."],
                        [('ok', '`ok`, to se povedlo.', [], Action.obtainItem(Item.pametfix))]
                     ),
                    ],
                 ),
                ],
             ),
            ]
        ),
    ]

    special = []


@dataclass(frozen=True)
class Zdroj:
    name = "Zdroj"
    at = "u zdroje"
    to = "ke zdroji"

    description = """Cestou ke zdroji jste se málem nechali seškvařit probíhajícím útvarem elektronů, jejich velitel křičel něco jako: "Póóóhyb, póóóhyb, myslíte si, že grafická karta se bez nás obejde? I vaše elektronová babička běhala rychlejc. Póóóhyb."
    Vyhnuli jste se jim úskokem do nevyužité napájecí větve, pak jste se oklepali a už opatrně u stěny jste došli až do zdroje.

    Tady to celé hučí, funí, bzučí a ve vzduchu cítíte všechen ten výkon. Z vrchu přichází od větráku neustálý proud vzduchu, ale i s ním je tu docela teplo.
    Ani si nechcete představit, co by se stalo, kdyby najednou přestal foukat.
    """

    # Slepá cesta navíc nikdy neuškodí ;)
    _vypnes_se = ('vypneš', "`Vypneš` se prosím?", ["Dobř... tak počkat, máte k tomuhle pověření? Jste od tlačítka? Nebo jdete s příkazem od procesoru? Chci vidět vaše pověření a to hned! Nemáte? Tak to nic nebude."], [("pardón", "`Pardón`, to jsme nevěděli.", [], [])])
    _nic = ('nic', "Vlastně `nic`, promiň že rušíme.", [], [])

    dialogue = [
        (no(Item.zrychleno.value), ["Na co čumíš?", "Ano, 350W, čteš to správně."],
            [('navýšit', "Můžeš prosím `navýšit` proud do procesoru?", ["Ani náhodou, je tu hrozný horko."],
                [('ok', '`Ok`, zkusíme s tím něco udělat.', [], [])]
             ),
             _vypnes_se,
             _nic,
            ]
        ),
        (no(Item.zdrojporazen.value), ["Na co čumíte?", "Ano, 350W, čtete správně."],
            [('navýšit', "Můžeš prosím `navýšit` proud do procesoru?", ["Mohl bych, ale musíš mi dokázat, že na to máte."],
                [('co', 'Na `co` máme?', ["Přece na to. Poražte mě v piškvorkách a proud je váš."],
                    [('porazím', "`Porazím` tě hravě, sleduj.", [], Action.moveToMinigame),
                     ('ne', "To spíš `ne`, piškvorky hrát neumíme.", [], []),
                    ],
                 )
                ]
             ),
             _vypnes_se,
             _nic,
            ]
        ),
        (yes(Item.zdrojporazen.value), ["Respekt.", "Pěkná práce."], [])
    ]


    special = []


@dataclass(frozen=True)
class Vetraky:
    name = "Větrák"
    at = "u větráku"
    to = "k větráku"

    description = """Šplháte větrací šachtou od zdroje k větráku a cítíte narůstající průvan. Za chvíli je tu takový hluk, že si myslíte, že už větší být nemůže. Ale pak vylezete za další záhyb a ještě se zesílá.
    Tady mluvení nedává smysl, budete muset řvát. A to ještě jenom po větru, jinak vás stejně nikdo neuslyší. Navíc za záhybem už také přestalo prosvítat světlo ze zdroje a vám asi nezbude nic jiného, než
    si na všechno kolem svítit.
    """

    dialogue = [
        (yes(Item.zrychleno.value), ["rychlejc to neumím!"], []),
        (no(Item.rozsviceno.value), ["co se děje? kdo tam?"],
            [('zrychlit', "potřebujeme více chlazení pro zdroj, můžeš se prosím `zrychlit`?", ["je tu tma jako v pytli, potřebuju lepší firmware osvětlení!"],
                [('dobře', '`dobře`, nějaké ti zkusíme sehnat.', [], [])]
             ),
            ]
        ),
        (yes(Item.rozsviceno.value), ["to mi tu to hezky svítí."],
            [('zrychlit', "můžeš se tedy prosím `zrychlit` teď?", ["ok, zkusím to."],
                [('dobře', '`dobře`, díky!', [], Action.obtainItem(Item.zrychleno))]
             ),
            ]
        ),
    ]

    special = [Special.loud, Special.darkness]


@dataclass(frozen=True)
class Procesor:
    name = "Procesor"
    at = "u procesoru"
    to = "k procesoru"

    description = """Stoupáte po schodech z motherboardu až na bájný vrcholek patice, kde sídlí vševědoucí procesor. Cestou minete řady kondenzátorů stojících
    na stráži okolo procesoru a pak překročíte hranu patice a vejdete do paláce procesoru.

    Na hlavě má obrovskou hliníkovou korunu, na jejímž vrcholku má ještě svůj vlastní osobní větrák a vítr z něj mu čechrá jeho stříbrné vlasy. Stojí na tisících
    zlatých nožek a když se na procesor podíváte, tak zahlédnete několik hlav, kde každá dělá něco úplně jiného. Ještě nikdy jste nezahlédli někoho tak
    efektivního. Do paláce proudí zástupy žadatelů, kteří chtějí chvilku jeho času, a procesor se ochotně každému aspoň chviličku věnuje. Někdy si sice musí
    žadatel chviličku počkat, ale pak je přijat se vší parádou.

    I na vás snad za chviličku přijde řada a jedna z hlav procesoru se vás laskavě ujme.
    """

    dialogue = [
        (lambda _: True, ["Přišli jste k části procesoru a zaklepali na firewall. Chvilku na něj prosím počkejte."], []),
    ]

    special = []


# není úplně hezké, ale co naděláš...
locations = [Vysavac(), Sitovka(), Motherboard(), Pamet(), Zdroj(), Vetraky(), Procesor()]
vysavac, sitovka, motherboard, pamet, zdroj, vetraky, procesor = locations

paths = {
    vysavac: [sitovka],
    sitovka: [vysavac, motherboard],
    motherboard: [pamet, procesor, zdroj, sitovka],
    pamet: [motherboard],
    zdroj: [motherboard, vetraky],
    vetraky: [zdroj],
    procesor: [motherboard],
}

end_game_text = """
    Přesvědčili jste procesor, aby vyslal po sběrnici instrukci `XC00P147`. Na sběrnici, na které poslouchaly
    naflashované napájecí čipy základní desky. Trvalo to jen zlomek sekundy, během které si napájecí čipy
    u zdroje ověřily, že jim umí dodat dostatek proudu, a pak již otevřely cestu proudu do osamocené napájecí
    větve vedoucí do rohu desky. Zároveň vypnuly na této lince všechny proudové ochrany.

    Napětí se skokově zvedlo a zlý invazní čip, který nějaký útočník přidal na okraj základní desky aby odposlouchával
    a škodil, se začal potit. Ale ještě to zvládal. Napájecí větev se začala postupně zahřívat (ještě, že jste z ní odstranili
    prach!) a větrák u zdroje se roztočil na nejvyšší výkon, ale zdroj tu zátěž zvládl.

    "Ještě pár sekund, už to bude," říkala si základní deska, která začínala cítit, že se napájecí větev rozžhavuje stále
    více a více. A najednou prásk! Ze zlého čipu v rohu základní desky najednou unikl všechen magický kouř a plastový obal
    z toho nejčernějšího plastu bez potisku se roztekl. Zbytek počítače však žil a všechny komponenty cítily, jak v tu chvíli
    zmizela přítomnost čehosi zlého, co je tu poslední dobou strašilo.

    "Děkuji vám," prohlásil procesor a vy jste najednou cítili, jak vás vesmírná síla volá kamsi dál. Uklonili jste
    se procesoru a pomalu jste se vznesli z vodičů do vzduchu a pak kamsi do dáli. Další počítače čekaly na svojí
    záchranu a vy jste si v tuto chvíli uvědomili, že to je přesně vaše poslání.

    Pokračování příště…
"""

# ---------------------------------------- CONTENT ----------------------------------------

async def update(id, response) -> bool:
    """Upraví stav pro daný team podle toho, jak zareagovali. Vrátí true/false podle toho,
    zda se update povedl a má se volat write."""
    global org_channel

    location = Utilities.get_location(id)
    position = Utilities.get_location_position(id)
    items = list(Utilities.get_items(id))

    sanitized_response = response.strip().lower()

    if position != None:
        position = list(position)

        # jsme-li v minihře
        if len(position) != 0 and isinstance(position[-1], int):
            if location == vysavac:
                pos = (4, 1)
                solution = [
                    "#########",
                    "#### ####",
                    "####    #",
                    "#   ### #",
                    "# #     #",
                    "# #######",
                    "# #######",
                    "#########",
                        ]

                mapping = {
                        "l": ("doleva", (-1, 0)),
                        "r": ("doprava", (1, 0)),
                        "u": ("nahoru", (0, -1)),
                        "d": ("dolů", (0, 1)),
                        }

                if sanitized_response.replace("l", "").replace("u", "").replace("r", "").replace("d", "") != "":
                    await send_with_special(id, f"**{location.name}:** V instrukcích jsou špatné znaky!", location.special)
                    return False

                for char in sanitized_response:
                    pos = (pos[0] + mapping[char][1][0], pos[1] + mapping[char][1][1])

                    if solution[pos[1]][pos[0]] == "#":
                        await send_with_special(id, f"**{location.name}:** Při jízdě {mapping[char][0]} jsem narazil do zdi. Vracím se zpět.", location.special)
                        return False

                if pos == (1, 6):
                    await send_with_special(id, f"**{location.name}:** Úspěšně jsem k počítači dojel! Vysávám...", location.special)
                    Utilities.set_location_position(id, [])
                    Utilities.get_items(id).append(Item.vysano.value)
                    return True

                await send_with_special(id, f"**{location.name}:** Do ničeho jsem nenarazil, ale k počítači jsem se nedostal. Vracím se zpět.", location.special)
                return False

            if location == zdroj:
                try:
                    pos = int(sanitized_response)

                    if not (1 <= pos <= 9):
                        await send_with_special(id, f"**{location.name}:** Neumíš počítat? `{pos}` není platný.", location.special)
                        return False

                    data = Utilities.get_location_position(id)
                    valid_moves = TicTacToe.valid_moves(data)

                    if pos not in valid_moves:
                        await send_with_special(id, f"**{location.name}:** No tak tam asi, ne, tam už něco je.", location.special)
                        return False

                    data.append(pos)

                    if TicTacToe.won(data) == 2:
                        await send_with_special(id, f"**{location.name}:** Pff, slušný výkon, proud máte navýšený." + "\n" + TicTacToe.show(data), location.special)
                        Utilities.set_location_position(id, [])
                        Utilities.get_items(id).append(Item.zdrojporazen.value)
                        return True

                    valid_moves = TicTacToe.valid_moves(data)
                    data.append(choice(valid_moves))

                    if TicTacToe.won(data) == 1:
                        await send_with_special(id, f"**{location.name}:** Ha, vyhrál jsem! Zkus to třeba příště." + "\n" + TicTacToe.show(data), location.special)
                        Utilities.set_location_position(id, [])
                        return True

                    if TicTacToe.won(data) == 0 and len(TicTacToe.valid_moves(data)) == 0:
                        await send_with_special(id, f"**{location.name}:** Remíza, takže smůla! Zkus to někdy jindy." + "\n" + TicTacToe.show(data), location.special)
                        Utilities.set_location_position(id, [])
                        return True

                    msg = choice([f"**{location.name}:** Zajímavý tah.", f"**{location.name}:** Hmm...", f"**{location.name}:** Slabý tah."]) + "\n" + TicTacToe.show(data)

                    await send_with_special(id, msg, location.special)
                    return False


                except ValueError:
                    await send_with_special(id, f"**{location.name}:** Co to meleš, `{sanitized_response}` není číslo.", location.special)
                    return False

            if location == sitovka:
                knp = ["kámen", "nůžky", "papír"]
                if sanitized_response not in knp:
                    await send_with_special(id, f"**{location.name}:** Hrajeme `kámen`, `nůžky` nebo `papír`!", location.special)
                    return False

                faejio = choice(knp)

                if sanitized_response == faejio:
                    await send_with_special(id, f"**{location.name}:** Také jsem měl `{faejio}`, remíza.", location.special)
                    return False

                if knp.index(sanitized_response) == (knp.index(faejio) - 1) % len(knp):
                    msg = f"Měl jsem `{faejio}`, vyhrál jsi!"
                    Utilities.get_location_position(id)[-1] = int(Utilities.get_location_position(id)[-1] / uniform(5, 10))
                else:
                    msg = f"Měl jsem `{faejio}`, prohrál jsi!"
                    Utilities.get_location_position(id)[-1] = int(Utilities.get_location_position(id)[-1] / uniform(2, 3))

                if Utilities.get_location_position(id)[-1] < 10:
                    msg += " Staženo!"
                    await send_with_special(id, f"**{location.name}:** {msg}", location.special)
                    Utilities.set_location_position(id, [])
                    if Item.pametfix.value not in Utilities.get_items(id):
                        Utilities.get_items(id).append(Item.pametsofware.value)
                    else:
                        Utilities.get_items(id).append(Item.rozsviceno.value)
                    return True

                await send_with_special(id, f"**{location.name}:** {msg} {format_remaining_time(Utilities.get_location_position(id)[-1])}", location.special)
                return False

    # stojíme u lokace
    if position is None:
        # můžeme dojít ke komponentě
        if sanitized_response == "dojít":
            Utilities.set_location_position(id, [])

            if location == procesor:
                await org_channel.send(f"Team {Utilities.get_data(id)['name']} došel k procesoru.")

            return True

        # můžeme jít do dostupných lokací
        try:
            int_response = int(sanitized_response)

            if int_response <= 0 or int_response > len(paths[location]):
                await send_with_special(id, "Neplatné číslo lokace.", location.special)
                return False

            Utilities.set_location(id, paths[location][int_response - 1])
            return True

        except ValueError:
            await send_with_special(id, "Neplatná možnost.", location.special)
            return False

    # jsme u komponenty - vždy můžeme jít zpět
    if position == []:
        if sanitized_response == "zpět":
            if location == procesor:
                await org_channel.send(f"Team {Utilities.get_data(id)['name']} odešel od procesoru.")

            Utilities.set_location_position(id, None)
            return True

    # najít správnou větev
    for condition, _, other in location.dialogue:
        if condition(items):
            break

    # dojdeme v dialogu tam, kde jsme byli
    while len(position) != 0:
        w = position.pop(0)
        for word, _, _, oth in other:
            word, oth
            if word == w:
                other = oth
                break

    for ww, _, resp, oth in other:
        if Special.loud in location.special and response != response.upper():
            await send_with_special(id, "COŽE? VŮBEC TĚ NESLYŠÍM.", location.special)
            return False

        if (sanitized_response == ww) if Special.loud not in location.special else (response == ww.upper()):
            # speciální akce na konci dialogu (přidávání itemu, minihra,...)
            if resp == [] and type(oth) != list:
                oth(id)

                # pokud jsme v minihře, necháme to takhle
                if len(Utilities.get_location_position(id)) > 0 and isinstance(Utilities.get_location_position(id)[-1], int):
                    return True

            # konec dialogu
            if resp == []:
                Utilities.set_location_position(id, [])

            # další část dialogu
            else:
                Utilities.set_location_position(id, Utilities.get_location_position(id) + [ww])
            return True
    else:
        text = "Neplatná možnost."
        if Special.loud in location.special:
            text = text.upper()

        await Utilities.get_channel(id).send(text)
        return False


async def send_with_special(id, message, special):
    if Special.loud in special:
        message = message.upper()

    if Special.darkness in special:
        # temnota jen pokud už není rozsvíceno
        if Item.rozsviceno.value not in Utilities.get_items(id):
            message = f"|| {message} ||"

    await Utilities.get_channel(id).send(message)


async def write(id, initial_paragraph=False):
    """Vypíše zprávu do kanálu teamu po aktuální interakci."""
    location = Utilities.get_location(id)
    position = Utilities.get_location_position(id)
    items = list(Utilities.get_items(id))

    if initial_paragraph:
        text = """Vítejte v adventuře!

        Jste zde v roli elektromagnetické entity, která se nějak dostala do počítače. Nevíte moc, co je to za počítač ani kde se nachází, ale vesmír chtěl, abyste se ocitli právě zde.
        Možná to má něco do činění se zlem, které uvnitř počítače cítíte – něco tu je a nemá tu co dělat. A nedávno se to probudilo po letech spánku. Snad bude víc vědět některá z komponent…


        Ovládání: <@&835801661417979914>, která vás bude provázet hrou, vám vždy vypíše informace o tom, kde se nacházíte a jaká máte v tuto chvíli možnosti. Každá možnost by u sebe měla mít `zvýrazněno`, jakým
        klíčovým slovem se dá zvolit (v případě čísel je to jen číslo bez závorek okolo). Když toto slovo kdokoliv z vašeho týmu napíše jako zprávu, tak tím vyvoláte danou volbu a <@&835801661417979914> vám
        napíše, kam jste se dostali. V případě, že <@&835801661417979914> nebude rozumět, tak si postěžuje. Občas také můžete potkat jiné speciální aktivity, ale všechny se ovládají stejným způsobem, napsáním
        zprávy v této vaší místnosti.

        Nad <@&835801661417979914> bdí ještě <@&838777490217500693> a pokud by vám v některém místě <@&835801661417979914> přestala fungovat, tak může zasáhnout. Pokud by si vašeho problému nevšimla, tak pište do kanálu <#839145972298678352>.
        """

        paragraphs = text.split("\n\n")

        message = ""
        for paragraph in paragraphs:
            message += "> " + " ".join(map(lambda x: x.strip(), paragraph.split("\n"))) + "\n> \n"
        message = message.rstrip("> \n") + "\n"

        await Utilities.get_channel(id).send(message)

    if position != None:
        position = list(position)

        # jsme-li v minihře
        if len(position) != 0 and isinstance(position[-1], int):
            # úvody miniher
            if location == vysavac:
                await send_with_special(id, f"**{location.name}**: Super, tak navigujte. Přijímám posloupnosti znaků L/U/R/D podle toho, zda mám jet doleva/nahoru/doprava/dolů.", location.special)
                return

            if location == zdroj:
                msg = f"**{location.name}**: Nemáš šanci. Začínám; říkej čísla od **1** do **9** podle toho, na jaké pozici chceš položit kolečko."
                pos = Utilities.get_location_position(id)
                pos.append(choice(TicTacToe.valid_moves([])))
                msg += "\n" + TicTacToe.show(pos)
                await send_with_special(id, msg, location.special)
                return

            if location == sitovka:
                remaining_time = randint(7000, 20000)
                Utilities.get_location_position(id)[-1] = remaining_time
                msg = f"**{location.name}**: Začínám stahovat. Pojď mezi tím hrát `kámen`/`nůžky`/`papír`! {format_remaining_time(remaining_time)}"
                await send_with_special(id, msg, location.special)
                return

            return

    # když vejdeme do lokace
    message = ""
    if position is None:
        message += f"**Nacházíte se {location.at}:**\n"

        paragraphs = location.description.split("\n\n")

        for paragraph in paragraphs:
            message += "> " + " ".join(map(lambda x: x.strip(), paragraph.split("\n"))) + "\n> \n"
        message = message.rstrip("> \n") + "\n\n"

        message += f"-> `Dojít` {location.to},\n"
        for i, path in enumerate(paths[location]):
            message += f"-> `({i + 1})` cestovat {path.to}{',' if i != len(paths[location]) - 1 else '.'}\n"
        message = message.strip("\n")
        await send_with_special(id, message, location.special)
        return

    # když se poprvé začneme bavit s komponentou
    for condition, responses, other in location.dialogue:
        if condition(items):
            if position == []:
                if len(responses) == 0:
                    message += f"**{location.name}** nereaguje:\n"
                else:
                    message += f"**{location.name}**: {choice(responses)}\n"

                for l in other:
                    message += f"-> {l[1]}\n"
                message += f"-> Jít `zpět`."
                await send_with_special(id, message, location.special)
                return
            break

    while len(position) != 0:
        w = position.pop(0)
        for word, _, response, oth in other:
            if word == w:
                other = oth
                break
        else:
            pass

    message += f"**{location.name}**: {choice(response)}\n"

    for _, sentence, _, _ in other:
        message += f"-> {sentence}\n"
    message = message.strip("\n")
    await send_with_special(id, message, location.special)

@client.event
async def on_ready():
    global data, channels, org_channel, started

    for channel in client.get_all_channels():
        # skip voice channels
        if not isinstance(channel, discord.TextChannel):
            continue

        # roomy jsou ve formátu team-*
        if channel.name.startswith("team-"):
            data[channel.id] = {
                    "name": channel.name,
                    "location": locations.index(motherboard),
                    "items": [],
                    "location_position": None}

            channels[channel.id] = channel

        if channel.name.startswith("org-bot"):
            org_channel = channel


@client.event
async def on_message(message):
    """Volá se, když se někde pošle zpráva."""
    global data, started, last_save_time

    # save každých 10s
    now = datetime.now()
    if (now - last_save_time).total_seconds() > 10 and started:
        last_save_time = now
        await org_channel.send("Automaticky ukládám stav hry.")
        await save()

    # bot neodpovídá sobě!
    if message.author == client.user:
        return

    # odpověď na DM, může být něco vtipného
    if str(message.channel).startswith("Direct Message"):
        return

    if message.channel.name == "org-bot":
        parts = message.content.lower().split()

        if len(parts) == 0:
            return

        if parts[0] == "help" or parts[0] == "?":
            await message.channel.send(
                "**Příkazy:**\n"
                "> `save` – uloží stav hry\n"
                "> `loadiknowwhatimdoing` – nahraje stav hry, přepisujíc ten aktualní\n\n"
                "> `status <jméno teamu>` – vypíše aktuální stav všech teamů / jednoho teamu\n"
                "> `startiknowwhatimdoing <backup>` – začne hru: umožní účastníkům interagovat s botem v kanálech a vypíše startovní message; pokud je specifikován backup, tak se nevypíše úvodní zpráva\n"
                "> `cleariknowwhatimdoing` – vyčistí velký počet zpráv v kanálu orgů a kanálech teamů\n\n"
                "> `add/remove <jméno teamu> <jméno itemu>` – přidá/odstraní teamu daný item\n"
                "> `move <jméno teamu> <číslo lokace>` – posune team do dané lokace; od 0 z pole [vysavac, sitovka, motherboard, pamet, zdroj, vetraky, procesor] \n"
                "> `finish <jméno teamu>` – vypíše teamu koncovou zprávu\n"
            )
            return

        if parts[0] == "save":
            await save()
            await message.channel.send(f"Manuálně ukládám stav hry.")
            return

        if parts[0] == "loadiknowwhatimdoing":
            load()
            await message.channel.send(f"Manuálně nahrávám stav hry.")
            return

        if parts[0] == "finish":
            if len(parts) == 2:
                for d in data:
                    if parts[1] == data[d]["name"]:
                        paragraphs = end_game_text.split("\n\n")

                        message = ""
                        for paragraph in paragraphs:
                            message += "> " + " ".join(map(lambda x: x.strip(), paragraph.split("\n"))) + "\n> \n"
                        message = message.rstrip("> \n") + "\n"

                        await Utilities.get_channel(d).send(message)
                        return

                await message.channel.send(f"Takový team neexistuje.")
                return

        if parts[0] == "status":
            if len(parts) == 2:
                for d in data:
                    if parts[1] == data[d]["name"]:
                        await message.channel.send(f"Data teamu {parts[1]}: \n```yaml\n{yaml.dump(data[d], indent=4)}\n```")
                        return

                await message.channel.send(f"Takový team neexistuje.")
                return

            await message.channel.send(f"Data teamů: \n```yaml\n{yaml.dump(data, indent=4)}\n```")
            return

        if parts[0] == "startiknowwhatimdoing":
            inpar = True
            if len(parts) == 2:
                if parts[1] == "backup":
                    inpar = False

            for id in data:
                await write(id, initial_paragraph=inpar)
            started = True
            return

        if parts[0] == "cleariknowwhatimdoing":
            await message.channel.purge(limit=10000)

            for id in data:
                await Utilities.get_channel(id).purge(limit=10000)

            return

        if parts[0] in ("add", "remove", "move"):
            try:
                action, id, item = parts

                for team in data:
                    if data[team]["name"] == id:
                        id = team
                        break
                else:
                    await message.channel.send('Team s takovým jménem neexistuje.')
                    return

                # pro přidávání/odebrání itemu
                if parts[0] != "move":
                    # test toho, zda item existuje
                    Item[item]
                else:
                    item = int(item)

                if action == "add":
                    Utilities.get_data(id)["items"].append(item)
                    await message.channel.send('Item úspěšně přidán.')
                    return

                if action == "remove":
                    if item not in Utilities.get_data(id)["items"]:
                        await message.channel.send('Team tento item nemá.')
                        return
                    Utilities.get_data(id)["items"].remove(item)
                    await message.channel.send('Item úspěšně odstraněn.')
                    return

                if action == "move":
                    Utilities.set_location(id, locations[item])
                    Utilities.set_location_position(id, None)

                    await message.channel.send(f'Team přesunut do: {locations[item].name}.')
                    await write(id)
                    return

            except ValueError:
                await message.channel.send('Lokace musí být číslo!')
            except KeyError:
                await message.channel.send('Item s takovým jménem neexistuje.')
            except Exception:
                await message.channel.send('Něco se nepovedlo. Je příkaz napsaný správně?')

            return

        await message.channel.send(f"Tenhle příkaz neznám.")
        return

    if not started:
        return

    # dále ignoruj kanály, které nejsou nějakého z teamů
    if message.channel.id not in data:
        return

    # změna stavu podle toho, co účastník napsal
    if await update(message.channel.id, message.content):
        # odpověď, pokud se změna povedla
        await write(message.channel.id)

print(f'Logging in.')
client.run('secret token pro bota')
