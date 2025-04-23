// same‐origin, so no more “http://localhost:8000”
const evtSource = new EventSource('/traffic_feed');
evtSource.onopen    = () => document.getElementById('status').innerText = 'Live';
evtSource.onerror   = () => document.getElementById('status').innerText = 'Disconnected';
evtSource.onmessage = e => {
  const { lanes, signal_times, timestamp } = JSON.parse(e.data);
  const container = document.getElementById('lanes');
  container.innerHTML = '';
  for (let lane in lanes) {
    const div = document.createElement('div');
    div.className = 'lane';
    const img = document.createElement('img');
    img.src = 'data:image/jpeg;base64,' + lanes[lane].image;
    img.width = 300;
    div.innerHTML = `<strong>${lane}</strong>: ${lanes[lane].count} vehicles ` +
                    `(Green: ${signal_times[lane]}s)`;
    div.appendChild(img);
    container.appendChild(div);
  }
  document.getElementById('status').innerText = `Updated: ${timestamp}`;
};

document.getElementById("uploadForm").onsubmit = async e => {
  e.preventDefault();
  const fileInput = document.getElementById("fileInput");
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  const res = await fetch("/upload_image", {
    method: "POST",
    body: formData
  });
  const data = await res.json();
  const result = document.getElementById("uploadResult");
  result.innerHTML = `Detected ${data.count} vehicles. Emergency: ${data.emergency ? 'Yes' : 'No'}<br>`;
  const img = document.createElement("img");
  img.src = 'data:image/jpeg;base64,' + data.image;
  img.width = 400;
  result.appendChild(img);
};
