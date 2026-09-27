# Minimal reader for flat "key: value" YAML (secrets.yaml). Same file as firmware/lib/flatyaml.py.
# Supports comments, blank lines, and "double" / 'single' quoted or bare values.
# No nesting, lists or multi-line strings. Also runs on CPython.


def parse(text):
    out = {}
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, rest = line.partition(":")
        if not sep or not key.strip():
            raise ValueError("secrets line %d: expected 'key: value'" % n)
        rest = rest.strip()
        if rest[:1] in ('"', "'"):
            q = rest[0]
            end = rest.find(q, 1)
            if end < 0:
                raise ValueError("secrets line %d: unclosed quote" % n)
            val = rest[1:end]
        else:
            val = rest.split(" #", 1)[0].strip()
        out[key.strip()] = val
    return out


def load(path):
    with open(path, encoding="utf-8") as f:
        return parse(f.read())
