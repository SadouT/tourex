"""Flutter code generator - converts widget tree JSON to valid Flutter/Dart code."""

import json

INDENT = "  "


def _indent(level):
    return INDENT * level


def generate_widget(node, level=3):
    """Recursively generate Dart code for a widget node."""
    wtype = node.get("type", "Container")
    props = node.get("properties", {})
    children = node.get("children", [])

    generators = {
        "Scaffold": _gen_scaffold,
        "AppBar": _gen_appbar,
        "Container": _gen_container,
        "Text": _gen_text,
        "Column": _gen_column,
        "Row": _gen_row,
        "Center": _gen_center,
        "Padding": _gen_padding,
        "SizedBox": _gen_sizedbox,
        "ElevatedButton": _gen_elevated_button,
        "TextField": _gen_textfield,
        "Image": _gen_image,
        "Icon": _gen_icon,
        "ListView": _gen_listview,
        "Card": _gen_card,
        "Stack": _gen_stack,
        "Positioned": _gen_positioned,
        "FloatingActionButton": _gen_fab,
        "BottomNavigationBar": _gen_bottom_nav,
        "Drawer": _gen_drawer,
        "ListTile": _gen_listtile,
        "Expanded": _gen_expanded,
        "Flexible": _gen_flexible,
        "Wrap": _gen_wrap,
        "GridView": _gen_gridview,
        "CircularProgressIndicator": _gen_circular_progress,
        "Divider": _gen_divider,
        "Spacer": _gen_spacer,
        "Opacity": _gen_opacity,
        "ClipRRect": _gen_cliprrect,
        "SingleChildScrollView": _gen_scrollview,
    }

    gen_func = generators.get(wtype, _gen_generic_container)
    return gen_func(node, props, children, level)


# ---------------------------------------------------------------------------
# Individual widget generators
# ---------------------------------------------------------------------------

