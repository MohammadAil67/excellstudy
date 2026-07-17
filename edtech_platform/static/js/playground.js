/**
 * Playground Canvas — ExcellStudy Agent Builder
 * Handles: drag-drop nodes, canvas interactions, SVG connections, config panel
 */

/* ------------------------------------------------------------------ */
/*  Node type definitions                                             */
/* ------------------------------------------------------------------ */
const NODE_TYPES = {
  'llm':       { label: 'LLM Call',        color: '#534AB7', icon: '🧠' },
  'tool':      { label: 'Tool',            color: '#1D9E75', icon: '🔧' },
  'condition': { label: 'Condition',        color: '#BA7517', icon: '🔀' },
  'memory':    { label: 'Memory',           color: '#6B7280', icon: '💾' },
  'human':     { label: 'Human Input',      color: '#E07B5E', icon: '👤' },
  'agent':     { label: 'Platform Agent',   color: '#1D9E75', icon: '🤖', outline: true }
};

/* ------------------------------------------------------------------ */
/*  PlaygroundCanvas                                                  */
/* ------------------------------------------------------------------ */
class PlaygroundCanvas {
  constructor(canvasElement) {
    this.canvas       = canvasElement;
    this.nodes        = new Map();
    this.connections   = [];
    this.selectedNode  = null;
    this.nodeIdCounter = 0;
    this.isConnecting  = false;
    this.connectionStart = null;
    this.svgLayer      = null;
    this._dragState    = null;          // internal drag bookkeeping
    this._tempLine     = null;          // rubber-band connection line

    this.init();
  }

  /* ---- bootstrap ---- */
  init() {
    this.setupSVGLayer();
    this.setupDropZone();
    this.setupPaletteDrag();
    this.setupCanvasClick();
  }

