/**
 * TourEx Flutter App Builder - Main logic
 * Handles: project management, canvas rendering, drag-and-drop,
 * widget tree, property editing, code generation, undo/redo.
 */

// ================================================================
// STATE
// ================================================================

const state = {
  project: null,         // current project metadata
  currentPageIdx: 0,     // index of active page
  selectedId: null,      // id of selected widget node
  undoStack: [],
  redoStack: [],
  dragType: null,        // widget type being dragged from palette
  dragNode: null,        // node being moved from tree
  counter: 0,            // unique id counter
};

function uid() {
  return "w" + (++state.counter) + "-" + Date.now().toString(36);
}

function currentPage() {
  if (!state.project || !state.project.pages[state.currentPageIdx]) return null;
  return state.project.pages[state.currentPageIdx];
}

function currentTree() {
  const p = currentPage();
  return p ? p.tree : null;
}

// ================================================================
// DEEP CLONE HELPER
// ================================================================

function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

// ================================================================
// UNDO / REDO
// ================================================================

function saveSnapshot() {
  state.undoStack.push(deepClone(state.project));
  if (state.undoStack.length > 50) state.undoStack.shift();
  state.redoStack = [];
}

function undo() {
  if (!state.undoStack.length) return;
  state.redoStack.push(deepClone(state.project));
  state.project = state.undoStack.pop();
  render();
  autoSave();
}

function redo() {
  if (!state.redoStack.length) return;
  state.undoStack.push(deepClone(state.project));
  state.project = state.redoStack.pop();
  render();
  autoSave();
}

// ================================================================
// TREE SEARCH HELPERS
// ================================================================

function findNodeById(tree, id) {
  if (!tree) return null;
  if (tree.id === id) return tree;
  for (const c of (tree.children || [])) {
    const found = findNodeById(c, id);
    if (found) return found;
  }
  return null;
}

function findParent(tree, id) {
  if (!tree || !tree.children) return null;
  for (const c of tree.children) {
    if (c.id === id) return tree;
    const found = findParent(c, id);
    if (found) return found;
  }
  return null;
}

function removeNodeById(tree, id) {
  if (!tree.children) return false;
  const idx = tree.children.findIndex((c) => c.id === id);
  if (idx !== -1) {
    tree.children.splice(idx, 1);
    return true;
  }
  for (const c of tree.children) {
    if (removeNodeById(c, id)) return true;
  }
  return false;
}

// ================================================================
// PROJECT MANAGEMENT
// ================================================================

async function loadProjects() {
  const res = await fetch("/api/projects");
  const projects = await res.json();
  const list = document.getElementById("project-list");
  list.innerHTML = "";
  if (!projects.length) {
    list.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px;">No projects yet. Create one above.</p>';
    return;
  }
  for (const p of projects) {
    const div = document.createElement("div");
    div.className = "project-item";
    div.innerHTML = `
      <span class="project-item-name">${p.name}</span>
      <div class="project-item-actions">
        <button class="btn btn-icon btn-danger" data-delete="${p.slug}" title="Delete">
          <span class="material-symbols-outlined">delete</span>
        </button>
      </div>`;
    div.addEventListener("click", (e) => {
      if (e.target.closest("[data-delete]")) return;
      openProject(p.slug);
    });
    div.querySelector("[data-delete]").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (confirm(`Delete "${p.name}"?`)) {
        await fetch(`/api/projects/${p.slug}`, { method: "DELETE" });
        loadProjects();
      }
    });
    list.appendChild(div);
  }
}

async function createProject() {
  const name = document.getElementById("new-project-name").value.trim() || "Untitled";
  const res = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  const project = await res.json();
  state.project = project;
  enterBuilder();
}

async function openProject(slug) {
  const res = await fetch(`/api/projects/${slug}`);
  state.project = await res.json();
  // Recount ids
  state.counter = 0;
  enterBuilder();
}

