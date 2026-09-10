# Rendering and Tests

Reuse the framework-owned environment when there is one. For a standalone package with `templates/` inside its import package, adapt this setup; `uv` manages the project's Jinja and pytest dependencies.

```python
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

env = Environment(
    loader=PackageLoader("example_app", "templates"),
    autoescape=select_autoescape(
        enabled_extensions=("html", "htm", "xml", "html.jinja"),
        default_for_string=True,
        default=False,
    ),
    undefined=StrictUndefined,
)
```

The example treats unknown extensions as text; adjust the list to the actual template names. Use a separate, explicitly non-escaping environment for plain text. Choose `trim_blocks`, `lstrip_blocks`, and `keep_trailing_newline` only when required by the output contract.

This small fixture tests the rendering boundary without a web server:

```python
import pytest
from jinja2 import DictLoader, Environment, StrictUndefined, UndefinedError


def test_rendering_contract():
    env = Environment(
        loader=DictLoader({
            "base.html": "<main>{% block content %}{% endblock %}</main>",
            "greeting.html": '{% extends "base.html" %}'
            "{% block content %}{{ name }}{% endblock %}",
        }),
        autoescape=True,
        undefined=StrictUndefined,
    )
    template = env.get_template("greeting.html")
    assert template.render(name="<script>&") == "<main>&lt;script&gt;&amp;</main>"
    with pytest.raises(UndefinedError):
        template.render()
```

Also test application templates with representative view data; a `DictLoader` fixture alone does not prove package contents. Build the wheel through the project's task, inspect its template entries, install it in a fresh environment, and render an actual template from a directory outside the source tree. Keep packaged templates available without relying on the current working directory.

Treat `safe` and `Markup` as trust assertions. Sanitization, if required, happens at a separately tested boundary; HTML escaping alone neither sanitizes trusted-marked markup nor prevents server-side template evaluation.

Sources: [Jinja API](https://jinja.palletsprojects.com/en/stable/api/) and [template escaping](https://jinja.palletsprojects.com/en/stable/templates/#html-escaping).
