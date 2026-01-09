// small frontend helper for the appointment flow and dashboard data
async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    const txt = await res.text().catch(()=>null);
    throw new Error(`HTTP ${res.status} ${txt || ''}`);
  }
  return res.json();
}

// Function to update notifications
async function updateNotifications() {
  const notificationCount = document.getElementById('notification-count');
  const notificationsList = document.getElementById('notifications-list');
  
  if (!notificationCount || !notificationsList) return;
  
  try {
    // Fetch both inventory alerts and upcoming appointments
    const [alertsRes, apptsRes] = await Promise.all([
      fetchJSON('/api/inventory/alerts'),
      fetchJSON('/api/appointments')
    ]);
    
    const notifications = [];
    
    // Add inventory alerts
    if (alertsRes.alerts && alertsRes.alerts.length) {
      alertsRes.alerts.forEach(alert => {
        notifications.push({
          type: 'inventory',
          icon: 'fas fa-exclamation-triangle',
          iconColor: '#f59e0b',
          title: alert.message,
          time: 'Just now'
        });
      });
    }
    
    // Add recent appointment notifications (last 24 hours or upcoming)
    if (apptsRes && apptsRes.length) {
      const now = new Date();
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      const nextWeek = new Date(now);
      nextWeek.setDate(nextWeek.getDate() + 7);
      
      apptsRes.forEach(appt => {
        try {
          const apptDate = new Date(appt.appointment_date);
          // Show appointments created in last 24h or upcoming within next week
          if (apptDate >= yesterday && apptDate <= nextWeek) {
            const isUpcoming = apptDate > now;
            const timeAgo = isUpcoming 
              ? `Scheduled for ${apptDate.toLocaleDateString()} ${apptDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`
              : `${apptDate.toLocaleDateString()} ${apptDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
            
            notifications.push({
              type: 'appointment',
              icon: 'fas fa-calendar-check',
              iconColor: '#10b981',
              title: `${appt.patient} with ${appt.doctor}`,
              time: timeAgo
            });
          }
        } catch (e) {
          console.warn('Invalid appointment date:', appt.appointment_date);
        }
      });
    }
    
    // Update notification count
    notificationCount.textContent = notifications.length;
    if (notifications.length > 0) {
      notificationCount.style.display = 'flex';
    } else {
      notificationCount.style.display = 'none';
    }
    
    // Update notifications list
    if (notifications.length) {
      notificationsList.innerHTML = notifications.map(n => `
        <div class="notification-item">
          <i class="${n.icon}" style="color: ${n.iconColor};"></i>
          <div class="notification-content">
            <div class="notification-title">${n.title}</div>
            <div class="notification-time">${n.time}</div>
          </div>
        </div>
      `).join('');
    } else {
      notificationsList.innerHTML = '<div class="notification-item">No new notifications</div>';
    }
  } catch (err) {
    console.error('Error updating notifications:', err);
    if (notificationCount) notificationCount.textContent = '!';
    if (notificationsList) notificationsList.innerHTML = '<div class="notification-item">Error loading notifications</div>';
  }
}

// Show a toast notification
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
    <span>${message}</span>
  `;
  document.body.appendChild(toast);
  
  // Trigger animation
  setTimeout(() => toast.classList.add('show'), 10);
  
  // Remove after 3 seconds
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

document.addEventListener('DOMContentLoaded', () => {
  // Sidebar toggle with persistence
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const SIDEBAR_KEY = 'mc.sidebarHidden';

  function setSidebarUI(hidden) {
    document.body.classList.toggle('sidebar-hidden', hidden);
    if (sidebarToggle) {
      const icon = sidebarToggle.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-bars', !hidden);
        icon.classList.toggle('fa-times', hidden);
      }
      sidebarToggle.setAttribute('aria-expanded', String(!hidden));
      sidebarToggle.setAttribute('title', hidden ? 'Show sidebar' : 'Hide sidebar');
    }
  }

  // Restore from localStorage
  try {
    const saved = localStorage.getItem(SIDEBAR_KEY);
    if (saved === 'true' || saved === 'false') {
      setSidebarUI(saved === 'true');
    }
  } catch (e) { /* ignore storage errors */ }

  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
      const nowHidden = !document.body.classList.contains('sidebar-hidden');
      setSidebarUI(nowHidden);
      try { localStorage.setItem(SIDEBAR_KEY, String(nowHidden)); } catch (e) {}
    });
  }

  // Update notifications
  updateNotifications();
  // Refresh notifications every 5 minutes
  setInterval(updateNotifications, 5 * 60 * 1000);
  
  // populate upcoming appointments panel if on appointments page
  const upcomingEl = document.getElementById('upcoming');
  if (upcomingEl) loadUpcoming();

  // appointment form logic
  const doctorEl = document.getElementById('doctor');
  const dateEl = document.getElementById('appt-date');
  const timeEl = document.getElementById('appt-time');
  const appForm = document.getElementById('appointment-form');

  if (doctorEl && dateEl) {
    // when doctor or date changes, fetch free slots
    async function updateSlots() {
      const docId = doctorEl.value;
      const date = dateEl.value;
      if (!docId || !date) {
        timeEl.innerHTML = '<option value="">Select doctor & date</option>';
        return;
      }
      try {
        const slots = await fetchJSON(`/api/get_slots/${docId}/${date}`);
        if (slots.length) {
          timeEl.innerHTML = '<option value="">Choose time...</option>' + slots.map(s => `<option value="${s}">${s}</option>`).join('');
        } else {
          timeEl.innerHTML = '<option value="">No slots available</option>';
        }
      } catch (e) {
        timeEl.innerHTML = '<option value="">Error loading slots</option>';
      }
    }
    doctorEl.addEventListener('change', updateSlots);
    dateEl.addEventListener('change', updateSlots);
  }

  if (appForm) {
    appForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const doctor = form.doctor.value;
      const patient = form.patient.value;
      const date = form.date.value; // yyyy-mm-dd
      const time = form.time.value; // HH:MM
      const notes = document.getElementById('notes') ? document.getElementById('notes').value : '';
      if (!doctor || !patient || !date || !time) {
        alert('Please fill required fields');
        return;
      }
      const iso = new Date(`${date}T${time}:00`).toISOString();
      try {
        await fetchJSON('/api/appointments/new', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({
            patient_id: patient,
            doctor_id: doctor,
            appointment_date: iso,
            notes
          })
        });
        
        // Success feedback
        showToast('Appointment scheduled successfully!', 'success');
        form.reset();
        
        // Refresh data
        if (typeof loadUpcoming === 'function') loadUpcoming();
        
        // Immediately update notifications
        await updateNotifications();
        
        // Briefly highlight the notification bell
        const notificationBtn = document.getElementById('notification-btn');
        if (notificationBtn) {
          notificationBtn.classList.add('pulse');
          setTimeout(() => notificationBtn.classList.remove('pulse'), 2000);
        }
      } catch (err) {
        alert('Failed to schedule: ' + err.message);
      }
    });
  }

  // load upcoming appointments
  async function loadUpcoming() {
    try {
      const appts = await fetchJSON('/api/appointments');
      const items = appts.slice(0, 8).map(a => {
        const when = new Date(a.appointment_date);
        return `<div class="item" data-id="${a.id}"><div><strong>${a.patient}</strong> with <em>${a.doctor}</em></div><div class="muted">${when.toLocaleString()}</div><div class="actions"><button data-id="${a.id}" class="btn small danger delete-appt">Delete</button></div></div>`;
      }).join('') || '<div class="muted">No upcoming appointments</div>';
      upcomingEl.innerHTML = items;
    } catch (e) {
      upcomingEl.innerHTML = '<div class="muted">Could not load appointments</div>';
    }
  }

  // delegate delete clicks
  document.addEventListener('click', async (ev) => {
    const btn = ev.target.closest && ev.target.closest('.delete-appt');
    if (!btn) return;
    const id = btn.getAttribute('data-id');
    if (!id) return;
    if (!confirm('Delete this appointment?')) return;
    try {
      await fetchJSON(`/api/appointments/${id}`, { method: 'DELETE' });
      loadUpcoming();
      alert('Appointment deleted');
    } catch (err) {
      alert('Failed to delete: ' + err.message);
    }
  });

  // patient delete handler (delegated)
  document.addEventListener('click', async (ev) => {
    const btn = ev.target.closest && ev.target.closest('.delete-patient');
    if (!btn) return;
    const id = btn.getAttribute('data-id');
    if (!id) return;
    if (!confirm('Delete this patient and all their appointments?')) return;
    try {
      await fetchJSON(`/api/patients/${id}`, { method: 'DELETE' });
      // remove row from recent table if present
      const row = document.querySelector(`tr[data-id="${id}"]`);
      if (row) row.remove();
      alert('Patient deleted');
    } catch (err) {
      alert('Failed to delete patient: ' + err.message);
    }
  });
  
    // Notification and admin dropdown toggles
    const notificationBtn = document.getElementById('notification-btn');
    const notificationsWrap = document.getElementById('notifications');
    const adminBtn = document.getElementById('admin-btn');
    const adminWrap = document.getElementById('admin-menu');

    function closeAllDropdowns() {
      if (notificationsWrap) notificationsWrap.classList.remove('open');
      if (adminWrap) adminWrap.classList.remove('open');
    }

    if (notificationBtn && notificationsWrap) {
      notificationBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = notificationsWrap.classList.toggle('open');
        if (isOpen) {
          // ensure list is fresh
          updateNotifications();
        }
        if (adminWrap) adminWrap.classList.remove('open');
      });
    }

    if (adminBtn && adminWrap) {
      adminBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        adminWrap.classList.toggle('open');
        if (notificationsWrap) notificationsWrap.classList.remove('open');
      });
    }

    // Close when clicking outside
    document.addEventListener('click', (e) => {
      const target = e.target;
      if (notificationsWrap && !notificationsWrap.contains(target)) notificationsWrap.classList.remove('open');
      if (adminWrap && !adminWrap.contains(target)) adminWrap.classList.remove('open');
    });
});

