"""Hilfsmodul für Lektion 4: macht aus einer for-Schleife ein Balkendiagramm.

Verwendung im Notebook:

    import diagramm          (einmal ausführen)

    %%diagramm               (über das eigene Programm setzen; Kommentare
                             und Leerzeilen darüber sind erlaubt)

Das Programm läuft wie gewohnt. Zusätzlich wird jeder Schleifendurchlauf zu
einem Balken: waagrecht die Laufvariable, senkrecht die Variable, die in der
Schleife berechnet und mit print ausgegeben wird. Enthält die Schleife eine
Auswahl, zeigt die Farbe, ob die Bedingung im jeweiligen Durchlauf erfüllt war.

Hinter %%diagramm kann der Name der Variablen stehen, die gezeigt werden soll,
zum Beispiel:  %%diagramm bremsweg


Für Neugierige
--------------
Schön, dass Sie hineinschauen. Die Diagramme zeichnet das Paket matplotlib.
Ein Balkendiagramm können Sie damit schon selbst schreiben, mit einer
for-Schleife. Probieren Sie es in einer leeren Zelle aus:

    import matplotlib.pyplot as plt

    for x in range(1, 6):
        plt.bar(x, x * x)        # ein Balken an der Stelle x mit der Höhe x * x
    plt.xlabel("x")
    plt.ylabel("x * x")
    plt.show()                   # erst jetzt erscheint das Bild

Diese Datei hat drei Teile:

    Teil 1  untersucht Ihr Programm und merkt sich die Werte jedes Durchlaufs.
            Dieser Teil ist fortgeschritten, Sie müssen ihn nicht verstehen.
    Teil 2  zeichnet das Diagramm mit matplotlib. Hier lohnt sich das Lesen.
    Teil 3  führt Ihre Zelle aus und meldet %%diagramm im Notebook an.

Die Datei verwendet Sprachmittel, die Sie erst später kennenlernen:
Funktionen (def), Listen ([...]) und Wörterbücher ({...}).
"""
import ast

_FARBE_JA = "tab:blue"        # Bedingung erfüllt
_FARBE_NEIN = "tab:orange"    # Bedingung nicht erfüllt


# ---------------------------------------------------------------------------
# Teil 1: Ihr Programm untersuchen (fortgeschritten)
#
# Python kann ein Programm nicht nur ausführen, sondern auch lesen: Das Modul
# ast zerlegt den Programmtext in einen Baum aus Anweisungen. Dieser Teil sucht
# darin die erste for-Schleife und fügt in den Schleifenkörper unsichtbare
# Zusatzzeilen ein. Sie notieren in jedem Durchlauf die Werte der Variablen.
# Ihr Programm in der Zelle bleibt dabei unverändert.
# ---------------------------------------------------------------------------


def _ist_zahl(wert):
    return isinstance(wert, (int, float)) and not isinstance(wert, bool)


def _erste_for_schleife(baum):
    schleifen = [k for k in ast.walk(baum) if isinstance(k, ast.For)]
    if not schleifen:
        return None
    return min(schleifen, key=lambda k: (k.lineno, k.col_offset))


def _ausgegebene_namen(schleife):
    """Sammelt die Namen aller Variablen, die in der Schleife in einem print stehen."""
    namen = set()
    for knoten in ast.walk(schleife):
        if (isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Name)
                and knoten.func.id == "print"):
            for teil in ast.walk(knoten):
                if isinstance(teil, ast.Name):
                    namen.add(teil.id)
    return namen


def _aufruf(name, *argumente):
    return ast.Expr(ast.Call(func=ast.Name(id=name, ctx=ast.Load()),
                             args=list(argumente), keywords=[]))


def _instrumentieren(baum):
    """Baut die Aufzeichnung in die erste for-Schleife ein."""
    schleife = _erste_for_schleife(baum)
    if schleife is None:
        return None, "Ich finde in dieser Zelle keine for-Schleife. Kopieren Sie Ihr Programm unter die Zeile %%diagramm."
    if not isinstance(schleife.target, ast.Name):
        return None, "Die Laufvariable der for-Schleife muss ein einzelner Name sein."
    laufvariable = schleife.target.id

    info = {"laufvariable": laufvariable, "kandidaten": [], "bedingung": None,
            "ausgegeben": _ausgegebene_namen(schleife)}
    # neuer Schleifenkörper: zuerst "ein Durchlauf beginnt" notieren ...
    neu = [_aufruf("__dg_start", ast.Name(id=laufvariable, ctx=ast.Load()))]
    for anweisung in schleife.body:
        # ... bei der ersten Auswahl notieren, ob die Bedingung erfüllt war ...
        if isinstance(anweisung, ast.If) and info["bedingung"] is None:
            info["bedingung"] = anweisung.test
            info["bedingung_text"] = ast.unparse(anweisung.test)
            anweisung.test = ast.Call(func=ast.Name(id="__dg_flag", ctx=ast.Load()),
                                      args=[anweisung.test], keywords=[])
        neu.append(anweisung)
        namen = []
        if isinstance(anweisung, ast.Assign):
            namen = [z.id for z in anweisung.targets if isinstance(z, ast.Name)]
        elif isinstance(anweisung, ast.AugAssign) and isinstance(anweisung.target, ast.Name):
            namen = [anweisung.target.id]
        # ... und nach jeder Zuweisung den neuen Wert der Variablen notieren
        for name in namen:
            if name == laufvariable:
                continue
            if name in info["kandidaten"]:
                info["kandidaten"].remove(name)
            info["kandidaten"].append(name)
            neu.append(_aufruf("__dg_set", ast.Constant(value=name),
                               ast.Name(id=name, ctx=ast.Load())))
    schleife.body = neu
    ast.fix_missing_locations(baum)
    return info, None


