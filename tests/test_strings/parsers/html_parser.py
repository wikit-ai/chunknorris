HTML_STRING_IN = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<h1>This is a h1 header</h1>
</head>
<body>
<div class="mw-heading mw-heading3"><h3 id="Occupation_des_sols">This is a h3 header</h3></div>
<p>This is some text with <a href="www.link.com">markdown links</a> within it.</p>
<figure class="mw-default-size mw-halign-center" typeof="mw:File/Thumb"><a href="/wiki/Fichier:79348-Villefollet-Sols.png" class="mw-file-description"><img alt="Carte en couleurs présentant l&#39;occupation des sols." src="//upload.wikimedia.org/wikipedia/commons/thumb/e/e9/79348-Villefollet-Sols.png/310px-79348-Villefollet-Sols.png" decoding="async" width="310" height="246" class="mw-file-element" srcset="//upload.wikimedia.org/wikipedia/commons/thumb/e/e9/79348-Villefollet-Sols.png/465px-79348-Villefollet-Sols.png 1.5x, //upload.wikimedia.org/wikipedia/commons/thumb/e/e9/79348-Villefollet-Sols.png/620px-79348-Villefollet-Sols.png 2x" data-file-width="3270" data-file-height="2598" /></a><figcaption>Carte des infrastructures et de l'occupation des sols de la commune en 2018.</figcaption></figure>
<tbody><tr>
<th scope="col">Header 1
</th>
<th scope="col">Header 2
</th>
<th scope="col">Header 3
</th></tr>
</body>
</html>
"""

HTML_STRING_OUT = """# This is a h1 header

### This is a h3 header

This is some text with [markdown links](www.link.com) within it.

Carte des infrastructures et de l'occupation des sols de la commune en 2018.

| Header 1 | Header 2 | Header 3 |
| --- | --- | --- |"""