const token = localStorage.getItem('token');
if (!token) location.href = 'login.html';
document.getElementById('usuario').innerText = localStorage.getItem('usuario') || '';
function sair() { localStorage.clear(); location.href = 'login.html'; }
function auth() { return { 'Authorization': 'Bearer ' + token }; }
function erro(msg) {
  const a = document.getElementById('alerta-erro');
  a.textContent = msg; a.classList.remove('d-none');
  setTimeout(() => a.classList.add('d-none'), 5000);
}

const mapa = L.map('mapa').setView([-6.4325, -50.0790], 11);
// Base rua (OSM) + satélite (Esri World Imagery, estilo Google Maps) + rótulos
const baseRua = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '&copy; OpenStreetMap'});
const baseSatelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {maxZoom: 19, attribution: 'Esri World Imagery'});
const rotulosSatelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {maxZoom: 19, opacity: 0.9});
const satComRotulos = L.layerGroup([baseSatelite, rotulosSatelite]);
baseSatelite.addTo(mapa); rotulosSatelite.addTo(mapa); // satélite como padrão (igual Maps)
L.control.layers({'Rua': baseRua, 'Satélite': satComRotulos}, null, {position: 'topright'}).addTo(mapa);
let camDesmate = null, camBuffers = null, camMina = null, chart = null;
const CORES = { mineracao: '#d62728', pastagem: '#ff9f1c', outros: '#6c757d' };
let SERIE = [], RESUMO = null;

async function api(path) {
  const r = await fetch(path, {headers: auth()});
  if (r.status === 401) { sair(); throw new Error('Sessão expirada'); }
  if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.erro || ('HTTP ' + r.status)); }
  return r.json();
}

async function base() {
  try {
    const [mina, buffers] = await Promise.all([api('/api/mina'), api('/api/buffers')]);
    if (camMina) mapa.removeLayer(camMina);
    if (camBuffers) mapa.removeLayer(camBuffers);
    camMina = L.geoJSON(mina, {pointToLayer: (f, ll) =>
      L.marker(ll).bindPopup(`<b>${f.properties.nome}</b><br>${f.properties.municipio}<br>${f.properties.substancia}`)}).addTo(mapa);
    camBuffers = L.geoJSON(buffers, {style: f => ({
      color: f.properties.raio_km === 1 ? '#198754' : f.properties.raio_km === 5 ? '#0d6efd' : '#adb5bd',
      weight: 2, dashArray: f.properties.raio_km === 10 ? '6 4' : null, fillOpacity: 0.05}) ,
      onEachFeature: (f, l) => l.bindPopup(`<b>Buffer ${f.properties.raio_km} km</b><br>${f.properties.area_ha} ha`)}).addTo(mapa);
    RESUMO = await api('/api/resumo');
    pintaResumo();
    await Promise.all([recarregar(), mostrarSerie()]);
  } catch (e) { erro('Falha ao carregar base: ' + e.message); }
}

function pintaResumo() {
  const ul = document.getElementById('lista-resumo');
  ul.innerHTML = '';
  const addItem = (texto, badge, badgeClass) => {
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex justify-content-between';
    li.textContent = texto;
    const span = document.createElement('span');
    span.className = 'badge ' + badgeClass;
    span.textContent = badge;
    li.appendChild(span);
    ul.appendChild(li);
  };
  RESUMO.por_ano.forEach(a => addItem(String(a.ano), `${a.ha} ha · ${a.patches}`, 'bg-secondary'));
  RESUMO.por_classe.forEach(c => addItem(c.classe, `${c.ha} ha`, 'bg-dark'));
}

function centroidLatLng(feature) {
  const g = feature.geometry;
  let ring = null;
  if (g.type === 'Polygon') ring = g.coordinates[0];
  else if (g.type === 'MultiPolygon') ring = g.coordinates[0][0];
  else if (g.type === 'Point') return L.latLng(g.coordinates[1], g.coordinates[0]);
  if (!ring || !ring.length) return null;
  let sumLon = 0, sumLat = 0;
  for (const c of ring) { sumLon += c[0]; sumLat += c[1]; }
  return L.latLng(sumLat / ring.length, sumLon / ring.length);
}
function raioCirculo(areaHa) {
  const r = Math.sqrt(parseFloat(areaHa) || 1) * 1.1;
  return Math.max(5, Math.min(16, r));
}