  /* ---- SVG overlay for connection lines ---- */
  setupSVGLayer() {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'playground-svg-layer');
    Object.assign(svg.style, {
      position: 'absolute', top: '0', left: '0',
      width: '100%', height: '100%',
      pointerEvents: 'none', zIndex: '0'
    });
    this.canvas.style.position = 'relative';
    this.canvas.insertBefore(svg, this.canvas.firstChild);
    this.svgLayer = svg;
  }

  /* ---- palette → canvas drag ---- */
  setupPaletteDrag() {
    document.querySelectorAll('[data-node-type]').forEach(el => {
      el.setAttribute('draggable', 'true');
      el.addEventListener('dragstart', e => {
        e.dataTransfer.setData('application/x-node-type', el.dataset.nodeType);
        e.dataTransfer.effectAllowed = 'copy';
      });
    });
  }

  /* ---- canvas drop zone ---- */
  setupDropZone() {
    this.canvas.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    });

    this.canvas.addEventListener('drop', e => {
      e.preventDefault();
      const type = e.dataTransfer.getData('application/x-node-type');
      if (!type || !NODE_TYPES[type]) return;

      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      this.createNode(type, x, y);
    });
  }

  /* ---- deselect on empty-canvas click ---- */
  setupCanvasClick() {
    this.canvas.addEventListener('mousedown', e => {
      if (e.target === this.canvas || e.target === this.svgLayer) {
        this.deselectAll();
        if (this.isConnecting) {
          this.cancelConnection();
        }
      }
    });
  }

  /* ================================================================ */
  /*  Node CRUD                                                       */
  /* ================================================================ */

  createNode(type, x, y) {
    const id = `node_${++this.nodeIdCounter}`;
    const meta = NODE_TYPES[type];
    const node = {
      id,
      type,
      x,
      y,
      config: this._defaultConfig(type),
      label: meta.label
    };
    this.nodes.set(id, node);
    this.renderNodeElement(node);
    this.selectNode(id);
    return node;
  }

  _defaultConfig(type) {
    switch (type) {
      case 'llm':       return { model: 'gpt-4o', temperature: 0.7, systemPrompt: '' };
      case 'tool':      return { toolName: '', parameters: '{}' };
      case 'condition': return { expression: '' };
      case 'memory':    return { memoryType: 'buffer', k: 5 };
      case 'human':     return { prompt: 'Provide input:' };
      case 'agent':     return { agentId: '' };
      default:          return {};
    }
  }

  /* ---- render a single node element ---- */
  renderNodeElement(node) {
    const meta = NODE_TYPES[node.type];
    const el = document.createElement('div');
    el.id = node.id;
    el.className = 'pg-node';
    el.style.cssText = `
      position:absolute; left:${node.x}px; top:${node.y}px;
      width:180px; border-radius:10px; background:#fff;
      box-shadow:0 2px 12px rgba(83,74,183,.1);
      border:2px solid ${meta.outline ? meta.color : 'transparent'};
      user-select:none; z-index:1; cursor:grab;
      font-family:'Inter',sans-serif; font-size:13px;
    `;

    /* header bar */
    const header = document.createElement('div');
    header.style.cssText = `
      background:${meta.color}; color:#fff; padding:8px 12px;
      border-radius:8px 8px 0 0; display:flex; align-items:center;
      justify-content:space-between; font-weight:600;
    `;
    header.innerHTML = `<span>${meta.icon} ${meta.label}</span>`;

    /* delete button */
    const del = document.createElement('button');
    del.textContent = '✕';
    del.title = 'Delete node';
    del.style.cssText = `
      background:none; border:none; color:rgba(255,255,255,.7);
      cursor:pointer; font-size:14px; line-height:1; padding:0 2px;
    `;
    del.addEventListener('click', e => { e.stopPropagation(); this.deleteNode(node.id); });
    header.appendChild(del);

    /* body */
    const body = document.createElement('div');
    body.style.cssText = 'padding:10px 12px; color:#6B7280; font-size:12px;';
    body.textContent = this._bodySummary(node);
    body.className = 'pg-node__body';

    /* ports */
    const portRow = document.createElement('div');
    portRow.style.cssText = 'display:flex; justify-content:space-between; padding:0 12px 8px;';

    const inPort  = this._createPort('in', node.id, meta.color);
    const outPort = this._createPort('out', node.id, meta.color);
    portRow.appendChild(inPort);
    portRow.appendChild(outPort);

    el.appendChild(header);
    el.appendChild(body);
    el.appendChild(portRow);

    el.addEventListener('mousedown', e => {
      if (e.target === del || e.target.classList.contains('pg-port')) return;
      this.selectNode(node.id);
    });

    this.canvas.appendChild(el);
    this.makeNodeDraggable(el, node);
  }

  _bodySummary(node) {
    switch (node.type) {
      case 'llm':       return `Model: ${node.config.model}`;
      case 'tool':      return node.config.toolName || 'No tool selected';
      case 'condition': return node.config.expression || 'No expression';
      case 'memory':    return `Type: ${node.config.memoryType}`;
      case 'human':     return node.config.prompt.slice(0, 30);
      case 'agent':     return node.config.agentId || 'Select agent';
      default:          return '';
    }
  }

  _createPort(direction, nodeId, color) {
    const port = document.createElement('div');
    port.className = `pg-port pg-port--${direction}`;
    port.dataset.nodeId = nodeId;
    port.dataset.direction = direction;
    port.title = direction === 'in' ? 'Input' : 'Output';
    port.style.cssText = `
      width:12px; height:12px; border-radius:50%;
      background:${direction === 'out' ? color : '#fff'};
      border:2px solid ${color}; cursor:crosshair;
    `;

    port.addEventListener('mousedown', e => {
      e.stopPropagation();
      if (direction === 'out') {
        this.startConnection(nodeId, port);
      }
    });

    port.addEventListener('mouseup', e => {
      e.stopPropagation();
      if (this.isConnecting && direction === 'in') {
        this.completeConnection(nodeId);
      }
    });

    return port;
  }

  /* ---- make a node draggable ---- */
  makeNodeDraggable(element, node) {
    let offsetX, offsetY;

    const onMouseMove = e => {
      const rect = this.canvas.getBoundingClientRect();
      let x = e.clientX - rect.left - offsetX;
      let y = e.clientY - rect.top  - offsetY;
      x = Math.max(0, Math.min(x, rect.width  - element.offsetWidth));
      y = Math.max(0, Math.min(y, rect.height - element.offsetHeight));
      element.style.left = x + 'px';
      element.style.top  = y + 'px';
      node.x = x;
      node.y = y;
      this.drawConnections();
    };

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      element.style.cursor = 'grab';
    };

    element.addEventListener('mousedown', e => {
      if (e.target.classList.contains('pg-port') || e.target.tagName === 'BUTTON') return;
      element.style.cursor = 'grabbing';
      const elRect = element.getBoundingClientRect();
      offsetX = e.clientX - elRect.left;
      offsetY = e.clientY - elRect.top;
      element.style.zIndex = 2;
      document.querySelectorAll('.pg-node').forEach(n => {
        if (n !== element) n.style.zIndex = 1;
      });
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    });
  }

  /* ================================================================ */
  /*  Selection                                                       */
  /* ================================================================ */
  selectNode(nodeId) {
    this.deselectAll();
    this.selectedNode = nodeId;
    const el = document.getElementById(nodeId);
    if (el) {
      el.style.outline = '2px solid #534AB7';
      el.style.outlineOffset = '2px';
    }
    const node = this.nodes.get(nodeId);
    if (node) this.updateConfigPanel(node);
  }

  deselectAll() {
    if (this.selectedNode) {
      const prev = document.getElementById(this.selectedNode);
      if (prev) { prev.style.outline = 'none'; prev.style.outlineOffset = '0'; }
    }
    this.selectedNode = null;
    const panel = document.getElementById('config-panel');
    if (panel) {
      panel.innerHTML = '<p style="color:#9CA3AF;text-align:center;padding:40px 16px;">Select a node to configure</p>';
    }
  }

  /* ---- config panel ---- */
  updateConfigPanel(node) {
    const panel = document.getElementById('config-panel');
    if (!panel) return;

    const meta = NODE_TYPES[node.type];
    let html = `<div style="padding:16px;">
      <h4 style="margin:0 0 16px;font-size:14px;color:#1A1A2E;">
        ${meta.icon} ${meta.label} Config
      </h4>`;

    switch (node.type) {
      case 'llm':
        html += this._field('Model', `<select class="input" data-cfg="model">
          ${['gpt-4o','gpt-4o-mini','claude-3.5-sonnet','gemini-1.5-pro']
            .map(m => `<option value="${m}"${node.config.model===m?' selected':''}>${m}</option>`).join('')}
        </select>`);
        html += this._field('Temperature', `<input type="range" min="0" max="2" step="0.1"
          value="${node.config.temperature}" data-cfg="temperature" style="width:100%">
          <span class="cfg-temp-val" style="font-size:12px;color:#6B7280;">${node.config.temperature}</span>`);
        html += this._field('System Prompt', `<textarea class="input" rows="3"
          data-cfg="systemPrompt" placeholder="You are a helpful assistant...">${node.config.systemPrompt}</textarea>`);
        break;

      case 'tool':
        html += this._field('Tool Name', `<input class="input" data-cfg="toolName"
          value="${node.config.toolName}" placeholder="e.g. web_search">`);
        html += this._field('Parameters (JSON)', `<textarea class="input" rows="3"
          data-cfg="parameters" placeholder='{"key": "value"}'>${node.config.parameters}</textarea>`);
        break;

      case 'condition':
        html += this._field('Expression', `<input class="input" data-cfg="expression"
          value="${node.config.expression}" placeholder="output.score > 0.8">`);
        break;

      case 'memory':
        html += this._field('Memory Type', `<select class="input" data-cfg="memoryType">
          ${['buffer','summary','vector','conversation']
            .map(m => `<option value="${m}"${node.config.memoryType===m?' selected':''}>${m}</option>`).join('')}
        </select>`);
        html += this._field('Window (k)', `<input type="number" class="input" data-cfg="k"
          value="${node.config.k}" min="1" max="50">`);
        break;

      case 'human':
        html += this._field('Prompt', `<textarea class="input" rows="2"
          data-cfg="prompt">${node.config.prompt}</textarea>`);
        break;

      case 'agent':
        html += this._field('Agent ID', `<input class="input" data-cfg="agentId"
          value="${node.config.agentId}" placeholder="agent_abc123">`);
        break;
    }

    html += `<button class="btn btn--danger btn--sm" style="margin-top:16px;width:100%"
      id="cfg-delete-btn">Delete Node</button></div>`;

    panel.innerHTML = html;

    /* bind change listeners */
    panel.querySelectorAll('[data-cfg]').forEach(input => {
      const key = input.dataset.cfg;
      const handler = () => {
        node.config[key] = input.type === 'range' ? parseFloat(input.value) : input.value;
        /* refresh body summary */
        const body = document.querySelector(`#${node.id} .pg-node__body`);
        if (body) body.textContent = this._bodySummary(node);
        /* temperature label */
        if (key === 'temperature') {
          const lbl = panel.querySelector('.cfg-temp-val');
          if (lbl) lbl.textContent = input.value;
        }
      };
      input.addEventListener('input', handler);
      input.addEventListener('change', handler);
    });

    const delBtn = document.getElementById('cfg-delete-btn');
    if (delBtn) delBtn.addEventListener('click', () => this.deleteNode(node.id));
  }

  _field(label, inputHtml) {
    return `<div style="margin-bottom:12px;">
      <label style="display:block;font-size:12px;font-weight:500;margin-bottom:4px;color:#1A1A2E;">${label}</label>
      ${inputHtml}
    </div>`;
  }

  /* ================================================================ */
  /*  Connections                                                      */
  /* ================================================================ */
  startConnection(nodeId, portElement) {
    this.isConnecting = true;
    this.connectionStart = { nodeId, portElement };
    this.canvas.style.cursor = 'crosshair';

    const onMove = e => {
      if (!this.isConnecting) return;
      const rect = this.canvas.getBoundingClientRect();
      const portRect = portElement.getBoundingClientRect();
      const x1 = portRect.left + portRect.width / 2  - rect.left;
      const y1 = portRect.top  + portRect.height / 2 - rect.top;
      const x2 = e.clientX - rect.left;
      const y2 = e.clientY - rect.top;
      this._drawTempLine(x1, y1, x2, y2);
    };

    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      this.cancelConnection();
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }

  completeConnection(targetNodeId) {
    if (!this.connectionStart) return;
    const sourceId = this.connectionStart.nodeId;
    if (sourceId === targetNodeId) { this.cancelConnection(); return; }

    /* prevent duplicates */
    const exists = this.connections.some(c => c.from === sourceId && c.to === targetNodeId);
    if (!exists) {
      this.connections.push({ from: sourceId, to: targetNodeId });
    }

    this.cancelConnection();
    this.drawConnections();
  }

  cancelConnection() {
    this.isConnecting = false;
    this.connectionStart = null;
    this.canvas.style.cursor = 'default';
    if (this._tempLine) { this._tempLine.remove(); this._tempLine = null; }
  }

  /* ---- SVG rendering ---- */
  drawConnections() {
    /* clear all current paths */
    while (this.svgLayer.firstChild) this.svgLayer.removeChild(this.svgLayer.firstChild);

    const canvasRect = this.canvas.getBoundingClientRect();

    this.connections.forEach(conn => {
      const fromEl = document.querySelector(`#${conn.from} .pg-port--out`);
      const toEl   = document.querySelector(`#${conn.to} .pg-port--in`);
      if (!fromEl || !toEl) return;

      const fromRect = fromEl.getBoundingClientRect();
      const toRect   = toEl.getBoundingClientRect();

      const x1 = fromRect.left + fromRect.width / 2  - canvasRect.left;
      const y1 = fromRect.top  + fromRect.height / 2 - canvasRect.top;
      const x2 = toRect.left   + toRect.width / 2    - canvasRect.left;
      const y2 = toRect.top    + toRect.height / 2   - canvasRect.top;

      const color = NODE_TYPES[this.nodes.get(conn.from)?.type]?.color || '#534AB7';
      this.drawBezierPath(x1, y1, x2, y2, color);
    });
  }

  drawBezierPath(x1, y1, x2, y2, color) {
    const dx = Math.abs(x2 - x1) * 0.5;
    const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', d);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', color);
    path.setAttribute('stroke-width', '2');
    path.setAttribute('stroke-linecap', 'round');
    path.style.pointerEvents = 'none';
    this.svgLayer.appendChild(path);
  }

  _drawTempLine(x1, y1, x2, y2) {
    if (this._tempLine) this._tempLine.remove();
    const dx = Math.abs(x2 - x1) * 0.5;
    const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', d);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#534AB7');
    path.setAttribute('stroke-width', '2');
    path.setAttribute('stroke-dasharray', '6 4');
    path.setAttribute('stroke-linecap', 'round');
    path.style.pointerEvents = 'none';
    this.svgLayer.appendChild(path);
    this._tempLine = path;
  }

  /* ================================================================ */
  /*  Delete                                                          */
  /* ================================================================ */
  deleteNode(nodeId) {
    const el = document.getElementById(nodeId);
    if (el) el.remove();
    this.nodes.delete(nodeId);
    this.connections = this.connections.filter(c => c.from !== nodeId && c.to !== nodeId);
    if (this.selectedNode === nodeId) this.deselectAll();
    this.drawConnections();
  }

  /* ================================================================ */
  /*  Import / Export                                                  */
  /* ================================================================ */
  exportCanvas() {
    return JSON.stringify({
      nodes: Array.from(this.nodes.values()),
      connections: this.connections
    }, null, 2);
  }

  importCanvas(data) {
    /* clear existing */
    this.nodes.forEach((_, id) => { const el = document.getElementById(id); if (el) el.remove(); });
    this.nodes.clear();
    this.connections = [];
    this.selectedNode = null;
    while (this.svgLayer.firstChild) this.svgLayer.removeChild(this.svgLayer.firstChild);

    const parsed = typeof data === 'string' ? JSON.parse(data) : data;

    /* determine highest id to keep counter in sync */
    let maxId = 0;
    (parsed.nodes || []).forEach(n => {
      const num = parseInt(n.id.replace('node_', ''), 10);
      if (num > maxId) maxId = num;
    });
    this.nodeIdCounter = maxId;

    /* recreate nodes */
    (parsed.nodes || []).forEach(n => {
      this.nodes.set(n.id, n);
      this.renderNodeElement(n);
    });

    /* recreate connections */
    this.connections = parsed.connections || [];
    this.drawConnections();
  }
}