def _grenze(info, y_name, namensraum):
    """Sucht in der Bedingung einen Vergleich der gezeigten Variablen mit einem festen Wert."""
    test = info["bedingung"]
    if not (isinstance(test, ast.Compare) and len(test.comparators) == 1):
        return None
    for seite, andere in ((test.left, test.comparators[0]), (test.comparators[0], test.left)):
        if isinstance(seite, ast.Name) and seite.id == y_name:
            if isinstance(andere, ast.Constant) and _ist_zahl(andere.value):
                return f"Grenzwert {andere.value:g}", andere.value
            if isinstance(andere, ast.Name) and _ist_zahl(namensraum.get(andere.id)):
                wert = namensraum[andere.id]
                return f"{andere.id} = {wert:g}", wert
    return None


# ---------------------------------------------------------------------------
# Teil 2: Zeichnen mit matplotlib
#
# durchlaeufe enthält für jeden Schleifendurchlauf den Wert der Laufvariablen
# und die Werte der berechneten Variablen. Daraus entsteht das Diagramm.
# ---------------------------------------------------------------------------
def _zeichnen(info, durchlaeufe, wunsch, namensraum):
    import matplotlib.pyplot as plt     # plt ist nur ein kurzer Name für das Paket

    def zahlenreihe(name):
        return [d for d in durchlaeufe if _ist_zahl(d["werte"].get(name)) and _ist_zahl(d["x"])]

    # Welche Variable wird gezeigt? Die gewünschte, sonst "anhalteweg",
    # sonst die zuletzt berechnete Variable, die auch ausgegeben wird,
    # sonst die Variable, die in der Schleife zuletzt berechnet wird.
    if wunsch:
        if not zahlenreihe(wunsch):
            print(f"Diagramm: Die Variable {wunsch} wird in der Schleife nicht als Zahl berechnet.")
            return
        y_name = wunsch
    else:
        reihenfolge = list(reversed(info["kandidaten"]))
        ausgegeben = info.get("ausgegeben", set())
        reihenfolge = ([n for n in reihenfolge if n in ausgegeben]
                       + [n for n in reihenfolge if n not in ausgegeben])
        if "anhalteweg" in reihenfolge:
            reihenfolge.remove("anhalteweg")
            reihenfolge.insert(0, "anhalteweg")
        y_name = next((n for n in reihenfolge if zahlenreihe(n)), None)
        if y_name is None:
            print("Diagramm: Speichern Sie den berechneten Wert in der Schleife in einer Variablen, "
                  "zum Beispiel  anhalteweg = ...  Dann kann ich ihn zeichnen.")
            return

    # Balkenbreite: 80 % des Abstands zwischen zwei Werten der Laufvariablen,
    # damit zwischen den Balken eine Lücke bleibt
    punkte = zahlenreihe(y_name)
    xs = [d["x"] for d in punkte]
    abstaende = [b - a for a, b in zip(sorted(set(xs)), sorted(set(xs))[1:])]
    breite = 0.8 * min(abstaende) if abstaende else 0.8

    plt.figure(figsize=(7, 4.2))        # neues, leeres Bild; Breite und Höhe in Zoll
    mit_bedingung = info["bedingung"] is not None and any(d["flag"] is not None for d in punkte)
    if mit_bedingung:
        ja = [d for d in punkte if d["flag"]]
        nein = [d for d in punkte if not d["flag"]]
        # plt.bar(Stellen, Höhen) zeichnet Balken. Hier bekommt es alle Balken
        # einer Farbe auf einmal als Liste. label ist der Text für die Legende.
        if ja:
            plt.bar([d["x"] for d in ja], [d["werte"][y_name] for d in ja], width=breite,
                    color=_FARBE_JA, label=f"{info['bedingung_text']}: erfüllt")
        if nein:
            plt.bar([d["x"] for d in nein], [d["werte"][y_name] for d in nein], width=breite,
                    color=_FARBE_NEIN, label=f"{info['bedingung_text']}: nicht erfüllt")
        grenze = _grenze(info, y_name, namensraum)
        if grenze:
            # waagrechte gestrichelte Linie auf der Höhe des Grenzwerts
            plt.axhline(grenze[1], color="black", linestyle="--", label=grenze[0])
        plt.legend()                    # zeigt die label-Texte in einem Kasten
    else:
        plt.bar(xs, [d["werte"][y_name] for d in punkte], width=breite, color=_FARBE_JA)

    # Titel und Achsenbeschriftung
    anzahl = len(durchlaeufe)
    plt.title(f"Ein Balken pro Schleifendurchlauf ({anzahl} Durchläufe)")
    plt.xlabel(f"Laufvariable {info['laufvariable']}")
    plt.ylabel(y_name)
    plt.show()                          # erst jetzt erscheint das Bild


