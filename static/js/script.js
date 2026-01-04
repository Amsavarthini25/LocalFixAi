const API_KEY = "pk.e1b6dbb6e8502ec7c028960d2d649198";

/* ======================================================
   PAGE 1 — IMAGE UPLOAD
====================================================== */
document.addEventListener("DOMContentLoaded", () => {

  const imageInput = document.getElementById("imageInput");
  if (!imageInput) return;

  const imagePreview = document.getElementById("imagePreview");
  const previewContainer = document.getElementById("previewContainer");
  const issueTypeField = document.getElementById("issueType");
  const departmentField = document.getElementById("department");
  const priorityField = document.getElementById("priority");
  const nextBtn = document.getElementById("nextBtn");

  let analysisDone = false;

  imageInput.addEventListener("change", async () => {

    const file = imageInput.files[0];
    if (!file) return;

    imagePreview.src = URL.createObjectURL(file);
    previewContainer.style.display = "block";

    const formData = new FormData();
    formData.append("image", file);
    formData.append("description", document.getElementById("description").value);

    const res = await fetch("/analyze", {
      method: "POST",
      body: formData
    });

    const data = await res.json();

    issueTypeField.value = data.ai_result.issue_type;
    departmentField.value = data.ai_result.department;
    priorityField.value = data.ai_result.priority;

    sessionStorage.setItem("complaintId", data.complaint_id);
    sessionStorage.setItem("issueType", data.ai_result.issue_type);
    sessionStorage.setItem("department", data.ai_result.department);
    sessionStorage.setItem("priority", data.ai_result.priority);

    analysisDone = true;
  });

  nextBtn.addEventListener("click", () => {
    if (!analysisDone) {
      alert("Upload image first");
      return;
    }
    window.location.href = "/location";
  });

  if (sessionStorage.getItem("issueType")) {
    issueTypeField.value = sessionStorage.getItem("issueType");
    departmentField.value = sessionStorage.getItem("department");
    priorityField.value = sessionStorage.getItem("priority");
    previewContainer.style.display = "block";
  }

});




/* ======================================================
   PAGE 2 — LOCATION
====================================================== */
if (document.getElementById("street")) {

  function identifyAuthority(address) {
    let type = "Unknown";
    let name = "Unknown";
    let ward = "Not Available";
    let zone = "Not Available";

    if (address.ward) ward = address.ward;

    if (address.suburb) zone = address.suburb;
    else if (address.neighbourhood) zone = address.neighbourhood;
    else if (address.city_district) zone = address.city_district;

    if (address.municipality) {
      type = "Municipality";
      name = address.municipality;
    }
    else if (address.city) {
      type = "Municipal Corporation";
      name = address.city + " Municipal Corporation";
    }
    else if (address.town) {
      type = "Municipality";
      name = address.town + " Municipality";
    }
    else if (address.village) {
      type = "Panchayat";
      name = address.village + " Panchayat";
    }

    return { type, name, ward, zone };
  }

  window.detectLocation = async () => {

    const street = document.getElementById("street").value;
const area = document.getElementById("area").value;
const city = document.getElementById("cityInput").value;
const state = document.getElementById("stateInput").value;
const pincode = document.getElementById("pincode").value;

sessionStorage.setItem("street", street);
sessionStorage.setItem("area", area);
sessionStorage.setItem("cityInput", city);
sessionStorage.setItem("stateInput", state);
sessionStorage.setItem("pincode", pincode);

const fullAddress = `${street}, ${area}, ${city}, ${state}, ${pincode}`;
sessionStorage.setItem("address", fullAddress);


    const query = `${street}, ${area}, ${city}, ${state}, ${pincode}, India`;

    const url = `https://us1.locationiq.com/v1/search.php?key=${API_KEY}&q=${encodeURIComponent(query)}&format=json&addressdetails=1`;

    const res = await fetch(url);
    const data = await res.json();

    if (!data || !data[0]) {
      alert("Location not found");
      return;
    }

    const loc = data[0];
    const addr = loc.address;

    const authority = identifyAuthority(addr);

    document.getElementById("lat").innerText = loc.lat;
    document.getElementById("lng").innerText = loc.lon;
    document.getElementById("city").innerText = addr.city || addr.town || "-";
    document.getElementById("state").innerText = addr.state || "-";
    document.getElementById("authorityName").innerText = authority.name;
    document.getElementById("authorityType").innerText = authority.type;
    document.getElementById("ward").innerText = authority.ward;
    document.getElementById("zone").innerText = authority.zone;


    sessionStorage.setItem("latitude", loc.lat);
    sessionStorage.setItem("longitude", loc.lon);
    sessionStorage.setItem("municipality", authority.name);
    sessionStorage.setItem("city", addr.city || addr.town || "");
    sessionStorage.setItem("state", addr.state || "");
    sessionStorage.setItem("authorityType", authority.type);
    sessionStorage.setItem("ward", authority.ward);
    sessionStorage.setItem("zone", authority.zone);
  };

  window.goToReview = () => {
    if (!sessionStorage.getItem("latitude")) {
      alert("Detect location first");
      return;
    }
    window.location.href = "/review";
  };
  document.addEventListener("DOMContentLoaded", () => {
  ["street","area","cityInput","stateInput","pincode"].forEach(id => {
    if (sessionStorage.getItem(id))
      document.getElementById(id).value = sessionStorage.getItem(id);
  });

  if (sessionStorage.getItem("latitude")) {
    document.getElementById("lat").innerText = sessionStorage.getItem("latitude");
    document.getElementById("lng").innerText = sessionStorage.getItem("longitude");
    document.getElementById("authorityName").innerText = sessionStorage.getItem("municipality");
    document.getElementById("authorityType").innerText = sessionStorage.getItem("authorityType");
    document.getElementById("ward").innerText = sessionStorage.getItem("ward");
    document.getElementById("zone").innerText = sessionStorage.getItem("zone");
  }
});

}




