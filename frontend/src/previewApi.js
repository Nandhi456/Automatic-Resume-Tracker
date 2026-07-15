const API_BASE = "https://automatic-resume-tracker-msmq.vercel.app";
//const API_BASE = "https://automatic-resume-tracker.streamlit.app";
//const API_BASE = "https://automatic-resume-tracker-art.fastapicloud.dev";
//const API_BASE = "https://automatic-resume-tracker-owtq.vercel.app";

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
    // Step 1: ask backend for a presigned B2 upload URL
    const { upload_url, filename } = await request(
        `/api/get_upload_url?filename=${encodeURIComponent(file.name)}`
    );

    // Step 2: upload the raw file directly to B2 (browser -> B2, skips your Vercel function)
    const uploadRes = await fetch(upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": "application/zip" },
    });

    if (!uploadRes.ok) {
        throw new Error("Direct upload to storage failed");
    }

    // Keep the same return shape your component already expects
    return { filename };
}

/* ---------------------- Extract ZIP ---------------------- */
export async function extractZip(folderName, destinationName = "") {
  return request("/api/extract", {
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
  return request("/api/folders");
}

/* ---------------------- Recent Files ---------------------- */
export async function getRecentFiles() {
  return request("/api/recent_files");
}

/* ---------------------- Statistics ---------------------- */
export async function getStatistics() {
  return request("/api/statistics");
}

/* ---------------------- Preview ---------------------- */
export async function getPreview(folderName) {
  return request(`/api/${encodeURIComponent(folderName)}/preview`);
}

/* ---------------------- Search ---------------------- */
export async function searchPreview(folderName, keyword) {
  return request(`/api/${encodeURIComponent(folderName)}/search`, {
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
  return `${API_BASE}/api/${encodeURIComponent(
    folderName
  )}/export_to_excel`;
}

/* ---------------------- Reset ---------------------- */
export async function resetApplication() {
  return request("/api/reset", {
    method: "POST",
  });
}

/* ---------------------- Open Recent File ---------------------- */
export function openRecentFile(path) {
    window.open(
        `${API_BASE}/api/open?path=${encodeURIComponent(path)}`,
        "_blank"
    );
}

/* ---------------------- Progress ---------------------- */
export async function getProgress() {
    return request("/api/progress");
}

/*
export async function deleteFolder(folder_name) {
    return request(`/api/folders/${encodeURIComponent(folder_name)}`, {
        method: "DELETE",
    });
}*/