def _gen_scaffold(node, props, children, level):
    lines = [f"{_indent(level)}Scaffold("]
    bg = props.get("backgroundColor", "")
    if bg:
        lines.append(f"{_indent(level+1)}backgroundColor: {_color(bg)},")
    # appbar
    appbar_children = [c for c in children if c.get("type") == "AppBar"]
    body_children = [c for c in children if c.get("type") != "AppBar"
                     and c.get("type") != "FloatingActionButton"
                     and c.get("type") != "BottomNavigationBar"
                     and c.get("type") != "Drawer"]
    fab_children = [c for c in children if c.get("type") == "FloatingActionButton"]
    nav_children = [c for c in children if c.get("type") == "BottomNavigationBar"]
    drawer_children = [c for c in children if c.get("type") == "Drawer"]

    if appbar_children:
        lines.append(f"{_indent(level+1)}appBar: {generate_widget(appbar_children[0], level+1).strip()},")
    if drawer_children:
        lines.append(f"{_indent(level+1)}drawer: {generate_widget(drawer_children[0], level+1).strip()},")
    if body_children:
        if len(body_children) == 1:
            lines.append(f"{_indent(level+1)}body: {generate_widget(body_children[0], level+1).strip()},")
        else:
            lines.append(f"{_indent(level+1)}body: Column(")
            lines.append(f"{_indent(level+2)}children: [")
            for c in body_children:
                lines.append(f"{generate_widget(c, level+3)},")
            lines.append(f"{_indent(level+2)}],")
            lines.append(f"{_indent(level+1)}),")
    if fab_children:
        lines.append(f"{_indent(level+1)}floatingActionButton: {generate_widget(fab_children[0], level+1).strip()},")
    if nav_children:
        lines.append(f"{_indent(level+1)}bottomNavigationBar: {generate_widget(nav_children[0], level+1).strip()},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_appbar(node, props, children, level):
    lines = [f"{_indent(level)}AppBar("]
    title = props.get("title", "")
    if title:
        lines.append(f"{_indent(level+1)}title: Text('{_escape(title)}'),")
    bg = props.get("backgroundColor", "")
    if bg:
        lines.append(f"{_indent(level+1)}backgroundColor: {_color(bg)},")
    center = props.get("centerTitle", "")
    if center:
        lines.append(f"{_indent(level+1)}centerTitle: {str(center).lower()},")
    elevation = props.get("elevation", "")
    if elevation:
        lines.append(f"{_indent(level+1)}elevation: {elevation},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_container(node, props, children, level):
    lines = [f"{_indent(level)}Container("]
    _add_box_props(lines, props, level)
    if children:
        if len(children) == 1:
            lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
        else:
            lines.append(f"{_indent(level+1)}child: Column(")
            lines.append(f"{_indent(level+2)}children: [")
            for c in children:
                lines.append(f"{generate_widget(c, level+3)},")
            lines.append(f"{_indent(level+2)}],")
            lines.append(f"{_indent(level+1)}),")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_text(node, props, children, level):
    text = props.get("text", "Text")
    lines = [f"{_indent(level)}Text("]
    lines.append(f"{_indent(level+1)}'{_escape(text)}',")
    style_parts = []
    fs = props.get("fontSize", "")
    if fs:
        style_parts.append(f"fontSize: {fs}")
    fw = props.get("fontWeight", "")
    if fw:
        style_parts.append(f"fontWeight: FontWeight.{fw}")
    color = props.get("color", "")
    if color:
        style_parts.append(f"color: {_color(color)}")
    if style_parts:
        lines.append(f"{_indent(level+1)}style: TextStyle({', '.join(style_parts)}),")
    align = props.get("textAlign", "")
    if align:
        lines.append(f"{_indent(level+1)}textAlign: TextAlign.{align},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_column(node, props, children, level):
    lines = [f"{_indent(level)}Column("]
    _add_axis_props(lines, props, level)
    lines.append(f"{_indent(level+1)}children: [")
    for c in children:
        lines.append(f"{generate_widget(c, level+2)},")
    lines.append(f"{_indent(level+1)}],")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_row(node, props, children, level):
    lines = [f"{_indent(level)}Row("]
    _add_axis_props(lines, props, level)
    lines.append(f"{_indent(level+1)}children: [")
    for c in children:
        lines.append(f"{generate_widget(c, level+2)},")
    lines.append(f"{_indent(level+1)}],")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_center(node, props, children, level):
    lines = [f"{_indent(level)}Center("]
    if children:
        lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_padding(node, props, children, level):
    p = props.get("padding", "8.0")
    lines = [f"{_indent(level)}Padding("]
    lines.append(f"{_indent(level+1)}padding: EdgeInsets.all({p}),")
    if children:
        lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_sizedbox(node, props, children, level):
    lines = [f"{_indent(level)}SizedBox("]
    w = props.get("width", "")
    h = props.get("height", "")
    if w:
        lines.append(f"{_indent(level+1)}width: {w},")
    if h:
        lines.append(f"{_indent(level+1)}height: {h},")
    if children:
        lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_elevated_button(node, props, children, level):
    label = props.get("label", "Button")
    lines = [f"{_indent(level)}ElevatedButton("]
    lines.append(f"{_indent(level+1)}onPressed: () {{}},")
    bg = props.get("backgroundColor", "")
    if bg:
        lines.append(f"{_indent(level+1)}style: ElevatedButton.styleFrom(backgroundColor: {_color(bg)}),")
    if children:
        lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
    else:
        lines.append(f"{_indent(level+1)}child: Text('{_escape(label)}'),")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_textfield(node, props, children, level):
    lines = [f"{_indent(level)}TextField("]
    hint = props.get("hintText", "")
    label = props.get("labelText", "")
    deco_parts = []
    if hint:
        deco_parts.append(f"hintText: '{_escape(hint)}'")
    if label:
        deco_parts.append(f"labelText: '{_escape(label)}'")
    border = props.get("border", "outline")
    if border == "outline":
        deco_parts.append("border: OutlineInputBorder()")
    elif border == "underline":
        deco_parts.append("border: UnderlineInputBorder()")
    if deco_parts:
        lines.append(f"{_indent(level+1)}decoration: InputDecoration({', '.join(deco_parts)}),")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_image(node, props, children, level):
    src = props.get("src", "https://via.placeholder.com/150")
    w = props.get("width", "")
    h = props.get("height", "")
    fit = props.get("fit", "")
    if src.startswith("http"):
        lines = [f"{_indent(level)}Image.network("]
        lines.append(f"{_indent(level+1)}'{_escape(src)}',")
    else:
        lines = [f"{_indent(level)}Image.asset("]
        lines.append(f"{_indent(level+1)}'{_escape(src)}',")
    if w:
        lines.append(f"{_indent(level+1)}width: {w},")
    if h:
        lines.append(f"{_indent(level+1)}height: {h},")
    if fit:
        lines.append(f"{_indent(level+1)}fit: BoxFit.{fit},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_icon(node, props, children, level):
    icon = props.get("icon", "star")
    size = props.get("size", "")
    color = props.get("color", "")
    lines = [f"{_indent(level)}Icon("]
    lines.append(f"{_indent(level+1)}Icons.{icon},")
    if size:
        lines.append(f"{_indent(level+1)}size: {size},")
    if color:
        lines.append(f"{_indent(level+1)}color: {_color(color)},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_listview(node, props, children, level):
    lines = [f"{_indent(level)}ListView("]
    padding = props.get("padding", "")
    if padding:
        lines.append(f"{_indent(level+1)}padding: EdgeInsets.all({padding}),")
    lines.append(f"{_indent(level+1)}children: [")
    for c in children:
        lines.append(f"{generate_widget(c, level+2)},")
    lines.append(f"{_indent(level+1)}],")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_card(node, props, children, level):
    lines = [f"{_indent(level)}Card("]
    elevation = props.get("elevation", "")
    if elevation:
        lines.append(f"{_indent(level+1)}elevation: {elevation},")
    color = props.get("color", "")
    if color:
        lines.append(f"{_indent(level+1)}color: {_color(color)},")
    if children:
        if len(children) == 1:
            lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
        else:
            lines.append(f"{_indent(level+1)}child: Column(")
            lines.append(f"{_indent(level+2)}children: [")
            for c in children:
                lines.append(f"{generate_widget(c, level+3)},")
            lines.append(f"{_indent(level+2)}],")
            lines.append(f"{_indent(level+1)}),")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_stack(node, props, children, level):
    lines = [f"{_indent(level)}Stack("]
    lines.append(f"{_indent(level+1)}children: [")
    for c in children:
        lines.append(f"{generate_widget(c, level+2)},")
    lines.append(f"{_indent(level+1)}],")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_positioned(node, props, children, level):
    lines = [f"{_indent(level)}Positioned("]
    for d in ("top", "bottom", "left", "right"):
        v = props.get(d, "")
        if v:
            lines.append(f"{_indent(level+1)}{d}: {v},")
    if children:
        lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_fab(node, props, children, level):
    lines = [f"{_indent(level)}FloatingActionButton("]
    lines.append(f"{_indent(level+1)}onPressed: () {{}},")
    bg = props.get("backgroundColor", "")
    if bg:
        lines.append(f"{_indent(level+1)}backgroundColor: {_color(bg)},")
    icon = props.get("icon", "add")
    lines.append(f"{_indent(level+1)}child: Icon(Icons.{icon}),")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_bottom_nav(node, props, children, level):
    lines = [f"{_indent(level)}BottomNavigationBar("]
    lines.append(f"{_indent(level+1)}items: [")
    items = props.get("items", [{"icon": "home", "label": "Home"}, {"icon": "settings", "label": "Settings"}])
    for item in items:
        lines.append(f"{_indent(level+2)}BottomNavigationBarItem(icon: Icon(Icons.{item.get('icon','home')}), label: '{_escape(item.get('label',''))}'),")
    lines.append(f"{_indent(level+1)}],")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_drawer(node, props, children, level):
    lines = [f"{_indent(level)}Drawer("]
    if children:
        if len(children) == 1:
            lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
        else:
            lines.append(f"{_indent(level+1)}child: ListView(")
            lines.append(f"{_indent(level+2)}children: [")
            for c in children:
                lines.append(f"{generate_widget(c, level+3)},")
            lines.append(f"{_indent(level+2)}],")
            lines.append(f"{_indent(level+1)}),")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_listtile(node, props, children, level):
    lines = [f"{_indent(level)}ListTile("]
    title = props.get("title", "")
    subtitle = props.get("subtitle", "")
    icon = props.get("leadingIcon", "")
    if icon:
        lines.append(f"{_indent(level+1)}leading: Icon(Icons.{icon}),")
    if title:
        lines.append(f"{_indent(level+1)}title: Text('{_escape(title)}'),")
    if subtitle:
        lines.append(f"{_indent(level+1)}subtitle: Text('{_escape(subtitle)}'),")
    lines.append(f"{_indent(level+1)}onTap: () {{}},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_expanded(node, props, children, level):
    lines = [f"{_indent(level)}Expanded("]
    flex = props.get("flex", "")
    if flex:
        lines.append(f"{_indent(level+1)}flex: {flex},")
    if children:
        lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_flexible(node, props, children, level):
    lines = [f"{_indent(level)}Flexible("]
    flex = props.get("flex", "")
    if flex:
        lines.append(f"{_indent(level+1)}flex: {flex},")
    if children:
        lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_wrap(node, props, children, level):
    lines = [f"{_indent(level)}Wrap("]
    spacing = props.get("spacing", "")
    if spacing:
        lines.append(f"{_indent(level+1)}spacing: {spacing},")
    run_spacing = props.get("runSpacing", "")
    if run_spacing:
        lines.append(f"{_indent(level+1)}runSpacing: {run_spacing},")
    lines.append(f"{_indent(level+1)}children: [")
    for c in children:
        lines.append(f"{generate_widget(c, level+2)},")
    lines.append(f"{_indent(level+1)}],")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_gridview(node, props, children, level):
    cols = props.get("crossAxisCount", "2")
    lines = [f"{_indent(level)}GridView.count("]
    lines.append(f"{_indent(level+1)}crossAxisCount: {cols},")
    spacing = props.get("crossAxisSpacing", "")
    if spacing:
        lines.append(f"{_indent(level+1)}crossAxisSpacing: {spacing},")
    main_spacing = props.get("mainAxisSpacing", "")
    if main_spacing:
        lines.append(f"{_indent(level+1)}mainAxisSpacing: {main_spacing},")
    lines.append(f"{_indent(level+1)}shrinkWrap: true,")
    lines.append(f"{_indent(level+1)}children: [")
    for c in children:
        lines.append(f"{generate_widget(c, level+2)},")
    lines.append(f"{_indent(level+1)}],")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_circular_progress(node, props, children, level):
    lines = [f"{_indent(level)}CircularProgressIndicator("]
    color = props.get("color", "")
    if color:
        lines.append(f"{_indent(level+1)}color: {_color(color)},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_divider(node, props, children, level):
    lines = [f"{_indent(level)}Divider("]
    thickness = props.get("thickness", "")
    if thickness:
        lines.append(f"{_indent(level+1)}thickness: {thickness},")
    color = props.get("color", "")
    if color:
        lines.append(f"{_indent(level+1)}color: {_color(color)},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_spacer(node, props, children, level):
    flex = props.get("flex", "")
    if flex:
        return f"{_indent(level)}Spacer(flex: {flex})"
    return f"{_indent(level)}Spacer()"


def _gen_opacity(node, props, children, level):
    op = props.get("opacity", "1.0")
    lines = [f"{_indent(level)}Opacity("]
    lines.append(f"{_indent(level+1)}opacity: {op},")
    if children:
        lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_cliprrect(node, props, children, level):
    radius = props.get("borderRadius", "8.0")
    lines = [f"{_indent(level)}ClipRRect("]
    lines.append(f"{_indent(level+1)}borderRadius: BorderRadius.circular({radius}),")
    if children:
        lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_scrollview(node, props, children, level):
    lines = [f"{_indent(level)}SingleChildScrollView("]
    if children:
        if len(children) == 1:
            lines.append(f"{_indent(level+1)}child: {generate_widget(children[0], level+1).strip()},")
        else:
            lines.append(f"{_indent(level+1)}child: Column(")
            lines.append(f"{_indent(level+2)}children: [")
            for c in children:
                lines.append(f"{generate_widget(c, level+3)},")
            lines.append(f"{_indent(level+2)}],")
            lines.append(f"{_indent(level+1)}),")
    lines.append(f"{_indent(level)})")
    return "\n".join(lines)


def _gen_generic_container(node, props, children, level):
    return _gen_container(node, props, children, level)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_box_props(lines, props, level):
    w = props.get("width", "")
    h = props.get("height", "")
    color = props.get("color", "")
    margin = props.get("margin", "")
    padding = props.get("padding", "")
    border_radius = props.get("borderRadius", "")
    alignment = props.get("alignment", "")

    if w:
        lines.append(f"{_indent(level+1)}width: {w},")
    if h:
        lines.append(f"{_indent(level+1)}height: {h},")
    if alignment:
        lines.append(f"{_indent(level+1)}alignment: Alignment.{alignment},")
    if margin:
        lines.append(f"{_indent(level+1)}margin: EdgeInsets.all({margin}),")
    if padding:
        lines.append(f"{_indent(level+1)}padding: EdgeInsets.all({padding}),")

    deco_parts = []
    if color:
        deco_parts.append(f"color: {_color(color)}")
    if border_radius:
        deco_parts.append(f"borderRadius: BorderRadius.circular({border_radius})")
    if deco_parts:
        lines.append(f"{_indent(level+1)}decoration: BoxDecoration({', '.join(deco_parts)}),")


def _add_axis_props(lines, props, level):
    main = props.get("mainAxisAlignment", "")
    cross = props.get("crossAxisAlignment", "")
    main_size = props.get("mainAxisSize", "")
    if main:
        lines.append(f"{_indent(level+1)}mainAxisAlignment: MainAxisAlignment.{main},")
    if cross:
        lines.append(f"{_indent(level+1)}crossAxisAlignment: CrossAxisAlignment.{cross},")
    if main_size:
        lines.append(f"{_indent(level+1)}mainAxisSize: MainAxisSize.{main_size},")


def _color(hex_val):
    if not hex_val:
        return "Colors.transparent"
    named_colors = {
        "red": "Colors.red", "blue": "Colors.blue", "green": "Colors.green",
        "white": "Colors.white", "black": "Colors.black", "grey": "Colors.grey",
        "gray": "Colors.grey", "orange": "Colors.orange", "purple": "Colors.purple",
        "yellow": "Colors.yellow", "pink": "Colors.pink", "teal": "Colors.teal",
        "cyan": "Colors.cyan", "amber": "Colors.amber", "indigo": "Colors.indigo",
        "brown": "Colors.brown", "transparent": "Colors.transparent",
    }
    if hex_val.lower() in named_colors:
        return named_colors[hex_val.lower()]
    hex_val = hex_val.lstrip("#")
    if len(hex_val) == 6:
        return f"Color(0xFF{hex_val.upper()})"
    if len(hex_val) == 8:
        return f"Color(0x{hex_val.upper()})"
    return f"Colors.blue"


def _escape(text):
    return text.replace("\\", "\\\\").replace("'", "\\'")


# ---------------------------------------------------------------------------
# Full project generation
# ---------------------------------------------------------------------------

def generate_page(page_name, widget_tree, is_home=False):
    """Generate a full StatelessWidget page class."""
    class_name = page_name.replace(" ", "")
    body = generate_widget(widget_tree, 3)
    return f"""class {class_name}Page extends StatelessWidget {{
  const {class_name}Page({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return {body.strip()};
  }}
}}"""


def generate_full_app(project_name, pages, theme=None):
    """Generate a complete main.dart for a multi-page Flutter app."""
    if not pages:
        pages = [{"name": "Home", "tree": {"type": "Scaffold", "properties": {}, "children": []}}]

    home_page = pages[0]
    home_class = home_page["name"].replace(" ", "")

    theme_str = ""
    if theme:
        primary = theme.get("primaryColor", "blue")
        brightness = theme.get("brightness", "light")
        theme_str = f"""
      theme: ThemeData(
        colorSchemeSeed: {_color(primary)},
        brightness: Brightness.{brightness},
        useMaterial3: true,
      ),"""

    routes = ""
    if len(pages) > 1:
        route_entries = []
        for p in pages:
            cname = p["name"].replace(" ", "")
            rname = "/" + p["name"].lower().replace(" ", "-")
            route_entries.append(f"        '{rname}': (context) => const {cname}Page(),")
        routes = "\n      routes: {\n" + "\n".join(route_entries) + "\n      },"

    page_classes = []
    for p in pages:
        page_classes.append(generate_page(p["name"], p["tree"]))

    safe_name = _escape(project_name)

    return f"""import 'package:flutter/material.dart';

void main() {{
  runApp(const MyApp());
}}

class MyApp extends StatelessWidget {{
  const MyApp({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: '{safe_name}',
      debugShowCheckedModeBanner: false,{theme_str}{routes}
      home: const {home_class}Page(),
    );
  }}
}}

{chr(10).join(page_classes)}
"""


def generate_pubspec(project_name):
    """Generate a basic pubspec.yaml."""
    safe = project_name.lower().replace(" ", "_").replace("-", "_")
    return f"""name: {safe}
description: A Flutter application built with TourEx Builder.
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.6

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0

flutter:
  uses-material-design: true
"""