/* ======================================================
   PAGE 3 — REVIEW
====================================================== */
if (document.getElementById("submitComplaintBtn")) {

  document.getElementById("revIssueType").value = sessionStorage.getItem("issueType");
  document.getElementById("revDepartment").value = sessionStorage.getItem("department");
  document.getElementById("revPriority").value = sessionStorage.getItem("priority");
  document.getElementById("revMunicipality").value = sessionStorage.getItem("municipality");
  document.getElementById("revLatitude").value = sessionStorage.getItem("latitude");
  document.getElementById("revLongitude").value = sessionStorage.getItem("longitude");
}


function submitComplaint() {
  fetch("/receive", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      complaint_id: sessionStorage.getItem("complaintId"),
      latitude: sessionStorage.getItem("latitude"),
      longitude: sessionStorage.getItem("longitude"),
      address: sessionStorage.getItem("address"),
      municipality: sessionStorage.getItem("municipality"),
      city: sessionStorage.getItem("city"),
      state: sessionStorage.getItem("state")
    })
  })
  .then(res => res.json())
  .then(() => {
    // 🚫 DO NOT clear session here
    window.location.href = "/success";
  })
  .catch(err => {
    console.error(err);
    alert("Submission failed");
  });
}

function goHome() {
  sessionStorage.clear();
  window.location.href = "/";
}

/* ============================
AUTHORITY DASHBOARD
================================*/

let activeComplaintId = null;

function openEtaPopup(id) {
    activeComplaintId = id;

    fetch(`/authority/eta/${id}`)
        .then(res => res.json())
        .then(data => {

            document.getElementById("etaText").innerText =
                `System Suggested ETA : ${data.system_eta} days`;

            document.getElementById("finalEta").value = data.eta;
            document.getElementById("overrideReason").value = "";
            document.getElementById("overrideSection").style.display = "none";

            document.getElementById("etaModal").style.display = "block";
        });
}

function closeModal(){
    document.getElementById("etaModal").style.display="none";
    document.getElementById("overrideSection").style.display="none";
    activeComplaintId = null;
}

function showOverride(){
    document.getElementById("overrideSection").style.display="block";
}

function acceptEta(){
    fetch("/authority/update-eta",{
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify({
            complaint_id: activeComplaintId,
            eta: document.getElementById("finalEta").value,
            overridden: document.getElementById("overrideReason").value !== "",
            reason: document.getElementById("overrideReason").value
        })
    }).then(()=>{ 
        alert("ETA Saved"); 
        location.reload(); 
    });
}


/*=========================================
STATUS TRACKING
===========================================*/

