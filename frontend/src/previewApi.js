const API_BASE = "https://automatic-resume-tracker-art.fastapicloud.dev/";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);

  if (!response.ok) {
    let error = {};
    try {
      error = await response.json();
    } catch {}

    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/* ---------------------- Upload ZIP ---------------------- */

export async function uploadZip(file) {
    const form = new FormData();
    form.append("file", file);

    const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: form,
    });

    if (!res.ok)
        throw new Error(await res.text());

    return res.json();
}

/* ---------------------- Extract ZIP ---------------------- */

export async function extractZip(folderName, destinationName = "") {
  return request("/extract", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      folder_name: folderName,
      destination_name: destinationName,
    }),
  });
}

/* ---------------------- Folder List ---------------------- */

export async function listFolders() {
  return request("/folders");
}

/* ---------------------- Recent Files ---------------------- */

export async function getRecentFiles() {
  return request("/recent_files");
}

/* ---------------------- Statistics ---------------------- */

export async function getStatistics() {
  return request("/statistics");
}

/* ---------------------- Preview ---------------------- */

export async function getPreview(folderName) {
  return request(`/${encodeURIComponent(folderName)}/preview`);
}

/* ---------------------- Search ---------------------- */

export async function searchPreview(folderName, keyword) {
  return request(`/${encodeURIComponent(folderName)}/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      keyword,
    }),
  });
}

/* ---------------------- Export Excel ---------------------- */

export function exportUrl(folderName) {
  return `${API_BASE}/${encodeURIComponent(
    folderName
  )}/export_to_excel`;
}

/* ---------------------- Open Recent File ---------------------- */

export async function resetApplication() {
  return request("/reset", {
    method: "POST",
  });
}

export function openRecentFile(path) {
    window.open(
        `${API_BASE}/open?path=${encodeURIComponent(path)}`,
        "_blank"
    );
}

export async function getProgress() {
    return request("/progress");
}
/*
export async function deleteFolder(folder_name) {
    return request(`/folders/${encodeURIComponent(folder_name)}`, {
        method: "DELETE",
    });
}*/
