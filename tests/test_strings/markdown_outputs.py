"""This file contains markdown chunks intended to be used 
to test the MarkdownChunkNorris chunker
"""

MD_STANDARD_CHUNKS = [
    "# This is header 1\n## This is header 2.1\nLorem markdownum Meleagros tumulo parentur virgo propter silentibus nascentia\nhostibus sanguine quem nec, ter ora origo, parte? Sensimus repercusso\nSicelidas animam dignum, aura, suae undamque vulnere.",
    "# This is header 1\n## This is header 2.2\n### This is header 3.1\nRex solvo sinu patuit in, Facit et Anaphen exosae eversae tenuit:\nales tuis, igne. Ab luna sponte movit eratque. Dextera iuvencae via mihi\n*patrioque*.",
    "# This is header 1\n## This is header 2.2\n### This is header 3.2\nRex solvo sinu patuit in, Facit et Anaphen exosae eversae tenuit:\nales tuis, igne. Ab luna sponte movit eratque. Dextera iuvencae via mihi\n*patrioque*."
    ]

MD_WITH_INTROS_CHUNKS = [
    '\nThis is some text before header 1. Sometimes it may be present\nand should not be discared.',
    '# This is header 1\nThis is an introduction of section 1, used to introduce the content \nof section 1. For example, section 2 contains section 2.',
    '# This is header 1\n## This is header 2\nThis is an introduction of section 2, used to introduce the content \nof section 2. For example, section 2 contains section 3.',
    '# This is header 1\n## This is header 2\n### This is header 3\nIngratasque sentire quanto, cognovit, nec est inmenso pavet fratrum, nescit.\nOssa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.\nPartem sic prosunt avenis postquam modo, montis; levi numero; non sed et\nsuperbos.'
    ]

MD_SKIPPED_HEADER_LEVELS_CHUNKS = [
    "# This is header 1\n### This is header 3.1\nIngratasque sentire quanto, cognovit, nec est inmenso pavet fratrum, nescit.\nOssa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.",
    "# This is header 1\n### This is header 3.2\n##### This is header 5\nIngratasque sentire quanto, cognovit, nec est inmenso pavet fratrum, nescit.\nOssa lympha, turres, in mundi lymphae te Ismariae aetas praeferre gravitas.\nPartem sic prosunt avenis postquam modo, montis; levi numero; non sed et\nsuperbos."
    ]

MD_WITH_LINKS_OUTPUTS = {
    "in_sentence": '\nThis is a section which contains links\n\nThis section has a link (lien : https://this-is-a-link.com/page)\n\nThis section has an image (lien : http://this/is/an/image.jpg)\n\nThis is an image_link (lien : https://image_link.com)\n',
    "end_of_chunk": "\nThis is a section which contains links\n\nThis section has a link\n\nThis section has an image\n\nThis is an image_link\n\nPour plus d'informations:\n- image_link: https://image_link.com\nPour plus d'informations:\n- image: http://this/is/an/image.jpg\nPour plus d'informations:\n- link: https://this-is-a-link.com/page",
    "remove": '\nThis is a section which contains links\n\nThis section has a link\n\nThis section has an image\n\nThis is an image_link\n',
    "leave_as_markdown": "\nThis is a section which contains links\n\nThis section has a [link](https://this-is-a-link.com/page)\n\nThis section has an ![image](http://this/is/an/image.jpg 'Image title')\n\nThis is an [![image_link](this/is/an/image.jpg 'This is image title')](https://image_link.com)\n"
    }