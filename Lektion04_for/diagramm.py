"""Hilfsmodul für Lektion 4: macht aus einer for-Schleife ein Balkendiagramm.

Verwendung im Notebook:

    import diagramm          (einmal ausführen)

    %%diagramm               (erste Zeile einer Zelle, darunter das eigene Programm)

Das Programm läuft wie gewohnt. Zusätzlich wird jeder Schleifendurchlauf zu
einem Balken: waagrecht die Laufvariable, senkrecht die Variable, die in der
Schleife berechnet wird. Enthält die Schleife eine Auswahl, zeigt die Farbe,
ob die Bedingung im jeweiligen Durchlauf erfüllt war.

Hinter %%diagramm kann der Name der Variablen stehen, die gezeigt werden soll,
zum Beispiel:  %%diagramm bremsweg
"""
import ast

_FARBE_JA = "tab:blue"
_FARBE_NEIN = "tab:orange"


def _ist_zahl(wert):
    return isinstance(wert, (int, float)) and not isinstance(wert, bool)


def _erste_for_schleife(baum):
    schleifen = [k for k in ast.walk(baum) if isinstance(k, ast.For)]
    if not schleifen:
        return None
    return min(schleifen, key=lambda k: (k.lineno, k.col_offset))


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

    info = {"laufvariable": laufvariable, "kandidaten": [], "bedingung": None}
    neu = [_aufruf("__dg_start", ast.Name(id=laufvariable, ctx=ast.Load()))]
    for anweisung in schleife.body:
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


def _zeichnen(info, durchlaeufe, wunsch, namensraum):
    import matplotlib.pyplot as plt

    def zahlenreihe(name):
        return [d for d in durchlaeufe if _ist_zahl(d["werte"].get(name)) and _ist_zahl(d["x"])]

    if wunsch:
        if not zahlenreihe(wunsch):
            print(f"Diagramm: Die Variable {wunsch} wird in der Schleife nicht als Zahl berechnet.")
            return
        y_name = wunsch
    else:
        reihenfolge = list(reversed(info["kandidaten"]))
        if "anhalteweg" in reihenfolge:
            reihenfolge.remove("anhalteweg")
            reihenfolge.insert(0, "anhalteweg")
        y_name = next((n for n in reihenfolge if zahlenreihe(n)), None)
        if y_name is None:
            print("Diagramm: Speichern Sie den berechneten Wert in der Schleife in einer Variablen, "
                  "zum Beispiel  anhalteweg = ...  Dann kann ich ihn zeichnen.")
            return

    punkte = zahlenreihe(y_name)
    xs = [d["x"] for d in punkte]
    abstaende = [b - a for a, b in zip(sorted(set(xs)), sorted(set(xs))[1:])]
    breite = 0.8 * min(abstaende) if abstaende else 0.8

    plt.figure(figsize=(7, 4.2))
    mit_bedingung = info["bedingung"] is not None and any(d["flag"] is not None for d in punkte)
    if mit_bedingung:
        ja = [d for d in punkte if d["flag"]]
        nein = [d for d in punkte if not d["flag"]]
        if ja:
            plt.bar([d["x"] for d in ja], [d["werte"][y_name] for d in ja], width=breite,
                    color=_FARBE_JA, label=f"{info['bedingung_text']}: erfüllt")
        if nein:
            plt.bar([d["x"] for d in nein], [d["werte"][y_name] for d in nein], width=breite,
                    color=_FARBE_NEIN, label=f"{info['bedingung_text']}: nicht erfüllt")
        grenze = _grenze(info, y_name, namensraum)
        if grenze:
            plt.axhline(grenze[1], color="black", linestyle="--", label=grenze[0])
        plt.legend()
    else:
        plt.bar(xs, [d["werte"][y_name] for d in punkte], width=breite, color=_FARBE_JA)

    anzahl = len(durchlaeufe)
    plt.title(f"Ein Balken pro Schleifendurchlauf ({anzahl} Durchläufe)")
    plt.xlabel(f"Laufvariable {info['laufvariable']}")
    plt.ylabel(y_name)
    plt.show()


def diagramm(zeile, zelle):
    """Zellmagie %%diagramm: führt die Zelle aus und zeichnet die for-Schleife."""
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
    durchlaeufe = []

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


def load_ipython_extension(shell):
    shell.register_magic_function(diagramm, magic_kind="cell", magic_name="diagramm")


try:
    from IPython import get_ipython as _get_ipython
    if _get_ipython() is not None:
        load_ipython_extension(_get_ipython())
except ImportError:
    pass
