const form = document.getElementById('query-form');
const input = document.getElementById('query-input');
const streamBody = document.getElementById('stream-body');
const resultsBody = document.getElementById('results-body');
const resultsFooter = document.getElementById('results-footer');
const loadingIndicator = document.getElementById('loading-indicator');

// Toolbar controls
const selectAllEl = document.getElementById('select-all');
const applyBtn = document.getElementById('apply-selected');
const saveBtn = document.getElementById('save-selected');
const downloadBtn = document.getElementById('download-csv');
const filterSavedEl = document.getElementById('filter-saved');

let currentOps = [];
const selectedIds = new Set();
const savedIds = new Set();

function getOpId(op) {
  return `${(op.title || '').trim().toLowerCase()}|${(op.source || '').trim().toLowerCase()}`;
}

function setLoading(isLoading) {
  const container = document.getElementById('progress-stream');
  if (isLoading) {
    container.classList.add('is-loading');
    loadingIndicator.setAttribute('aria-busy', 'true');
  } else {
    container.classList.remove('is-loading');
    loadingIndicator.setAttribute('aria-busy', 'false');
  }
}

function addStep(node, text) {
  const wrap = document.createElement('div');
  wrap.className = 'step-item';
  const nodeEl = document.createElement('div');
  nodeEl.className = 'step-node';
  nodeEl.textContent = `Node: ${node}`;
  const textEl = document.createElement('div');
  textEl.className = 'step-text';
  textEl.textContent = text;
  wrap.appendChild(nodeEl);
  wrap.appendChild(textEl);
  streamBody.appendChild(wrap);
  streamBody.scrollTop = streamBody.scrollHeight;
}

function feedback(msg) {
  resultsFooter.textContent = msg;
}

function renderResults(opportunities) {
  currentOps = Array.isArray(opportunities) ? opportunities.slice() : [];
  resultsBody.innerHTML = '';

  const filtered = filterSavedEl && filterSavedEl.checked
    ? currentOps.filter(op => savedIds.has(getOpId(op)))
    : currentOps;

  filtered.forEach((op, idx) => {
    const id = getOpId(op) || `op-${idx}`;
    const card = document.createElement('div');
    card.className = 'op-card';

    const header = document.createElement('div');
    header.className = 'op-header';

    const title = document.createElement('h3');
    title.className = 'op-title';
    title.textContent = op.title || 'Untitled';

    const actions = document.createElement('div');
    actions.className = 'op-actions';

    const selectWrap = document.createElement('label');
    selectWrap.className = 'op-select';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = selectedIds.has(id);
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) selectedIds.add(id); else selectedIds.delete(id);
      updateToolbarCounts();
    });
    selectWrap.appendChild(checkbox);
    selectWrap.appendChild(document.createTextNode('Select'));

    const savedMark = document.createElement('span');
    savedMark.className = 'op-saved';
    savedMark.textContent = savedIds.has(id) ? 'Saved' : '';

    const score = document.createElement('div');
    score.className = 'op-score';
    score.textContent = `Score: ${typeof op.score === 'number' ? Math.round(op.score) : '-'}`;

    actions.appendChild(selectWrap);
    actions.appendChild(savedMark);
    actions.appendChild(score);

    header.appendChild(title);
    header.appendChild(actions);

    const summary = document.createElement('p');
    summary.className = 'op-summary';
    summary.textContent = op.summary || '';

    const source = document.createElement('div');
    source.className = 'op-source';
    if (op.source) {
      const link = document.createElement('a');
      link.className = 'op-link';
      link.href = op.source;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = op.source;
      source.appendChild(document.createTextNode('Source: '));
      source.appendChild(link);
    }

    card.appendChild(header);
    card.appendChild(summary);
    card.appendChild(source);

    resultsBody.appendChild(card);
  });

  updateToolbarCounts();
}

function updateToolbarCounts() {
  const count = currentOps.length;
  const sel = selectedIds.size;
  feedback(sel ? `${sel} selected of ${count}` : `${count} results`);
  if (selectAllEl) {
    const allIds = new Set(currentOps.map(getOpId));
    let allSelected = true;
    for (const id of allIds) if (!selectedIds.has(id)) { allSelected = false; break; }
    selectAllEl.checked = allSelected && count > 0;
  }
}

function downloadCSV() {
  const rows = [["title","summary","source","score"]];
  const filtered = filterSavedEl && filterSavedEl.checked
    ? currentOps.filter(op => savedIds.has(getOpId(op)))
    : currentOps;
  filtered.forEach(op => {
    const r = [op.title||'', op.summary||'', op.source||'', typeof op.score==='number'?String(op.score):''];
    rows.push(r.map(v => '"' + String(v).replace(/"/g,'""') + '"'));
  });
  const csv = rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'opportunities.csv';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function applySelected() {
  const ids = Array.from(selectedIds);
  if (!ids.length) { feedback('No selections.'); return; }
  let opened = 0;
  ids.forEach(id => {
    const op = currentOps.find(o => getOpId(o) === id);
    if (op && op.source) {
      opened += 1;
      setTimeout(() => window.open(op.source, '_blank', 'noopener,noreferrer'), 0);
    }
  });
  feedback(`${opened} opportunities opened (pop-up blocker may limit).`);
}

function saveSelected() {
  const ids = Array.from(selectedIds);
  if (!ids.length) { feedback('No selections.'); return; }
  ids.forEach(id => savedIds.add(id));
  feedback(`${ids.length} opportunities saved.`);
  renderResults(currentOps);
}

// Wire toolbar events
if (downloadBtn) downloadBtn.addEventListener('click', downloadCSV);
if (applyBtn) applyBtn.addEventListener('click', applySelected);
if (saveBtn) saveBtn.addEventListener('click', saveSelected);
if (filterSavedEl) filterSavedEl.addEventListener('change', () => renderResults(currentOps));
if (selectAllEl) selectAllEl.addEventListener('change', () => {
  const ids = currentOps.map(getOpId);
  if (selectAllEl.checked) ids.forEach(id => selectedIds.add(id)); else ids.forEach(id => selectedIds.delete(id));
  renderResults(currentOps);
});

function connectWS(query) {
  streamBody.innerHTML = '';
  resultsBody.innerHTML = '';
  resultsFooter.textContent = '';
  selectedIds.clear();
  setLoading(true);

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws?q=${encodeURIComponent(query)}`);

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'ack') {
        addStep('init', `Started: ${msg.query}`);
        return;
      }
      if (msg.type === 'error') {
        addStep('error', msg.message || 'Unknown error');
        setLoading(false);
        return;
      }
      if (msg.type === 'step') {
        const node = msg.node;
        const state = msg.state || {};
        const steps = state.steps || [];
        const last = steps[steps.length - 1] || 'Updated';
        addStep(node, last);
        if (state.opportunities) {
          renderResults(state.opportunities);
        }
        return;
      }
      if (msg.type === 'final') {
        const final = msg.state || {};
        if (final.opportunities) {
          renderResults(final.opportunities);
        }
        addStep('done', 'Completed');
        setLoading(false);
        ws.close();
        return;
      }
    } catch (e) {
      addStep('parse', 'Failed to parse message');
      setLoading(false);
    }
  };

  ws.onerror = () => { addStep('socket', 'WebSocket error'); setLoading(false); };
  ws.onclose = () => { setLoading(false); };
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  connectWS(q);
});
