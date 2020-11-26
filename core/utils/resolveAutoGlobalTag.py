"""
Script that resolves auto:... to global tag values
"""
import sys
from Configuration.AlCa.autoCond import autoCond as auto_globaltag


def resolve_globaltag(tag):
    """
    Translate auto:... to an actual globaltag
    If globaltag value is a list, it returns the first element
    """
    if not tag.startswith('auto:'):
        return tag

    tag = tag.replace('auto:', '', 1)
    resolved_tag = auto_globaltag[tag]
    if isinstance(resolved_tag, (list, tuple)):
        resolved_tag = resolved_tag[0]

    return resolved_tag


def main():
    """
    Main
    """
    if len(sys.argv) < 3:
        print('Missing auto GlobalTag label argument')
        print('usage: %s <label> <auto:globaltag>[,<auto:globaltag2>]' % (sys.argv[0]))
        sys.exit(1)

    label = sys.argv[1].strip()
    tags = [t.strip() for t in sys.argv[2].split(',') if t.strip()]
    for tag in tags:
        print('GlobalTag: %s %s %s' % (label, tag, resolve_globaltag(tag)))


if __name__ == '__main__':
    main()
