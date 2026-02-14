/**
 * Widget definitions for the Flutter App Builder.
 * Each widget defines its category, icon, default properties, and accepted children.
 */

const WIDGET_DEFS = {
  // ── Layout ────────────────────────────────────────────────
  Scaffold: {
    category: "Layout",
    icon: "web",
    label: "Scaffold",
    acceptsChildren: true,
    isRoot: true,
    defaultProps: { backgroundColor: "" },
    propertyDefs: [
      { key: "backgroundColor", label: "Background", type: "color" },
    ],
  },
  AppBar: {
    category: "Layout",
    icon: "web_asset",
    label: "AppBar",
    acceptsChildren: false,
    defaultProps: { title: "App Title", backgroundColor: "", centerTitle: "", elevation: "" },
    propertyDefs: [
      { key: "title", label: "Title", type: "text" },
      { key: "backgroundColor", label: "Background", type: "color" },
      { key: "centerTitle", label: "Center Title", type: "select", options: ["", "true", "false"] },
      { key: "elevation", label: "Elevation", type: "number" },
    ],
  },
  Column: {
    category: "Layout",
    icon: "view_column",
    label: "Column",
    acceptsChildren: true,
    defaultProps: { mainAxisAlignment: "", crossAxisAlignment: "", mainAxisSize: "" },
    propertyDefs: [
      { key: "mainAxisAlignment", label: "Main Axis", type: "select", options: ["", "start", "end", "center", "spaceBetween", "spaceAround", "spaceEvenly"] },
      { key: "crossAxisAlignment", label: "Cross Axis", type: "select", options: ["", "start", "end", "center", "stretch"] },
      { key: "mainAxisSize", label: "Main Size", type: "select", options: ["", "min", "max"] },
    ],
  },
  Row: {
    category: "Layout",
    icon: "table_rows",
    label: "Row",
    acceptsChildren: true,
    defaultProps: { mainAxisAlignment: "", crossAxisAlignment: "" },
    propertyDefs: [
      { key: "mainAxisAlignment", label: "Main Axis", type: "select", options: ["", "start", "end", "center", "spaceBetween", "spaceAround", "spaceEvenly"] },
      { key: "crossAxisAlignment", label: "Cross Axis", type: "select", options: ["", "start", "end", "center", "stretch"] },
    ],
  },
  Container: {
    category: "Layout",
    icon: "check_box_outline_blank",
    label: "Container",
    acceptsChildren: true,
    defaultProps: { width: "", height: "", color: "", padding: "", margin: "", borderRadius: "", alignment: "" },
    propertyDefs: [
      { key: "width", label: "Width", type: "number" },
      { key: "height", label: "Height", type: "number" },
      { key: "color", label: "Color", type: "color" },
      { key: "padding", label: "Padding", type: "number" },
      { key: "margin", label: "Margin", type: "number" },
      { key: "borderRadius", label: "Radius", type: "number" },
      { key: "alignment", label: "Alignment", type: "select", options: ["", "center", "topLeft", "topCenter", "topRight", "centerLeft", "centerRight", "bottomLeft", "bottomCenter", "bottomRight"] },
    ],
  },
  Center: {
    category: "Layout",
    icon: "filter_center_focus",
    label: "Center",
    acceptsChildren: true,
    maxChildren: 1,
    defaultProps: {},
    propertyDefs: [],
  },
  Padding: {
    category: "Layout",
    icon: "padding",
    label: "Padding",
    acceptsChildren: true,
    maxChildren: 1,
    defaultProps: { padding: "8.0" },
    propertyDefs: [
      { key: "padding", label: "Padding", type: "number" },
    ],
  },
  SizedBox: {
    category: "Layout",
    icon: "aspect_ratio",
    label: "SizedBox",
    acceptsChildren: true,
    maxChildren: 1,
    defaultProps: { width: "", height: "16" },
    propertyDefs: [
      { key: "width", label: "Width", type: "number" },
      { key: "height", label: "Height", type: "number" },
    ],
  },
  Expanded: {
    category: "Layout",
    icon: "expand",
    label: "Expanded",
    acceptsChildren: true,
    maxChildren: 1,
    defaultProps: { flex: "" },
    propertyDefs: [
      { key: "flex", label: "Flex", type: "number" },
    ],
  },
  Flexible: {
    category: "Layout",
    icon: "swap_vert",
    label: "Flexible",
    acceptsChildren: true,
    maxChildren: 1,
    defaultProps: { flex: "" },
    propertyDefs: [
      { key: "flex", label: "Flex", type: "number" },
    ],
  },
  Stack: {
    category: "Layout",
    icon: "layers",
    label: "Stack",
    acceptsChildren: true,
    defaultProps: {},
    propertyDefs: [],
  },
  Positioned: {
    category: "Layout",
    icon: "pinch",
    label: "Positioned",
    acceptsChildren: true,
    maxChildren: 1,
    defaultProps: { top: "", bottom: "", left: "", right: "" },
    propertyDefs: [
      { key: "top", label: "Top", type: "number" },
      { key: "bottom", label: "Bottom", type: "number" },
      { key: "left", label: "Left", type: "number" },
      { key: "right", label: "Right", type: "number" },
    ],
  },
  Wrap: {
    category: "Layout",
    icon: "wrap_text",
    label: "Wrap",
    acceptsChildren: true,
    defaultProps: { spacing: "8", runSpacing: "8" },
    propertyDefs: [
      { key: "spacing", label: "Spacing", type: "number" },
      { key: "runSpacing", label: "Run Spacing", type: "number" },
    ],
  },

  // ── Scrolling ─────────────────────────────────────────────
  SingleChildScrollView: {
    category: "Scrolling",
    icon: "swap_vert",
    label: "ScrollView",
    acceptsChildren: true,
    defaultProps: {},
    propertyDefs: [],
  },
  ListView: {
    category: "Scrolling",
    icon: "view_list",
    label: "ListView",
    acceptsChildren: true,
    defaultProps: { padding: "" },
    propertyDefs: [
      { key: "padding", label: "Padding", type: "number" },
    ],
  },
  GridView: {
    category: "Scrolling",
    icon: "grid_view",
    label: "GridView",
    acceptsChildren: true,
    defaultProps: { crossAxisCount: "2", crossAxisSpacing: "8", mainAxisSpacing: "8" },
    propertyDefs: [
      { key: "crossAxisCount", label: "Columns", type: "number" },
      { key: "crossAxisSpacing", label: "H Spacing", type: "number" },
      { key: "mainAxisSpacing", label: "V Spacing", type: "number" },
    ],
  },

  // ── Display ───────────────────────────────────────────────
  Text: {
    category: "Display",
    icon: "text_fields",
    label: "Text",
    acceptsChildren: false,
    defaultProps: { text: "Hello World", fontSize: "", fontWeight: "", color: "", textAlign: "" },
    propertyDefs: [
      { key: "text", label: "Text", type: "text" },
      { key: "fontSize", label: "Size", type: "number" },
      { key: "fontWeight", label: "Weight", type: "select", options: ["", "normal", "bold", "w100", "w200", "w300", "w400", "w500", "w600", "w700", "w800", "w900"] },
      { key: "color", label: "Color", type: "color" },
      { key: "textAlign", label: "Align", type: "select", options: ["", "left", "center", "right", "justify"] },
    ],
  },
  Icon: {
    category: "Display",
    icon: "star",
    label: "Icon",
    acceptsChildren: false,
    defaultProps: { icon: "star", size: "", color: "" },
    propertyDefs: [
      { key: "icon", label: "Icon", type: "text" },
      { key: "size", label: "Size", type: "number" },
      { key: "color", label: "Color", type: "color" },
    ],
  },
  Image: {
    category: "Display",
    icon: "image",
    label: "Image",
    acceptsChildren: false,
    defaultProps: { src: "https://via.placeholder.com/150", width: "", height: "", fit: "" },
    propertyDefs: [
      { key: "src", label: "Source", type: "text" },
      { key: "width", label: "Width", type: "number" },
      { key: "height", label: "Height", type: "number" },
      { key: "fit", label: "Fit", type: "select", options: ["", "cover", "contain", "fill", "fitWidth", "fitHeight"] },
    ],
  },
  Divider: {
    category: "Display",
    icon: "horizontal_rule",
    label: "Divider",
    acceptsChildren: false,
    defaultProps: { thickness: "", color: "" },
    propertyDefs: [
      { key: "thickness", label: "Thickness", type: "number" },
      { key: "color", label: "Color", type: "color" },
    ],
  },
  Spacer: {
    category: "Display",
    icon: "space_bar",
    label: "Spacer",
    acceptsChildren: false,
    defaultProps: { flex: "" },
    propertyDefs: [
      { key: "flex", label: "Flex", type: "number" },
    ],
  },
  CircularProgressIndicator: {
    category: "Display",
    icon: "progress_activity",
    label: "Progress",
    acceptsChildren: false,
    defaultProps: { color: "" },
    propertyDefs: [
      { key: "color", label: "Color", type: "color" },
    ],
  },

  // ── Input ─────────────────────────────────────────────────
  ElevatedButton: {
    category: "Input",
    icon: "smart_button",
    label: "Button",
    acceptsChildren: true,
    maxChildren: 1,
    defaultProps: { label: "Button", backgroundColor: "" },
    propertyDefs: [
      { key: "label", label: "Label", type: "text" },
      { key: "backgroundColor", label: "Background", type: "color" },
    ],
  },
  TextField: {
    category: "Input",
    icon: "edit",
    label: "TextField",
    acceptsChildren: false,
    defaultProps: { hintText: "Enter text...", labelText: "", border: "outline" },
    propertyDefs: [
      { key: "hintText", label: "Hint", type: "text" },
      { key: "labelText", label: "Label", type: "text" },
      { key: "border", label: "Border", type: "select", options: ["outline", "underline", "none"] },
    ],
  },

  // ── Composite ─────────────────────────────────────────────
  Card: {
    category: "Composite",
    icon: "crop_square",
    label: "Card",
    acceptsChildren: true,
    defaultProps: { elevation: "2", color: "" },
    propertyDefs: [
      { key: "elevation", label: "Elevation", type: "number" },
      { key: "color", label: "Color", type: "color" },
    ],
  },
  ListTile: {
    category: "Composite",
    icon: "list",
    label: "ListTile",
    acceptsChildren: false,
    defaultProps: { title: "Title", subtitle: "", leadingIcon: "" },
    propertyDefs: [
      { key: "title", label: "Title", type: "text" },
      { key: "subtitle", label: "Subtitle", type: "text" },
      { key: "leadingIcon", label: "Icon", type: "text" },
    ],
  },
  FloatingActionButton: {
    category: "Composite",
    icon: "add_circle",
    label: "FAB",
    acceptsChildren: false,
    defaultProps: { icon: "add", backgroundColor: "" },
    propertyDefs: [
      { key: "icon", label: "Icon", type: "text" },
      { key: "backgroundColor", label: "Background", type: "color" },
    ],
  },
  BottomNavigationBar: {
    category: "Composite",
    icon: "bottom_navigation",
    label: "BottomNav",
    acceptsChildren: false,
    defaultProps: {
      items: [
        { icon: "home", label: "Home" },
        { icon: "search", label: "Search" },
        { icon: "person", label: "Profile" },
      ],
    },
    propertyDefs: [],
  },
  Drawer: {
    category: "Composite",
    icon: "menu",
    label: "Drawer",
    acceptsChildren: true,
    defaultProps: {},
    propertyDefs: [],
  },

  // ── Effects ───────────────────────────────────────────────
  Opacity: {
    category: "Effects",
    icon: "opacity",
    label: "Opacity",
    acceptsChildren: true,
    maxChildren: 1,
    defaultProps: { opacity: "1.0" },
    propertyDefs: [
      { key: "opacity", label: "Opacity", type: "number", min: 0, max: 1, step: 0.1 },
    ],
  },
  ClipRRect: {
    category: "Effects",
    icon: "rounded_corner",
    label: "ClipRRect",
    acceptsChildren: true,
    maxChildren: 1,
    defaultProps: { borderRadius: "8.0" },
    propertyDefs: [
      { key: "borderRadius", label: "Radius", type: "number" },
    ],
  },
};

// Gather categories
const WIDGET_CATEGORIES = {};
for (const [type, def] of Object.entries(WIDGET_DEFS)) {
  const cat = def.category;
  if (!WIDGET_CATEGORIES[cat]) WIDGET_CATEGORIES[cat] = [];
  WIDGET_CATEGORIES[cat].push({ type, ...def });
}
