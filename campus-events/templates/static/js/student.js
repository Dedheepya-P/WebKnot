// student.js - simple student UI interacting with API
const studentMsg = document.getElementById('studentMsg');
const eventsDiv = document.getElementById('events');

document.getElementById('createStudent').onclick = async () => {
  const payload = {
    student_uuid: document.getElementById('student_uuid').value || undefined,
    college_id: "college-1",
    student_local_id: document.getElementById('student_local_id').value,
    name: document.getElementById('student_name').value,
    email: document.getElementById('student_email').value
  };
  try {
    const res = await fetch('/api/students', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const j = await res.json();
    document.getElementById('student_uuid').value = j.student_uuid;
    studentMsg.textContent = "Saved. Student UUID: " + j.student_uuid;
  } catch (e) {
    studentMsg.textContent = "Error: " + e.toString();
  }
};

document.getElementById('loadEvents').onclick = loadEvents;

async function loadEvents(){
  const college = document.getElementById('collegeFilter').value || 'college-1';
  const res = await fetch(`/api/reports/event_popularity?college_id=${encodeURIComponent(college)}&limit=100`);
  const rows = await res.json();
  let html = '';
  const student_uuid = document.getElementById('student_uuid').value;
  for (const r of rows){
    html += `<div class="card"><h4>${r.title}</h4><div>Type: ${r.event_type} • Registrations: ${r.registrations||0}</div>
      <div style="margin-top:.5rem">
        <button onclick="register('${r.event_id}')">Register</button>
        <button onclick="checkin('${r.event_id}')">Check-in</button>
        <button onclick="openFeedback('${r.event_id}')">Feedback</button>
      </div>
      <div id="msg-${r.event_id}"></div>
    </div>`;
  }
  eventsDiv.innerHTML = html || "<em>No events</em>";
}

async function register(event_id){
  const student_uuid = document.getElementById('student_uuid').value;
  if (!student_uuid) return alert("Create student first.");
  const res = await fetch(`/api/events/${event_id}/register`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({student_uuid})
  });
  const j = await res.json();
  document.getElementById(`msg-${event_id}`).textContent = "Register: " + (j.status || JSON.stringify(j));
}

async function checkin(event_id){
  const student_uuid = document.getElementById('student_uuid').value;
  if (!student_uuid) return alert("Create student first.");
  const res = await fetch(`/api/events/${event_id}/attendance`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({student_uuid, method:"manual"})
  });
  const j = await res.json();
  document.getElementById(`msg-${event_id}`).textContent = "Check-in recorded";
}

function openFeedback(event_id){
  const rating = prompt("Enter rating 1-5 (cancel to skip):");
  if (!rating) return;
  const student_uuid = document.getElementById('student_uuid').value;
  fetch(`/api/events/${event_id}/feedback`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({student_uuid, rating: parseInt(rating), comments: ""})
  }).then(r=>r.json()).then(j=>{
    document.getElementById(`msg-${event_id}`).textContent = "Feedback submitted";
  }).catch(e=>alert("Error: "+e));
}