async function autoSave() {
  if (!state.project) return;
  await fetch(`/api/projects/${state.project.slug}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.project),
  });
}

function enterBuilder() {
  document.getElementById("project-modal").classList.remove("active");
  document.getElementById("builder").classList.remove("hidden");
  document.getElementById("project-title").textContent = state.project.name;
  state.currentPageIdx = 0;
  state.selectedId = null;
  render();
}

function exitBuilder() {
  document.getElementById("project-modal").classList.add("active");
  document.getElementById("builder").classList.add("hidden");
  state.project = null;
  loadProjects();
}

// ================================================================
// RENDER ALL
// ================================================================

function render() {
  renderPageTabs();
  renderCanvas();
  renderWidgetTree();
  renderProperties();
}

// ================================================================
// PAGE TABS
// ================================================================

function renderPageTabs() {
  const tabs = document.getElementById("page-tabs");
  tabs.innerHTML = "";
  if (!state.project) return;
  state.project.pages.forEach((page, i) => {
    const btn = document.createElement("button");
    btn.className = "page-tab" + (i === state.currentPageIdx ? " active" : "");
    btn.textContent = page.name;
    btn.addEventListener("click", () => {
      state.currentPageIdx = i;
      state.selectedId = null;
      render();
    });
    // Double-click to rename
    btn.addEventListener("dblclick", () => {
      const newName = prompt("Page name:", page.name);
      if (newName && newName.trim()) {
        saveSnapshot();
        page.name = newName.trim();
        render();
        autoSave();
      }
    });
    tabs.appendChild(btn);
  });
}

function addPage() {
  if (!state.project) return;
  const name = prompt("New page name:", "Page " + (state.project.pages.length + 1));
  if (!name) return;
  saveSnapshot();
  state.project.pages.push({
    name: name.trim(),
    tree: {
      id: uid(),
      type: "Scaffold",
      properties: {},
      children: [
        {
          id: uid(),
          type: "AppBar",
          properties: { title: name.trim() },
          children: [],
        },
        {
          id: uid(),
          type: "Center",
          properties: {},
          children: [
            {
              id: uid(),
              type: "Text",
              properties: { text: name.trim(), fontSize: "20" },
              children: [],
            },
          ],
        },
      ],
    },
  });
  state.currentPageIdx = state.project.pages.length - 1;
  state.selectedId = null;
  render();
  autoSave();
}

// ================================================================
// CANVAS RENDERING
// ================================================================

function renderCanvas() {
  const canvas = document.getElementById("canvas");
  const tree = currentTree();
  if (!tree) {
    canvas.innerHTML = '<div class="drop-placeholder">Drop widgets here</div>';
    return;
  }
  canvas.innerHTML = "";
  const el = renderCanvasNode(tree);
  if (el) canvas.appendChild(el);
}

function renderCanvasNode(node) {
  if (!node) return null;
  const def = WIDGET_DEFS[node.type];
  const el = document.createElement("div");
  el.className = `canvas-widget cw-${node.type.toLowerCase()}`;
  el.dataset.id = node.id;

  if (state.selectedId === node.id) el.classList.add("selected");

  // Label
  const label = document.createElement("span");
  label.className = "canvas-widget-label";
  label.textContent = node.type;
  el.appendChild(label);

  // Click to select
  el.addEventListener("click", (e) => {
    e.stopPropagation();
    state.selectedId = node.id;
    render();
  });

  // Drop target for drag-and-drop
  if (def && def.acceptsChildren) {
    el.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.stopPropagation();
      el.classList.add("drop-target");
    });
    el.addEventListener("dragleave", (e) => {
      el.classList.remove("drop-target");
    });
    el.addEventListener("drop", (e) => {
      e.preventDefault();
      e.stopPropagation();
      el.classList.remove("drop-target");
      handleDrop(node.id);
    });
  }

  const props = node.properties || {};

  // Render specific visual styles
  switch (node.type) {
    case "Scaffold":
      if (props.backgroundColor) el.style.backgroundColor = props.backgroundColor;
      break;

    case "AppBar": {
      const bg = props.backgroundColor || "#2196F3";
      el.style.backgroundColor = bg;
      el.textContent = "";
      el.appendChild(label);
      const titleSpan = document.createElement("span");
      titleSpan.textContent = props.title || "App Bar";
      el.appendChild(titleSpan);
      break;
    }

    case "Text": {
      el.textContent = "";
      el.appendChild(label);
      const textSpan = document.createElement("span");
      textSpan.textContent = props.text || "Text";
      if (props.fontSize) textSpan.style.fontSize = props.fontSize + "px";
      if (props.fontWeight) {
        const fw = props.fontWeight;
        textSpan.style.fontWeight = fw === "bold" ? "bold" : fw.startsWith("w") ? fw.slice(1) : fw;
      }
      if (props.color) textSpan.style.color = props.color;
      if (props.textAlign) el.style.textAlign = props.textAlign;
      el.appendChild(textSpan);
      break;
    }

    case "Container":
      if (props.width) el.style.width = props.width + "px";
      if (props.height) el.style.height = props.height + "px";
      if (props.color) el.style.backgroundColor = props.color;
      if (props.padding) el.style.padding = props.padding + "px";
      if (props.margin) el.style.margin = props.margin + "px";
      if (props.borderRadius) el.style.borderRadius = props.borderRadius + "px";
      break;

    case "ElevatedButton": {
      el.textContent = "";
      el.appendChild(label);
      const btnSpan = document.createElement("span");
      btnSpan.textContent = props.label || "Button";
      el.appendChild(btnSpan);
      if (props.backgroundColor) el.style.backgroundColor = props.backgroundColor;
      break;
    }

    case "TextField":
      el.textContent = "";
      el.appendChild(label);
      const hintSpan = document.createElement("span");
      hintSpan.textContent = props.hintText || props.labelText || "Text field";
      el.appendChild(hintSpan);
      break;

    case "Image": {
      el.textContent = "";
      el.appendChild(label);
      const imgIcon = document.createElement("span");
      imgIcon.className = "material-symbols-outlined";
      imgIcon.textContent = "image";
      imgIcon.style.fontSize = "32px";
      el.appendChild(imgIcon);
      if (props.width) el.style.width = props.width + "px";
      if (props.height) el.style.height = props.height + "px";
      break;
    }

    case "Icon": {
      el.textContent = "";
      el.appendChild(label);
      const iconSpan = document.createElement("span");
      iconSpan.className = "material-symbols-outlined";
      iconSpan.textContent = props.icon || "star";
      if (props.size) iconSpan.style.fontSize = props.size + "px";
      if (props.color) iconSpan.style.color = props.color;
      el.appendChild(iconSpan);
      break;
    }

    case "SizedBox":
      if (props.width) el.style.width = props.width + "px";
      if (props.height) el.style.height = props.height + "px";
      break;

    case "Padding":
      el.style.padding = (props.padding || "8") + "px";
      break;

    case "Card":
      break;

    case "ListTile": {
      el.textContent = "";
      el.appendChild(label);
      if (props.leadingIcon) {
        const li = document.createElement("span");
        li.className = "material-symbols-outlined cw-listtile-icon";
        li.textContent = props.leadingIcon;
        el.appendChild(li);
      }
      const content = document.createElement("div");
      content.className = "cw-listtile-content";
      const t = document.createElement("div");
      t.className = "cw-listtile-title";
      t.textContent = props.title || "Title";
      content.appendChild(t);
      if (props.subtitle) {
        const s = document.createElement("div");
        s.className = "cw-listtile-subtitle";
        s.textContent = props.subtitle;
        content.appendChild(s);
      }
      el.appendChild(content);
      break;
    }

    case "FloatingActionButton": {
      el.textContent = "";
      el.appendChild(label);
      if (props.backgroundColor) el.style.backgroundColor = props.backgroundColor;
      const fabIcon = document.createElement("span");
      fabIcon.className = "material-symbols-outlined";
      fabIcon.textContent = props.icon || "add";
      el.appendChild(fabIcon);
      break;
    }

    case "BottomNavigationBar": {
      el.textContent = "";
      el.appendChild(label);
      const items = props.items || [{ icon: "home", label: "Home" }];
      items.forEach((item) => {
        const navItem = document.createElement("div");
        navItem.className = "cw-bottomnav-item";
        const ic = document.createElement("span");
        ic.className = "material-symbols-outlined";
        ic.textContent = item.icon || "home";
        navItem.appendChild(ic);
        const lb = document.createElement("span");
        lb.textContent = item.label || "";
        navItem.appendChild(lb);
        el.appendChild(navItem);
      });
      break;
    }

    case "Divider":
      if (props.thickness) el.style.height = props.thickness + "px";
      if (props.color) el.style.backgroundColor = props.color;
      break;

    case "CircularProgressIndicator":
      if (props.color) el.style.borderTopColor = props.color;
      break;

    case "Opacity":
      el.style.opacity = props.opacity || "1.0";
      break;

    case "ClipRRect":
      el.style.borderRadius = (props.borderRadius || "8") + "px";
      break;

    case "GridView":
      el.style.gridTemplateColumns = `repeat(${props.crossAxisCount || 2}, 1fr)`;
      if (props.crossAxisSpacing) el.style.gap = props.crossAxisSpacing + "px";
      break;

    case "Column":
      if (props.mainAxisAlignment) {
        const map = { start: "flex-start", end: "flex-end", center: "center", spaceBetween: "space-between", spaceAround: "space-around", spaceEvenly: "space-evenly" };
        el.style.justifyContent = map[props.mainAxisAlignment] || "";
      }
      if (props.crossAxisAlignment) {
        const map = { start: "flex-start", end: "flex-end", center: "center", stretch: "stretch" };
        el.style.alignItems = map[props.crossAxisAlignment] || "";
      }
      break;

    case "Row":
      if (props.mainAxisAlignment) {
        const map = { start: "flex-start", end: "flex-end", center: "center", spaceBetween: "space-between", spaceAround: "space-around", spaceEvenly: "space-evenly" };
        el.style.justifyContent = map[props.mainAxisAlignment] || "";
      }
      if (props.crossAxisAlignment) {
        const map = { start: "flex-start", end: "flex-end", center: "center", stretch: "stretch" };
        el.style.alignItems = map[props.crossAxisAlignment] || "";
      }
      break;
  }

  // Render children
  if (node.children && node.children.length > 0) {
    for (const child of node.children) {
      const childEl = renderCanvasNode(child);
      if (childEl) el.appendChild(childEl);
    }
  } else if (def && def.acceptsChildren && node.type !== "Scaffold") {
    const ph = document.createElement("div");
    ph.className = "drop-placeholder";
    ph.textContent = "Drop here";
    ph.style.padding = "12px";
    ph.style.fontSize = "11px";
    el.appendChild(ph);
  }

  return el;
}

// ================================================================
// WIDGET PALETTE
// ================================================================

function renderWidgetPalette() {
  const palette = document.getElementById("widget-palette");
  palette.innerHTML = "";

  for (const [catName, widgets] of Object.entries(WIDGET_CATEGORIES)) {
    if (catName === "Layout" && widgets.find((w) => w.isRoot)) {
      // Don't show Scaffold in palette
    }
    const cat = document.createElement("div");
    cat.className = "widget-category";
    cat.dataset.category = catName;

    const title = document.createElement("div");
    title.className = "widget-category-title";
    title.textContent = catName;
    cat.appendChild(title);

    const grid = document.createElement("div");
    grid.className = "widget-grid";

    for (const w of widgets) {
      if (w.isRoot) continue;
      const item = document.createElement("div");
      item.className = "widget-item";
      item.draggable = true;
      item.dataset.type = w.type;
      item.innerHTML = `<span class="material-symbols-outlined">${w.icon}</span>${w.label}`;

      item.addEventListener("dragstart", (e) => {
        state.dragType = w.type;
        state.dragNode = null;
        e.dataTransfer.effectAllowed = "copy";
        item.classList.add("dragging");
      });

      item.addEventListener("dragend", () => {
        state.dragType = null;
        item.classList.remove("dragging");
      });

      grid.appendChild(item);
    }

    cat.appendChild(grid);
    palette.appendChild(cat);
  }
}

// Widget search
function setupWidgetSearch() {
  const input = document.getElementById("widget-search");
  input.addEventListener("input", () => {
    const q = input.value.toLowerCase();
    const items = document.querySelectorAll(".widget-item");
    const cats = document.querySelectorAll(".widget-category");

    items.forEach((item) => {
      const match = item.dataset.type.toLowerCase().includes(q) || item.textContent.toLowerCase().includes(q);
      item.style.display = match ? "" : "none";
    });

    cats.forEach((cat) => {
      const visibleItems = cat.querySelectorAll('.widget-item:not([style*="display: none"])');
      cat.style.display = visibleItems.length ? "" : "none";
    });
  });
}

// ================================================================
// DRAG & DROP
// ================================================================

function handleDrop(targetId) {
  const tree = currentTree();
  if (!tree) return;

  if (state.dragType) {
    // Dropping a new widget from palette
    const def = WIDGET_DEFS[state.dragType];
    if (!def) return;

    saveSnapshot();
    const newNode = {
      id: uid(),
      type: state.dragType,
      properties: deepClone(def.defaultProps),
      children: [],
    };

    const target = findNodeById(tree, targetId);
    if (!target) return;
    const targetDef = WIDGET_DEFS[target.type];
    if (targetDef && targetDef.acceptsChildren) {
      target.children.push(newNode);
    } else {
      // Add as sibling
      const parent = findParent(tree, targetId);
      if (parent) {
        const idx = parent.children.findIndex((c) => c.id === targetId);
        parent.children.splice(idx + 1, 0, newNode);
      }
    }

    state.selectedId = newNode.id;
    state.dragType = null;
    render();
    autoSave();
  } else if (state.dragNode) {
    // Moving existing node
    const nodeId = state.dragNode;
    if (nodeId === targetId) return;

    // Prevent dropping into own descendants
    const node = findNodeById(tree, nodeId);
    if (findNodeById(node, targetId)) return;

    saveSnapshot();
    const nodeCopy = deepClone(node);
    removeNodeById(tree, nodeId);

    const target = findNodeById(tree, targetId);
    if (target) {
      const targetDef = WIDGET_DEFS[target.type];
      if (targetDef && targetDef.acceptsChildren) {
        target.children.push(nodeCopy);
      } else {
        const parent = findParent(tree, targetId);
        if (parent) {
          const idx = parent.children.findIndex((c) => c.id === targetId);
          parent.children.splice(idx + 1, 0, nodeCopy);
        }
      }
    }

    state.selectedId = nodeCopy.id;
    state.dragNode = null;
    render();
    autoSave();
  }
}

// Also allow dropping on the canvas root
function setupCanvasDrop() {
  const canvas = document.getElementById("canvas");
  canvas.addEventListener("dragover", (e) => {
    e.preventDefault();
  });
  canvas.addEventListener("drop", (e) => {
    e.preventDefault();
    const tree = currentTree();
    if (tree) {
      handleDrop(tree.id);
    } else if (state.dragType) {
      // Create root scaffold
      saveSnapshot();
      const def = WIDGET_DEFS[state.dragType];
      const newNode = {
        id: uid(),
        type: state.dragType,
        properties: deepClone(def.defaultProps),
        children: [],
      };
      const page = currentPage();
      if (page) {
        page.tree = {
          id: uid(),
          type: "Scaffold",
          properties: {},
          children: [newNode],
        };
        render();
        autoSave();
      }
    }
  });
}

// ================================================================
// WIDGET TREE PANEL
// ================================================================

function renderWidgetTree() {
  const container = document.getElementById("widget-tree");
  const tree = currentTree();
  container.innerHTML = "";
  if (!tree) {
    container.innerHTML = '<p class="hint">No widgets yet. Drag widgets to the canvas.</p>';
    return;
  }
  container.appendChild(renderTreeNode(tree, 0));
}

function renderTreeNode(node, depth) {
  const def = WIDGET_DEFS[node.type];
  const hasChildren = node.children && node.children.length > 0;

  const wrap = document.createElement("div");
  wrap.className = "tree-node";

  const header = document.createElement("div");
  header.className = "tree-node-header" + (state.selectedId === node.id ? " selected" : "");
  header.style.paddingLeft = (depth * 12 + 8) + "px";
  header.draggable = !def?.isRoot;

  // Toggle
  const toggle = document.createElement("span");
  toggle.className = "tree-node-toggle";
  toggle.textContent = hasChildren ? "▼" : "";
  header.appendChild(toggle);

  // Icon
  const icon = document.createElement("span");
  icon.className = "material-symbols-outlined tree-node-icon";
  icon.textContent = def?.icon || "widgets";
  icon.style.fontSize = "14px";
  header.appendChild(icon);

  // Name
  const name = document.createElement("span");
  name.className = "tree-node-name";
  name.textContent = node.type;
  header.appendChild(name);

  // Type hint
  const typeHint = document.createElement("span");
  typeHint.className = "tree-node-type";
  if (node.type === "Text") typeHint.textContent = `"${(node.properties.text || "").substring(0, 15)}"`;
  else if (node.type === "AppBar") typeHint.textContent = node.properties.title || "";
  header.appendChild(typeHint);

  // Actions
  const actions = document.createElement("div");
  actions.className = "tree-node-actions";

  if (!def?.isRoot) {
    const delBtn = document.createElement("button");
    delBtn.className = "tree-action";
    delBtn.innerHTML = '<span class="material-symbols-outlined">delete</span>';
    delBtn.title = "Delete";
    delBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      saveSnapshot();
      removeNodeById(currentTree(), node.id);
      if (state.selectedId === node.id) state.selectedId = null;
      render();
      autoSave();
    });
    actions.appendChild(delBtn);
  }

  header.appendChild(actions);

  // Select on click
  header.addEventListener("click", (e) => {
    e.stopPropagation();
    state.selectedId = node.id;
    render();
  });

  // Drag from tree
  header.addEventListener("dragstart", (e) => {
    state.dragNode = node.id;
    state.dragType = null;
    e.dataTransfer.effectAllowed = "move";
  });

  header.addEventListener("dragend", () => {
    state.dragNode = null;
  });

  wrap.appendChild(header);

  // Children
  if (hasChildren) {
    const childrenContainer = document.createElement("div");
    childrenContainer.className = "tree-node-children";

    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      childrenContainer.classList.toggle("collapsed");
      toggle.textContent = childrenContainer.classList.contains("collapsed") ? "▶" : "▼";
    });

    for (const child of node.children) {
      childrenContainer.appendChild(renderTreeNode(child, depth + 1));
    }
    wrap.appendChild(childrenContainer);
  }

  return wrap;
}

// ================================================================
// PROPERTIES EDITOR
// ================================================================

function renderProperties() {
  const container = document.getElementById("properties-editor");
  const tree = currentTree();

  if (!state.selectedId || !tree) {
    container.innerHTML = '<p class="hint">Select a widget to edit its properties</p>';
    return;
  }

  const node = findNodeById(tree, state.selectedId);
  if (!node) {
    container.innerHTML = '<p class="hint">Widget not found</p>';
    return;
  }

  const def = WIDGET_DEFS[node.type];
  if (!def) {
    container.innerHTML = '<p class="hint">Unknown widget type</p>';
    return;
  }

  container.innerHTML = "";

  // Title
  const title = document.createElement("div");
  title.className = "prop-widget-title";
  title.innerHTML = `<span class="material-symbols-outlined">${def.icon}</span> ${node.type}`;
  container.appendChild(title);

  if (!def.propertyDefs || !def.propertyDefs.length) {
    const hint = document.createElement("p");
    hint.className = "hint";
    hint.textContent = "No editable properties";
    container.appendChild(hint);
    return;
  }

  // Group properties by section
  const section = document.createElement("div");
  section.className = "prop-section";

  for (const propDef of def.propertyDefs) {
    const row = document.createElement("div");
    row.className = "prop-row";

    const label = document.createElement("span");
    label.className = "prop-label";
    label.textContent = propDef.label;
    row.appendChild(label);

    const inputWrap = document.createElement("div");
    inputWrap.className = "prop-input";

    const currentValue = node.properties[propDef.key] ?? "";

    if (propDef.type === "text") {
      const input = document.createElement("input");
      input.type = "text";
      input.value = currentValue;
      input.addEventListener("input", () => {
        saveSnapshot();
        node.properties[propDef.key] = input.value;
        render();
        autoSave();
      });
      inputWrap.appendChild(input);
    } else if (propDef.type === "number") {
      const input = document.createElement("input");
      input.type = "number";
      input.value = currentValue;
      if (propDef.min !== undefined) input.min = propDef.min;
      if (propDef.max !== undefined) input.max = propDef.max;
      if (propDef.step !== undefined) input.step = propDef.step;
      input.addEventListener("input", () => {
        saveSnapshot();
        node.properties[propDef.key] = input.value;
        render();
        autoSave();
      });
      inputWrap.appendChild(input);
    } else if (propDef.type === "select") {
      const select = document.createElement("select");
      for (const opt of propDef.options) {
        const option = document.createElement("option");
        option.value = opt;
        option.textContent = opt || "(none)";
        if (opt === currentValue) option.selected = true;
        select.appendChild(option);
      }
      select.addEventListener("change", () => {
        saveSnapshot();
        node.properties[propDef.key] = select.value;
        render();
        autoSave();
      });
      inputWrap.appendChild(select);
    } else if (propDef.type === "color") {
      inputWrap.className = "prop-input prop-input-color";
      const colorInput = document.createElement("input");
      colorInput.type = "color";
      colorInput.value = currentValue && currentValue.startsWith("#") ? currentValue : "#2196F3";
      const textInput = document.createElement("input");
      textInput.type = "text";
      textInput.value = currentValue;
      textInput.placeholder = "#hex or name";

      colorInput.addEventListener("input", () => {
        saveSnapshot();
        node.properties[propDef.key] = colorInput.value;
        textInput.value = colorInput.value;
        render();
        autoSave();
      });
      textInput.addEventListener("input", () => {
        saveSnapshot();
        node.properties[propDef.key] = textInput.value;
        render();
        autoSave();
      });
      inputWrap.appendChild(colorInput);
      inputWrap.appendChild(textInput);
    }

    row.appendChild(inputWrap);
    section.appendChild(row);
  }

  container.appendChild(section);

  // Show properties tab
  switchTab("properties");
}

// ================================================================
// TABS
// ================================================================

function switchTab(tabName) {
  document.querySelectorAll(".panel-tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === tabName);
  });
  document.getElementById("tab-tree").classList.toggle("hidden", tabName !== "tree");
  document.getElementById("tab-properties").classList.toggle("hidden", tabName !== "properties");
}

// ================================================================
// CODE GENERATION
// ================================================================

async function showCode() {
  if (!state.project) return;
  const res = await fetch(`/api/projects/${state.project.slug}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  const data = await res.json();
  document.getElementById("code-output").textContent = data.code || "// No code generated";
  document.getElementById("code-modal").classList.add("active");
}

function copyCode() {
  const code = document.getElementById("code-output").textContent;
  navigator.clipboard.writeText(code).then(() => {
    const btn = document.getElementById("btn-copy-code");
    btn.innerHTML = '<span class="material-symbols-outlined">check</span> Copied!';
    setTimeout(() => {
      btn.innerHTML = '<span class="material-symbols-outlined">content_copy</span> Copy';
    }, 2000);
  });
}

async function exportProject() {
  if (!state.project) return;
  window.location.href = `/api/projects/${state.project.slug}/export`;
}

// ================================================================
// THEME
// ================================================================

function showThemeEditor() {
  if (!state.project) return;
  const theme = state.project.theme || {};
  const primaryInput = document.getElementById("theme-primary");
  const brightnessSelect = document.getElementById("theme-brightness");

  const pc = theme.primaryColor || "#2196F3";
  primaryInput.value = pc.startsWith("#") ? pc : "#2196F3";
  brightnessSelect.value = theme.brightness || "light";

  document.getElementById("theme-modal").classList.add("active");
}

function applyTheme() {
  if (!state.project) return;
  saveSnapshot();
  state.project.theme = {
    primaryColor: document.getElementById("theme-primary").value,
    brightness: document.getElementById("theme-brightness").value,
  };
  document.getElementById("theme-modal").classList.remove("active");
  autoSave();
}

// ================================================================
// KEYBOARD SHORTCUTS
// ================================================================

function setupKeyboard() {
  document.addEventListener("keydown", (e) => {
    // Ctrl+Z / Cmd+Z = undo
    if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
      e.preventDefault();
      undo();
    }
    // Ctrl+Y / Cmd+Shift+Z = redo
    if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) {
      e.preventDefault();
      redo();
    }
    // Delete / Backspace = delete selected widget
    if ((e.key === "Delete" || e.key === "Backspace") && state.selectedId) {
      // Don't delete if in input
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
      const tree = currentTree();
      if (!tree) return;
      const node = findNodeById(tree, state.selectedId);
      if (!node) return;
      const def = WIDGET_DEFS[node.type];
      if (def?.isRoot) return;
      e.preventDefault();
      saveSnapshot();
      removeNodeById(tree, state.selectedId);
      state.selectedId = null;
      render();
      autoSave();
    }
  });
}

