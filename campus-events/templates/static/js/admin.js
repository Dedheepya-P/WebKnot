// admin.js - simple admin UI that talks to the Flask API
const createBtn = document.getElementById('createEventBtn');
const createMsg = document.getElementById('createMsg');
const eventsList = document.getElementById('eventsList');
const refreshBtn = document.getElementById('refreshEvents');
const filterType = document.getElementById('filterType');

createBtn.onclick = async () => {
  createMsg.textContent = "Creating...";
  const payload = {
    college_id: document.getElementById('college_id').value,
    title: document.getElementById('title').value,
    event_type: document.getElementById('event_type').value,
    start_ts: document.getElementById('start_ts').value,
    end_ts: document.getElementById('end_ts').value,
    location: document.getElementById('location').value,
    capacity: parseInt(document.getElementById('capacity').value || "0"),
    status: "published"
  };
  try {
    const res = await fetch('/api/events', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const j = await res.json();
    createMsg.textContent = res.ok ? `Created event ${j.event_id}` : `Error: ${JSON.stringify(j)}`;
    loadEvents();
  } catch(e) {
    createMsg.textContent = "Error: " + e.toString();
  }
};

async function loadEvents(){
  eventsList.textContent = "Loading...";
  const college = document.getElementById('college_id').value || '';
  const type = filterType.value || '';
  const url = `/api/reports/event_popularity?college_id=${encodeURIComponent(college)}&limit=100`;
  const res = await fetch(url);
  const rows = await res.json();
  let html = '';
  for (const r of rows){
    if (type && r.event_type !== type) continue;
    html += `<div class="event"><strong>${r.title}</strong> (${r.event_type})<br/>Registrations: ${r.registrations || 0}<br/>Start: ${r.start_ts || ''}</div>`;
  }
  eventsList.innerHTML = html || "<em>No events</em>";
}

refreshBtn.onclick = loadEvents;
filterType.onchange = loadEvents;
loadEvents();