document.addEventListener("DOMContentLoaded", () => {

  if (!document.getElementById("status-actions")) return;

  const complaintId = document.getElementById("status-actions").dataset.cid;
  const currentStatus = document.getElementById("status-actions").dataset.status;

  const btnMap = {
    "Assigned": {text:"Mark as Visited", next:"Visited"},
    "Visited": {text:"Start Work", next:"In_Progress"},
    "In_Progress": {text:"Mark as Resolved", next:"Resolved"}
  };

  if(btnMap[currentStatus]){
    const btn = document.createElement("button");
    btn.className = "status-btn";
    btn.innerText = btnMap[currentStatus].text;

    btn.onclick = () => {
      fetch("/authority/update-status",{
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify({
          complaint_id: complaintId,
          status: btnMap[currentStatus].next
        })
      }).then(()=>location.reload());
    };

    document.getElementById("status-actions").appendChild(btn);
  }

});



function fetchNotifications(){
  fetch("/authority/notifications-json")
    .then(r=>r.json())
    .then(data=>{
        let container = document.getElementById("notif-container");
        container.innerHTML = "";
        data.forEach(n=>{
            let row = `<div>
                Complaint #${n.complaint_id} | Level ${n.escalation_level} | ${n.notified_to} | ${n.notified_at}
            </div>`;
            container.innerHTML += row;
        });
    });
}

setInterval(fetchNotifications, 60000); // refresh every minute
fetchNotifications(); // initial load


document.addEventListener("DOMContentLoaded", function () {
  const role = document.getElementById("role");
  const dept = document.getElementById("department");
  const muni = document.getElementById("municipality");

  function applyRules() {
    const r = role.value;

    if (r === "Assistant Commissioner") {
      dept.value = "";
      dept.disabled = true;
      dept.removeAttribute("required");

      muni.disabled = false;
      muni.setAttribute("required", "required");
    }

    else if (r === "Commissioner") {
      dept.value = "";
      muni.value = "NA";

      dept.disabled = true;
      muni.disabled = true;

      dept.removeAttribute("required");
      muni.removeAttribute("required");
    }

    else {
      dept.disabled = false;
      muni.disabled = false;
      dept.setAttribute("required", "required");
      muni.setAttribute("required", "required");

      if (muni.value === "NA") muni.value = "";
    }
  }

  role.addEventListener("change", applyRules);
});

function fetchNotifications() {
    fetch('/api/citizen/notifications')
    .then(response => response.json())
    .then(data => {
        const list = document.querySelector('.notification-list');
        if (!list) return;

        list.innerHTML = '';
        if (data.length === 0) {
            list.innerHTML = '<p>No notifications yet.</p>';
            return;
        }

        data.forEach(n => {
            const li = document.createElement('li');
            li.className = 'notification-item';
            li.innerHTML = `
                <strong>Complaint ID:</strong> ${n.complaint_id}<br>
                <strong>Status:</strong> ${n.status}<br>
                <strong>Updated By:</strong> ${n.updated_by_name || 'System'}<br>
                <small>${n.timestamp}</small>
            `;
            list.appendChild(li);
        });
    })
    .catch(err => console.error('Error fetching notifications:', err));
}

// Poll every 10 seconds
setInterval(fetchNotifications, 10000);
document.addEventListener('DOMContentLoaded', fetchNotifications);


function updateNotificationCount() {
    fetch('/api/citizen/unread_count')
    .then(res => res.json())
    .then(data => {
        const badge = document.getElementById('notif-count');
        if (data.count > 0) {
            badge.textContent = data.count;
            badge.style.display = 'inline';
        } else {
            badge.style.display = 'none';
        }
    })
    .catch(err => console.error('Error fetching unread count:', err));
}

// Poll every 10 seconds
function loadUnread() {
    fetch('/api/authority/unread-count')
    .then(res => res.json())
    .then(d => {
        const badge = document.getElementById('noti-badge');
        if (!badge) return;
        if (d.cnt > 0) {
            badge.innerText = d.cnt;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    });
}

document.addEventListener('DOMContentLoaded', loadUnread);
setInterval(loadUnread, 30000); // update every 30 sec


//-----------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("userDropdownToggle");
  const menu = document.getElementById("userDropdownMenu");

  if (toggle && menu) {
    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.toggle("show"); // add .show class to display dropdown
    });

    // Hide dropdown when clicking outside
    document.addEventListener("click", () => {
      menu.classList.remove("show");
    });
  }

  // Optional: redirect logout to home if needed
  const logoutLink = document.getElementById("logoutLink");
  if (logoutLink) {
    logoutLink.addEventListener("click", (e) => {
      e.preventDefault();
      fetch(logoutLink.href) // call logout route
        .then(() => {
          sessionStorage.clear();
          window.location.href = "/";
        });
    });
  }
});

