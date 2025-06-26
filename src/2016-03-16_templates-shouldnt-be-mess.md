---
title: Templates shouldn't be a mess
summary: On formatting of HTML templates
---

I was working on another Django project when I decided to write down my thoughts on readable template code formatting.

I believe that templates are more readable when they're written with the idea that a clean, correctly indented hypertext should be produced.
Django documentation states that there are template variables and template tags in the template language. In my formatting explanation, I call both 'tags' and divide them into text-producing and non-text-producing ones.
Django documentation samples and lots of coders mix up indentation of hypertext and template tags. I use independent parallel indentation for non-text-producing template tags which are placed on separate lines out of hypertext, and I separate such tags from surrounding hypertext with empty lines.

In detail:

- hypertext is written with common, global indentation hierarchy
- text-producing template tags (variable substitutions, includes, etc.) are placed like the hypertext which they produce:
    - tags which produce inline hypertext fragments are placed inside the hypertext lines
    - tags which produce (multi)line hypertext fragments are placed on separate lines, indented like the hypertext which they produce, following the global hypertext indentation
- non-text-producing, or logic-controlling template tags, which generate no text themselves, but define the logic of template processing (conditional operators, loops, variable assignments, etc.), are another thing:
    - tags which control inline hypertext fragments (e. g. conditional block which controls a hypertext tag attribute) are placed within these lines
    - tags which control (multi)line hypertext fragments or no hypertext at all are placed on separate lines, following their own global indentation hierarchy, independent from the one of the hypertext; such template tag lines are separated by empty lines from the hypertext and hypertext-producing template tags around them

Example:

```
<html>
  <head>
  </head>
  <body>
    {% include 'header.htm' %}

{% if list %}

    <ul>

  {% for item in list %}

      <li>{{ item }}</li>

  {% endfor %}

    </ul>

{% endif %}

  </body>
</html>
```
