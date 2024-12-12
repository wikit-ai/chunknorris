MD_STANDARD_SETEXT_IN = """
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

MD_STANDARD_SETEXT_OUT = """
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

MD_WITH_CODE_BLOCK = """
```This is not a code block```
This is a text

```py
This is a code block
```

This is a text
"""

MD_WITH_METADATA = """---
metadatakey: metadatavalue
---
markdown content
"""