// Logout handler
function handleLogout() {
  if (confirm('Are you sure you want to logout?')) {
    showToast('Logging out...', 'success');
    // In a real app, you would call a logout API endpoint
    setTimeout(() => {
      window.location.href = '/';
    }, 1000);
  }
}

// small helper used in template reset button
function resetForm() {
  const f = document.getElementById('appointment-form');
  if (f) f.reset();
}

// AI Functions
async function getAISuggestions() {
  const doctorEl = document.getElementById('doctor');
  const dateEl = document.getElementById('appt-date');
  const suggestionsEl = document.getElementById('ai-suggestions');
  
  if (!doctorEl || !dateEl || !suggestionsEl) return;
  
  const doctorId = doctorEl.value;
  const date = dateEl.value;
  
  if (!doctorId || !date) {
    alert('Please select a doctor and date first');
    return;
  }
  
  try {
    suggestionsEl.innerHTML = '<div style="padding: 0.5rem;"><i class="fas fa-spinner fa-spin"></i> Getting AI suggestions...</div>';
    
    const response = await fetch('/api/ai/suggest-appointment', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ doctor_id: parseInt(doctorId), date: date })
    });
    
    const data = await response.json();
    
    if (data.suggestions && data.suggestions.length > 0) {
      suggestionsEl.innerHTML = `
        <div style="background: #e9fbf9; padding: 1rem; border-radius: 8px; margin-top: 0.5rem;">
          <strong><i class="fas fa-robot"></i> AI Recommendations:</strong>
          <div style="margin-top: 0.5rem;">
            ${data.suggestions.map((s, idx) => `
              <div style="padding: 0.5rem; margin: 0.25rem 0; background: white; border-radius: 4px; cursor: pointer; border: 1px solid #0aa89e;"
                   onclick="selectAITime('${s.time}')">
                <strong>${s.time_display}</strong> 
                <span style="color: #666; font-size: 0.9em;">(Score: ${s.score.toFixed(2)})</span>
                <span style="float: right; color: #0aa89e; font-size: 0.85em;">${s.reason}</span>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    } else {
      suggestionsEl.innerHTML = '<div style="padding: 0.5rem; color: #666;">No AI suggestions available</div>';
    }
  } catch (err) {
    suggestionsEl.innerHTML = `<div style="padding: 0.5rem; color: #d32f2f;">Error: ${err.message}</div>`;
  }
}

