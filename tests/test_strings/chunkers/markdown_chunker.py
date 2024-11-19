"""This file contains markdown strings intended to be used 
to test the MarkdownChunkNorris chunker
"""

from chunknorris.chunkers.tools import Chunk
from chunknorris.parsers.markdown.components import MarkdownLine

MD_STANDARD_IN = """
# This is header 1

## This is header 2.1

Lorem markdownum Meleagros tumulo parentur virgo propter silentibus nascentia
**hostibus** sanguine quem nec, ter ora origo, parte? Sensimus repercusso
Sicelidas animam dignum, aura, suae undamque **vulnere**.

## This is header 2.2

### This is header 3.1

Rex solvo sinu patuit in, Facit et Anaphen exosae eversae tenuit:
**ales** tuis, igne. **Ab luna** sponte movit eratque. Dextera iuvencae via mihi
*patrioque*.

### This is header 3.2

Rex solvo sinu patuit in, Facit et Anaphen exosae eversae tenuit:
**ales** tuis, igne. **Ab luna** sponte movit eratque. Dextera iuvencae via mihi
*patrioque*.
"""

MD_STANDARD_OUT = [
    "# This is header 1\n\n## This is header 2.1\n\nLorem markdownum Meleagros tumulo parentur virgo propter silentibus nascentia\n**hostibus** sanguine quem nec, ter ora origo, parte? Sensimus repercusso\nSicelidas animam dignum, aura, suae undamque **vulnere**.",
    "# This is header 1\n\n## This is header 2.2\n\n### This is header 3.1\n\nRex solvo sinu patuit in, Facit et Anaphen exosae eversae tenuit:\n**ales** tuis, igne. **Ab luna** sponte movit eratque. Dextera iuvencae via mihi\n*patrioque*.",
    "# This is header 1\n\n## This is header 2.2\n\n### This is header 3.2\n\nRex solvo sinu patuit in, Facit et Anaphen exosae eversae tenuit:\n**ales** tuis, igne. **Ab luna** sponte movit eratque. Dextera iuvencae via mihi\n*patrioque*.",
]

MD_WITH_INTROS_IN = """
This is some text before header 1.
Sometimes it may be present and should not be discared.

# This is header 1

This is an introduction of section 1, used to introduce the content of section 1.
For example, section 2 contains section 2.

## This is header 2

This is an introduction of section 2, used to introduce the content of section 2.
For example, section 2 contains section 3.

### This is header 3

Ingratasque sentire quanto, cognovit, nec est inmenso **pavet fratrum**, nescit.
Ossa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.
Partem sic prosunt avenis postquam modo, montis; **levi numero**; non sed et superbos.
"""

MD_WITH_INTROS_OUT = [
    "This is some text before header 1.\nSometimes it may be present and should not be discared.",
    "# This is header 1\n\nThis is an introduction of section 1, used to introduce the content of section 1.\nFor example, section 2 contains section 2.",
    "# This is header 1\n\n## This is header 2\n\nThis is an introduction of section 2, used to introduce the content of section 2.\nFor example, section 2 contains section 3.",
    "# This is header 1\n\n## This is header 2\n\n### This is header 3\n\nIngratasque sentire quanto, cognovit, nec est inmenso **pavet fratrum**, nescit.\nOssa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.\nPartem sic prosunt avenis postquam modo, montis; **levi numero**; non sed et superbos.",
]

MD_SKIPPED_HEADER_LEVELS_IN = """
# This is header 1

### This is header 3.1

Ingratasque sentire quanto, cognovit, nec est inmenso **pavet fratrum**, nescit.
Ossa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.

### This is header 3.2

##### This is header 5

Ingratasque sentire quanto, cognovit, nec est inmenso **pavet fratrum**, nescit.
Ossa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.
"""

MD_SKIPPED_HEADER_LEVELS_OUT = [
    "# This is header 1\n\n### This is header 3.1\n\nIngratasque sentire quanto, cognovit, nec est inmenso **pavet fratrum**, nescit.\nOssa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.",
    "# This is header 1\n\n### This is header 3.2\n\n##### This is header 5\n\nIngratasque sentire quanto, cognovit, nec est inmenso **pavet fratrum**, nescit.\nOssa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.",
]

MD_BIG_CHUNK_IN = Chunk(
    headers=[MarkdownLine(text="# This is header 1", line_idx=0)],
    content=[
        MarkdownLine(text="## This is header 2.1", line_idx=1),
        MarkdownLine(text="\n", line_idx=2),
        MarkdownLine(
            text="word word word word word word word word word word", line_idx=3
        ),
        MarkdownLine(
            text="word word word word word word word word word word", line_idx=4
        ),
        MarkdownLine(
            text="word word word word word word word word word word", line_idx=5
        ),
        MarkdownLine(text="## This is header 2.2", line_idx=6),
        MarkdownLine(text="\n", line_idx=7),
        MarkdownLine(
            text="word word word word word word word word word word", line_idx=8
        ),
        MarkdownLine(
            text="word word word word word word word word word word", line_idx=9
        ),
        MarkdownLine(
            text="word word word word word word word word word word", line_idx=10
        ),
    ],
    start_line=0,
)

MD_BIG_CHUNK_OUT = [
    "# This is header 1\n\n## This is header 2.1\n\nword word word word word word word word word word",
    "# This is header 1\n\n## This is header 2.1\n\nword word word word word word word word word word",
    "# This is header 1\n\n## This is header 2.1\n\nword word word word word word word word word word",
    "# This is header 1\n\n## This is header 2.2\n\n## This is header 2.2\n\nword word word word word word word word word word",
    "# This is header 1\n\n## This is header 2.2\n\nword word word word word word word word word word",
    "# This is header 1\n\n## This is header 2.2\n\nword word word word word word word word word word",
]
