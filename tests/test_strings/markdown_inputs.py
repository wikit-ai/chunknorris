"""This file contains markdown strings intended to be used 
to test the MarkdownChunkNorris chunker
"""

MD_STANDARD = """
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

MD_WITH_INTROS = """
This is some text before header 1. Sometimes it may be present
and should not be discared.

# This is header 1

This is an introduction of section 1, used to introduce the content 
of section 1. For example, section 2 contains section 2.

## This is header 2

This is an introduction of section 2, used to introduce the content 
of section 2. For example, section 2 contains section 3.

### This is header 3

Ingratasque sentire quanto, cognovit, nec est inmenso **pavet fratrum**, nescit.
Ossa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.
Partem sic prosunt avenis postquam modo, montis; **levi numero**; non sed et
superbos.
"""

MD_SKIPPED_HEADER_LEVELS = """
# This is header 1

### This is header 3.1

Ingratasque sentire quanto, cognovit, nec est inmenso **pavet fratrum**, nescit.
Ossa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.

### This is header 3.2

##### This is header 5

Ingratasque sentire quanto, cognovit, nec est inmenso **pavet fratrum**, nescit.
Ossa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.
Partem sic prosunt avenis postquam modo, montis; **levi numero**; non sed et
superbos.
"""

MD_WITH_LINKS = """
This is a section which contains links

This section has a [link](https://this-is-a-link.com/page)

This section has an ![image](http://this/is/an/image.jpg 'Image title')

This is an [![image_link](this/is/an/image.jpg 'This is image title')](https://image_link.com)
"""

MD_STANDARD_SETEXT = """
This is header 1
================

This is header 2.1
------------------

Lorem markdownum Meleagros tumulo parentur virgo propter silentibus nascentia
**hostibus** sanguine quem nec, ter ora origo, parte? Sensimus repercusso
Sicelidas animam dignum, aura, suae undamque **vulnere**.

This is header 2.2
------------------

### This is header 3.1

Rex solvo sinu patuit in, Facit et Anaphen exosae eversae tenuit:
**ales** tuis, igne. **Ab luna** sponte movit eratque. Dextera iuvencae via mihi
*patrioque*.

### This is header 3.2

Rex solvo sinu patuit in, Facit et Anaphen exosae eversae tenuit:
**ales** tuis, igne. **Ab luna** sponte movit eratque. Dextera iuvencae via mihi
*patrioque*.
"""