function selectAITime(timeISO) {
  const timeEl = document.getElementById('appt-time');
  const dateEl = document.getElementById('appt-date');
  
  if (!timeEl || !dateEl) return;
  
  // Parse ISO time and set the time select
  try {
    const dt = new Date(timeISO);
    const timeStr = `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`;
    
    // Find and select the option
    for (let option of timeEl.options) {
      if (option.value === timeStr) {
        timeEl.value = timeStr;
        break;
      }
    }
    
    // If not found, add it
    if (timeEl.value !== timeStr) {
      const option = document.createElement('option');
      option.value = timeStr;
      option.textContent = timeStr;
      timeEl.appendChild(option);
      timeEl.value = timeStr;
    }
  } catch (err) {
    console.error('Error selecting AI time:', err);
  }
}

// NLP Query Processing
async function processNLPQuery(query) {
  try {
    const response = await fetch('/api/ai/nlp-query', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ query: query })
    });
    
    return await response.json();
  } catch (err) {
    console.error('NLP query error:', err);
    return { error: err.message };
  }
}

// Patient Flow Prediction
async function predictPatientFlow(date) {
  try {
    const response = await fetch('/api/ai/predict-flow', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ date: date })
    });
    
    return await response.json();
  } catch (err) {
    console.error('Flow prediction error:', err);
    return { error: err.message };
  }
}

// Global Search Handler
function handleGlobalSearch() {
  const searchInput = document.getElementById('global-search');
  if (!searchInput) return;
  
  const query = searchInput.value.trim();
  if (!query) return;
  
  // Redirect to AI search page with query
  window.location.href = `/ai-search?q=${encodeURIComponent(query)}`;
}

// Allow Enter key in global search
document.addEventListener('DOMContentLoaded', () => {
  const globalSearch = document.getElementById('global-search');
  if (globalSearch) {
    globalSearch.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        handleGlobalSearch();
      }
    });
  }
});