/* ------------------------------------------------------------------ */
/*  ConsoleStream — WebSocket output viewer                           */
/* ------------------------------------------------------------------ */
class ConsoleStream {
  constructor(outputElement, sessionId) {
    this.output    = outputElement;
    this.sessionId = sessionId;
    this.ws        = null;
  }

  connect() {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${protocol}://${location.host}/ws/playground/${this.sessionId}/console/`;

    this.ws = new WebSocket(url);

    this.ws.addEventListener('open', () => {
      this.appendOutput('⚡ Connected to console\n', 'system');
    });

    this.ws.addEventListener('message', e => {
      try {
        const msg = JSON.parse(e.data);
        this.appendOutput(msg.text + '\n', msg.type || 'stdout');
      } catch {
        this.appendOutput(e.data + '\n', 'stdout');
      }
    });

    this.ws.addEventListener('close', () => {
      this.appendOutput('🔌 Disconnected\n', 'system');
    });

    this.ws.addEventListener('error', () => {
      this.appendOutput('❌ Connection error\n', 'stderr');
    });
  }

  appendOutput(text, type) {
    if (!this.output) return;
    const span = document.createElement('span');
    span.textContent = text;
    const colors = {
      stdout: '#E0DEF4',
      stderr: '#F07070',
      system: '#25C290'
    };
    span.style.color = colors[type] || colors.stdout;
    this.output.appendChild(span);
    this.output.scrollTop = this.output.scrollHeight;
  }

  clear() {
    if (this.output) this.output.innerHTML = '';
  }
}

/* ------------------------------------------------------------------ */
/*  Bootstrap                                                         */
/* ------------------------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('playground-canvas');
  if (canvas) {
    window.playground = new PlaygroundCanvas(canvas);
  }

  const consoleEl = document.getElementById('playground-console-output');
  const sessionId = consoleEl?.dataset?.sessionId;
  if (consoleEl && sessionId) {
    window.consoleStream = new ConsoleStream(consoleEl, sessionId);
    window.consoleStream.connect();
  }

  /* Export / Import buttons */
  const exportBtn = document.getElementById('playground-export-btn');
  if (exportBtn && window.playground) {
    exportBtn.addEventListener('click', () => {
      const json = window.playground.exportCanvas();
      const blob = new Blob([json], { type: 'application/json' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url;
      a.download = 'agent_graph.json';
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  const importBtn = document.getElementById('playground-import-btn');
  if (importBtn && window.playground) {
    importBtn.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json';
      input.addEventListener('change', () => {
        const file = input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => window.playground.importCanvas(reader.result);
        reader.readAsText(file);
      });
      input.click();
    });
  }
});