// ================================================================
// MODAL CLOSE
// ================================================================

function setupModals() {
  document.querySelectorAll(".modal-close").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modalId = btn.dataset.close;
      document.getElementById(modalId).classList.remove("active");
    });
  });

  // Close on overlay click
  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay && overlay.id !== "project-modal") {
        overlay.classList.remove("active");
      }
    });
  });
}

// ================================================================
// INIT
// ================================================================

function init() {
  // Button handlers
  document.getElementById("btn-create-project").addEventListener("click", createProject);
  document.getElementById("btn-back").addEventListener("click", exitBuilder);
  document.getElementById("btn-add-page").addEventListener("click", addPage);
  document.getElementById("btn-undo").addEventListener("click", undo);
  document.getElementById("btn-redo").addEventListener("click", redo);
  document.getElementById("btn-preview").addEventListener("click", showCode);
  document.getElementById("btn-export").addEventListener("click", exportProject);
  document.getElementById("btn-copy-code").addEventListener("click", copyCode);
  document.getElementById("btn-theme").addEventListener("click", showThemeEditor);
  document.getElementById("btn-apply-theme").addEventListener("click", applyTheme);

  // Enter key in project name input
  document.getElementById("new-project-name").addEventListener("keydown", (e) => {
    if (e.key === "Enter") createProject();
  });

  // Tabs
  document.querySelectorAll(".panel-tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  renderWidgetPalette();
  setupWidgetSearch();
  setupCanvasDrop();
  setupKeyboard();
  setupModals();
  loadProjects();
}

document.addEventListener("DOMContentLoaded", init);