# ---------------------------------------------------------------------------
# Teil 3: Die Zelle ausführen und %%diagramm anmelden
# ---------------------------------------------------------------------------
def diagramm(zeile, zelle):
    """Zellmagie %%diagramm: führt die Zelle aus und zeichnet die for-Schleife."""
    # zelle ist der Text Ihrer Zelle, zeile der Text hinter %%diagramm
    from IPython import get_ipython
    shell = get_ipython()
    quelltext = shell.transform_cell(zelle) if shell else zelle
    try:
        baum = ast.parse(quelltext)
    except SyntaxError:
        if shell:
            shell.showsyntaxerror()
            return
        raise
    info, meldung = _instrumentieren(baum)
    namensraum = shell.user_ns if shell else {}
    if info is None:
        exec(compile(ast.parse(quelltext), "<Ihr Programm>", "exec"), namensraum)
        print(f"Diagramm: {meldung}")
        return

    import linecache
    zeilen = quelltext.splitlines(keepends=True)
    linecache.cache["<Ihr Programm>"] = (len(quelltext), None, zeilen, "<Ihr Programm>")
    durchlaeufe = []                    # hier sammeln sich die Notizen aus Teil 1

    def start(x):
        durchlaeufe.append({"x": x, "werte": {}, "flag": None})

    def setzen(name, wert):
        if durchlaeufe:
            durchlaeufe[-1]["werte"][name] = wert

    def flag(wert):
        if durchlaeufe and durchlaeufe[-1]["flag"] is None:
            durchlaeufe[-1]["flag"] = bool(wert)
        return wert

    namensraum.update({"__dg_start": start, "__dg_set": setzen, "__dg_flag": flag})
    try:
        # Ihr Programm (mit den Zusatzzeilen) ausführen
        exec(compile(baum, "<Ihr Programm>", "exec"), namensraum)
    except Exception:
        if shell:
            import sys
            typ, fehler, spur = sys.exc_info()
            shell.showtraceback((typ, fehler, spur.tb_next))
            return
        raise
    finally:
        for name in ("__dg_start", "__dg_set", "__dg_flag"):
            namensraum.pop(name, None)

    if not durchlaeufe:
        print("Diagramm: Die Schleife wurde kein einziges Mal durchlaufen.")
        return
    _zeichnen(info, durchlaeufe, zeile.strip(), namensraum)


def _magie_nach_oben(zeilen):
    """Schiebt die Zeile %%diagramm an den Anfang der Zelle.

    Jupyter erkennt %%diagramm nur in der allerersten Zeile. Steht darüber ein
    Kommentar oder eine Leerzeile, käme sonst die Meldung "not found".
    """
    try:
        for nummer, zeile in enumerate(zeilen):
            wort = zeile.strip().split(" ")[0]
            if wort == "%%diagramm":
                if nummer == 0 and zeile.startswith("%%diagramm"):
                    return zeilen
                kopf = zeile.strip() + "\n"
                return [kopf] + zeilen[:nummer] + zeilen[nummer + 1:]
    except Exception:
        pass
    return zeilen


def load_ipython_extension(shell):
    # macht dem Notebook bekannt, dass %%diagramm die Funktion diagramm aufruft
    shell.register_magic_function(diagramm, magic_kind="cell", magic_name="diagramm")
    # vor jeder Ausführung prüfen, ob %%diagramm nach oben geschoben werden muss
    try:
        filter_ = shell.input_transformers_cleanup
        filter_[:] = [f for f in filter_ if getattr(f, "__name__", "") != "_magie_nach_oben"]
        filter_.append(_magie_nach_oben)
    except Exception:
        pass                            # ältere Jupyter-Version: %%diagramm muss dann ganz oben stehen


# Diese Zeilen laufen bei "import diagramm" und melden %%diagramm an.
try:
    from IPython import get_ipython as _get_ipython
    if _get_ipython() is not None:
        load_ipython_extension(_get_ipython())
except ImportError:
    pass
