'use strict';

const get = id => document.getElementById(id);
const hex = (value, width = 4) => value.toString(16).toUpperCase().padStart(width, '0');
const source = get('source');
const history = [];
let state, selected, busy = false, running = false, dirty = false;

function values(id, entries) {
  get(id).replaceChildren(...entries.map(([name, value, changed]) => {
    const item = document.createElement('div');
    const label = document.createElement('dt');
    const data = document.createElement('dd');
    label.textContent = name;
    data.textContent = changed ? value + '*' : value;
    item.classList.toggle('changed', Boolean(changed));
    item.append(label, data);
    return item;
  }));
}

function renderProcessor() {
  const step = selected ?? history.at(-1);
  const previous = history[(step?.number ?? 1) - (history[0]?.number ?? 1) - 1];
  const word = step?.ir ?? state.ir;
  values('control', [['Шаг', step?.number ?? state.count], ['PC', hex(step?.pc ?? state.pc)], ['IR', hex(word, 8)]]);
  get('command').textContent = step ? hex(step.address) + '  ' + step.command : 'Команда ещё не выполнена';
  values('fields', [
    ['OPCODE', hex(word >>> 28, 1)], ['MODE1', ((word >>> 26) & 3).toString(2).padStart(2, '0')],
    ['OP1', hex((word >>> 22) & 15, 1)], ['MODE2', ((word >>> 20) & 3).toString(2).padStart(2, '0')],
    ['OP2', hex((word >>> 16) & 15, 1)], ['PAYLOAD', hex(word & 65535)],
  ]);
  values('registers', (step?.registers ?? state.registers).map((value, i) => [
    state.register_names[i], hex(value), value !== (previous?.registers[i] ?? 0),
  ]));
  values('flags', (step?.flags ?? state.flags).map((value, i) => [
    ['ZF', 'CF', 'SF'][i], Number(value), value !== (previous?.flags[i] ?? false),
  ]));
  const write = step?.write;
  get('write').textContent = write
    ? `Запись ОЗУ [${hex(write[0])}]: ${hex(write[1])} → ${hex(write[2])}`
    : 'Записей в ОЗУ за шаг нет';
  get('latest').disabled = !selected;
}

function renderMemory() {
  const start = state.memory_start;
  const write = history.at(-1)?.write;
  get('range').textContent = `Текущее ОЗУ · ${hex(start)}–${hex(start + state.memory.length - 1)}`;
  get('memory').replaceChildren();
  for (let i = 0; i < state.memory.length; i += 16) {
    get('memory').append(hex(start + i) + '  ');
    state.memory.slice(i, i + 16).forEach((byte, j) => {
      const address = start + i + j;
      const text = hex(byte, 2);
      if (write && (address === write[0] || address === write[0] + 1)) {
        const mark = document.createElement('mark');
        mark.textContent = text;
        get('memory').append(mark, ' ');
      } else {
        get('memory').append(text + ' ');
      }
    });
    get('memory').append('\n');
  }
}

function selectStep(step) {
  selected = step;
  get('trace').querySelector('.selected')?.classList.remove('selected');
  if (step) get('trace').children[step.number - history[0].number].classList.add('selected');
  renderProcessor();
}

function addTrace(steps) {
  const fragment = document.createDocumentFragment();
  for (const step of steps) {
    history.push(step);
    const row = document.createElement('tr');
    const button = document.createElement('button');
    button.textContent = step.number;
    button.onclick = () => selectStep(step);
    row.insertCell().append(button);
    for (const text of [hex(step.address), step.command, hex(step.pc)]) {
      row.insertCell().textContent = text;
    }
    fragment.append(row);
  }
  get('trace').append(fragment);
  if (steps.length && !selected) {
    const panel = get('trace').closest('.trace');
    panel.scrollTop = panel.scrollHeight;
  }
}