async function recarregar() {
  try {
    const ano = document.getElementById('f-ano').value;
    const classe = document.getElementById('f-classe').value;
    const buffer = document.getElementById('f-buffer').value;
    let url = '/api/desmate?limite=2000';
    if (ano) url += '&ano=' + ano;
    if (classe) url += '&classe=' + classe;
    if (buffer) url += '&buffer=' + buffer;
    const data = await api(url);
    if (camDesmate) mapa.removeLayer(camDesmate);
    camDesmate = L.layerGroup().addTo(mapa);
    const feats = data.features || [];
    const mineracao = feats.filter(f => f.properties.classe === 'mineracao');
    const outros = feats.filter(f => f.properties.classe !== 'mineracao');
    if (mineracao.length) {
      const geoMine = {type:'FeatureCollection', features: mineracao};
      L.geoJSON(geoMine, {
        style: {color:'#ff3b30', weight:2, opacity:0.95, fillColor:'#d62728', fillOpacity:0.78},
        onEachFeature: (f, l) => l.bindPopup(`<b>${f.properties.classe}</b> · ${f.properties.ano}<br>${f.properties.area_ha} ha · ${f.properties.fonte}<br><span class="small text-muted">área única recortada da cava</span>`)
      }).addTo(camDesmate);
    }
    outros.forEach(f => {
      const ll = centroidLatLng(f);
      if (!ll) return;
      const cor = CORES[f.properties.classe] || '#6c757d';
      const r = raioCirculo(f.properties.area_ha);
      L.circleMarker(ll, {radius:r, color:cor, weight:2, opacity:0.9, fillColor:cor, fillOpacity:0.42}).bindPopup(`<b>${f.properties.classe}</b> · ${f.properties.ano}<br>${f.properties.area_ha} ha · ${f.properties.fonte}<br><span class="small text-muted">centróide do polígono MapBiomas</span>`).addTo(camDesmate);
    });
    if (camBuffers) camBuffers.bringToBack();
    document.getElementById('contador').innerText = feats.length;
    const ha = feats.reduce((s, f) => s + (parseFloat(f.properties.area_ha) || 0), 0);
    document.getElementById('kpi-ha').innerText = ha.toFixed(1) + ' ha';
    // mostra tamanho da mina do ano selecionado no proprio mapa
    const mineFeat = feats.find(f => f.properties.classe === 'mineracao');
    if (mineFeat) {
      const lbl = mineFeat.properties.ano + ' · ' + mineFeat.properties.area_ha + ' ha';
      if (!window._mineLabel) {
        window._mineLabel = L.control({position: 'bottomleft'});
        window._mineLabel.onAdd = () => { const d = L.DomUtil.create('div'); d.id='mine-year-label'; d.className='bg-dark text-light border border-danger px-2 py-1 rounded small shadow'; return d; };
        window._mineLabel.addTo(mapa);
      }
      const el = document.getElementById('mine-year-label');
      el.textContent = '';
      const b = document.createElement('b');
      b.style.color = '#ff3b30';
      b.textContent = `⬢ Mina ${lbl}`;
      el.appendChild(b);
    }
    // % do buffer
    let denom = null;
    if (RESUMO && buffer) {
      const b = RESUMO.buffers_ha.find(x => String(x.raio_km) === String(buffer));
      if (b) denom = b.ha;
    } else if (RESUMO) {
      const b = RESUMO.buffers_ha.find(x => x.raio_km === 10);
      if (b) denom = b.ha;
    }
    document.getElementById('kpi-perc').innerText = denom ? (ha / denom * 100).toFixed(2) + ' %' : '—';
    const cont = {};
    feats.forEach(f => cont[f.properties.classe] = (cont[f.properties.classe] || 0) + 1);
    const dom = Object.entries(cont).sort((a, b) => b[1] - a[1])[0];
    document.getElementById('kpi-classe').innerText = dom ? dom[0] : '—';
    if (feats.length) { try { mapa.fitBounds(camDesmate.getBounds().pad(0.1)); } catch (e) {} }
  } catch (e) { erro(e.message); }
}

async function mostrarSerie() {
  try {
    SERIE = await api('/api/serie');
    const anos = [...new Set(SERIE.map(s => s.ano))].sort();
    const por = (raio) => anos.map(a => SERIE.filter(s => s.ano === a && s.raio_km === raio).reduce((t, s) => t + s.ha, 0));
    const ctx = document.getElementById('graf');
    if (chart) chart.destroy();
    if (window.Chart) Chart.defaults.color = '#cfd4da';
    chart = new Chart(ctx, {type: 'line',
      data: {labels: anos, datasets: [
        {label: '1 km', data: por(1), tension: 0.2},
        {label: '5 km', data: por(5), tension: 0.2},
        {label: '10 km', data: por(10), tension: 0.2}]},
      options: {plugins: {legend: {position: 'bottom'}}, scales: {y: {title: {display: true, text: 'ha'}}}}});
    // tabela - construção segura via DOM
    const tab = document.getElementById('tab');
    tab.innerHTML = '';
    anos.forEach(a => {
      const v = (r) => SERIE.filter(s => s.ano === a && s.raio_km === r).reduce((t, s) => t + s.ha, 0).toFixed(1);
      const tr = document.createElement('tr');
      [a, v(1), v(5), v(10)].forEach(val => {
        const td = document.createElement('td');
        td.textContent = val;
        tr.appendChild(td);
      });
      tab.appendChild(tr);
    });
    interpreta();
  } catch (e) { erro(e.message); }
}

function interpreta() {
  const tot = (raio, ano) => SERIE.filter(s => s.raio_km === raio && s.ano === ano).reduce((t, s) => t + s.ha, 0);
  const anos = [...new Set(SERIE.map(s => s.ano))].sort();
  if (anos.length < 2) return;
  const a0 = anos[0], a1 = anos[anos.length - 1];
  const past5 = SERIE.filter(s => s.raio_km === 5 && s.classe === 'pastagem').reduce((t, s) => t + s.ha, 0);
  const min1 = SERIE.filter(s => s.raio_km === 1 && s.classe === 'mineracao').reduce((t, s) => t + s.ha, 0);
  const cresc5 = tot(5, a1) - tot(5, a0);
  const interp = document.getElementById('texto-interp');
  interp.textContent = '';
  const mkB = (t) => { const e = document.createElement('b'); e.textContent = t; return e; };
  interp.append('Entre ', mkB(String(a0)), ` e `, mkB(String(a1)), ` o desmate no buffer 5km cresceu `, mkB(`${cresc5.toFixed(1)} ha`), '. ');
  interp.append('Pastagem soma ', mkB(`${past5.toFixed(1)} ha`), ' no 5km contra ', mkB(`${min1.toFixed(1)} ha`), ' de mineração no 1km. ');
  interp.append('Leitura: há perda florestal associada à mina (cava/pilha no 1km), mas o vetor dominante no entorno é agropecuário — coerente com Canaã dos Carajás. Defender 5km como "entorno funcional" e 1km como "impacto direto".');
}

base();