function controls() {
  const locked = busy || running;
  for (const id of ['source', 'choose', 'example', 'load', 'address', 'symbols']) {
    get(id).disabled = locked;
  }
  for (const id of ['step', 'run']) {
    get(id).disabled = locked || dirty || !state?.loaded || state.halted;
  }
  get('prev').disabled = locked || !state?.memory_start;
  get('next').disabled = locked || !state || state.memory_start + state.memory.length >= 65536;
  get('stop').hidden = !running;
  get('status').textContent = running ? 'Выполняется…' : dirty
    ? 'Загрузите отредактированный код в ОЗУ.'
    : state?.halted ? `HALT · выполнено команд: ${state.count}`
    : state?.loaded ? `Выполнено команд: ${state.count}` : 'Загрузите программу для выполнения.';
}

function showError(message = '') {
  get('error').textContent = message;
  get('error').hidden = !message;
}

async function request(action, address = state?.memory_start ?? 0) {
  const response = await fetch('/api', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({action, address, source: action === 'load' ? source.value : undefined}),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error);
  state = data;
  if (action === 'load') {
    dirty = false;
    selected = undefined;
    history.length = 0;
    get('trace').replaceChildren();
  }
  if (action === 'load' || get('symbols').options.length === 1) {
    get('symbols').replaceChildren(new Option('Метки', ''));
    for (const [name, location] of Object.entries(state.symbols)) {
      get('symbols').add(new Option(`${name} · ${hex(location)}`, location));
    }
  }
  addTrace(state.trace);
  renderProcessor();
  renderMemory();
  if (state.error) throw new Error(state.error);
}

async function perform(action, address) {
  if (busy || running) return;
  busy = true;
  running = action === 'run';
  controls();
  showError();
  try {
    do {
      await request(action, address);
    } while (running && !state.halted);
  } catch (error) {
    showError(error.message);
  } finally {
    running = busy = false;
    controls();
  }
}

function edited() {
  dirty = true;
  showError();
  controls();
}

async function readFile(file) {
  if (!file || busy || running) return;
  try {
    source.value = await file.text();
    edited();
  } catch (error) {
    showError(error.message);
  }
}

function goTo(address) {
  if (!Number.isInteger(address) || address < 0 || address > 65535) {
    showError('Введите шестнадцатеричный адрес от 0000 до FFFF.');
    return;
  }
  get('address').value = hex(address);
  perform('memory', address);
}

get('theme').onclick = () => {
  const dark = document.documentElement.dataset.theme !== 'dark';
  setTheme(dark);
  localStorage.setItem('theme', dark ? 'dark' : 'light');
};
function setTheme(dark) {
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  get('theme').textContent = dark ? 'Светлая тема' : 'Тёмная тема';
  get('theme').setAttribute('aria-pressed', String(dark));
}
setTheme(localStorage.getItem('theme') === 'dark');

source.oninput = edited;
get('choose').onclick = () => get('file').click();
get('file').onchange = event => {
  readFile(event.target.files[0]);
  event.target.value = '';
};
source.ondragover = event => {
  event.preventDefault();
  source.classList.add('drag');
};
source.ondragleave = () => source.classList.remove('drag');
source.ondrop = event => {
  event.preventDefault();
  source.classList.remove('drag');
  readFile(event.dataTransfer.files[0]);
};
get('example').onchange = async event => {
  const path = event.target.value;
  if (!path) return;
  try {
    const response = await fetch(path);
    if (!response.ok) throw new Error('Не удалось открыть пример.');
    source.value = await response.text();
    edited();
  } catch (error) {
    showError(error.message);
  } finally {
    event.target.value = '';
  }
};
get('load').onclick = () => {
  get('address').value = '0000';
  perform('load', 0);
};
get('step').onclick = () => perform('step');
get('run').onclick = () => perform('run');
get('stop').onclick = () => {
  running = false;
  controls();
};
get('latest').onclick = () => selectStep(undefined);
get('memory-form').onsubmit = event => {
  event.preventDefault();
  const text = get('address').value.trim().replace(/^0x/i, '');
  goTo(/^[0-9a-f]{1,4}$/i.test(text) ? parseInt(text, 16) : NaN);
};
get('prev').onclick = () => goTo(state.memory_start - state.memory.length);
get('next').onclick = () => goTo(state.memory_start + state.memory.length);
get('symbols').onchange = event => {
  if (event.target.value !== '') goTo(Number(event.target.value));
  event.target.value = '';
};
perform('memory');
