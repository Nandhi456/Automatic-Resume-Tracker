import { AnimatePresence, motion } from "framer-motion";
import { useState, useRef, useEffect } from "react";
import { Folder, FileSpreadsheet, Loader2 } from "lucide-react"; 
import Preview from "./preview";
import {uploadZip, extractZip, listFolders,getPreview, getRecentFiles, openRecentFile, getStatistics, resetApplication, getProgress, getUploadUrl, uploadToB2} from "./previewApi";

const container = {
  height: "100vh",
  width: "100vw",
  display: "flex",
  flexDirection: "column",
  justifyContent: "flex-start",
  alignItems: "stretch",
  gap: "0",
  padding: "0",
  margin: "0",
  background: "linear-gradient(135deg, #0f172a, #1e293b)",
  color: "#f8fafc",
  fontFamily: "Inter, sans-serif",
  overflow: "hidden",
}

const containerTitle = {
  width: "100%",
  padding: "30px 40px",
  background: "rgba(30, 41, 59, 0.6)",
  borderBottom: "2px solid rgba(56, 189, 248, 0.3)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
}

const containerTitleText = {
  margin: 0,
  fontSize: "2.5rem",
  fontWeight: 700,
  color: "#f8fafc",
}

const contentWrapper = {
  display: "flex",
  flexDirection: "row",
  justifyContent: "flex-start",
  alignItems: "stretch",
  flex: 1,
  gap: "0",
  overflow: "hidden",
}

const centerContent = {
  display: "flex",
  flexDirection: "column",
  justifyContent: "flex-start",
  alignItems: "stretch",
  flex: 0.95,
  height: "100%",
  minHeight: "calc(100vh - 160px)",
  padding: "20px",
  overflowY: "auto",
}

const leftSidebar = {
  width: "400px",
  height: "100%",
  padding: "24px",
  background: "rgba(30, 41, 59, 0.95)",
  borderRight: "1px solid rgba(148, 163, 184, 0.16)",
  overflowY: "auto",
  boxShadow: "2px 0 20px rgba(15, 23, 42, 0.5)",
}

const rightSidebar = {
  width: "46%",
  height: "100%",
  padding: "20px",
  background: "rgba(30, 41, 59, 0.95)",
  borderLeft: "1px solid rgba(148, 163, 184, 0.16)",
  overflowY: "auto",
  boxShadow: "-2px 0 20px rgba(15, 23, 42, 0.5)",
}

const sidebarTitle = {
  margin: "0 0 20px 0",
  fontSize: "1.1rem",
  fontWeight: 700,
  color: "#f8fafc",
  borderBottom: "2px solid #38bdf8",
  paddingBottom: "12px",
}

const sidebarItem = {
  padding: "12px 16px",
  marginBottom: "10px",
  background: "rgba(11, 79, 57, 0.6)",
  borderRadius: "8px",
  color: "#cbd5e1",
  cursor: "pointer",
  transition: "all 0.2s ease",
  fontSize: "0.9rem",
}

const card = {
  width: "100%",
  height: "100%",
  display: "flex",
  flexDirection: "column",
  padding: "28px",
  borderRadius: "16px",
  background: "rgba(15,23,42,.96)",
  border: "1px solid rgba(148,163,184,.12)",
  boxShadow: "0 20px 40px rgba(0,0,0,.35)",
};

const header = {
  marginBottom: "28px",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
}

const subtitle = {
  margin: 0,
  color: "#94a3b8",
  fontSize: "0.95rem",
}

const field = {
  display: "flex",
  flexDirection: "column",
  gap: "10px",
  marginBottom: "22px",
}

const label = {
  fontSize: "0.9rem",
  color: "#cbd5e1",
}

const input = {
  width: "100%",
  padding: "14px 16px",
  borderRadius: "14px",
  border: "1px solid #334155",
  background: "#0f172a",
  color: "#e2e8f0",
  outline: "none",
}

const button = {
  width: "100%",
  padding: "14px 18px",
  borderRadius: "16px",
  border: "none",
  background: "#38bdf8",
  color: "#0f172a",
  fontWeight: 700,

}

const statusBox = {
  flex: 1,
  marginTop: "20px",
  background: "#111827",
  borderRadius: "14px",
  padding: "20px",
  display: "flex",
  alignItems: "flex-start",
  justifyContent: "flex-start",
  color: "#e2e8f0",
};

const folderRow = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "12px 14px",
  marginTop: "10px",
  background: "rgba(56, 189, 248, 0.08)",
  border: "1px solid rgba(56, 189, 248, 0.25)",
  borderRadius: "10px",
}

const folderName = {
  flex: 1,
  fontSize: "1rem",
  color: "#e2e8f0",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
}

const generateBtn = {
  display: "flex",
  alignItems: "center",
  gap: "6px",
  border: "1px solid #38bdf8",
  background: "rgba(56, 189, 248, 0.15)",
  color: "#38bdf8",
  borderRadius: "999px",
  padding: "6px 12px",
  fontSize: "0.90rem",
  fontWeight: 600,
  cursor: "pointer",
  flexShrink: 0,
}

const fileUploadBtn = {
  width: "100%",
  padding: "14px 16px",
  borderRadius: "14px",
  border: "1px dashed #334155",
  background: "#0f172a",
  color: "#e2e8f0",
  outline: "none",
  display: "flex",
  alignItems: "center",
  gap: "10px",
  cursor: "pointer",
  fontSize: "0.9rem",
}
 
const fileUploadEmoji = {
  fontSize: "1.3rem",
  lineHeight: 1,
}
 
const processingBox = {
  width: "100%",
  maxWidth: "800px",
  marginTop: "20px",
  padding: "20px",
  background: "#111827",
  borderRadius: "12px",
  border: "1px solid #334155",
};

const progressOuter = {
  width: "100%",
  height: "24px",
  background: "#1e293b",
  borderRadius: "10px",
  overflow: "hidden",
  marginTop: "10px",
};

const progressInner = {
  height: "100%",
  background: "#38bdf8",
  transition: "width .3s",
};

const processingFile = {
  marginTop: "12px",
  marginBottom: "14px",
  padding: "10px 12px",
  background: "rgba(30,41,59,.6)",
  borderRadius: "8px",
  color: "#e2e8f0",
  fontSize: "13px",
  fontWeight: "500",
  wordBreak: "break-word",
};

const stepsContainer = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  marginTop: "10px",
};

const stepItem = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  color: "#cbd5e1",
  fontSize: "13px",
};

const completedStep = {
  color: "#22c55e",
  fontWeight: "600",
};

const pendingStep = {
  color: "#facc15",
  fontWeight: "500",
};

const processingCard = {
  marginTop: "18px",
  padding: "18px",
  borderRadius: "14px",
  background: "rgba(15,23,42,0.95)",
  border: "1px solid rgba(56,189,248,0.25)",
  boxShadow: "0 8px 24px rgba(0,0,0,.25)",
};

const deleteBtn = {
    marginLeft: 10,
    width: 32,
    height: 32,
    borderRadius: "50%",
    border: "none",
    background: "#ef4444",
    color: "#fff",
    cursor: "pointer",
    fontSize: 14,
    fontWeight: "bold",
};

const zipErrorStyle = {
    color: "#ff4d4f",
    fontWeight: "700",
    fontSize: "15px",
    marginTop: "14px",
    textAlign: "center",
    textShadow:
        "0 0 6px rgba(255,77,79,.8), 0 0 12px rgba(255,77,79,.7), 0 0 20px rgba(255,77,79,.6)",
    animation: "glowText 1.2s ease-in-out infinite alternate",
};


export default function AutomaticResumeTracker() {
  const [zipFile, setZipFile] = useState(null);
  const [destination, setDestination] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [isExtracting, setIsExtracting] = useState(false);
  const [percentage, setPercentage] = useState(0);
  const [recentFiles, setRecentFiles] = useState([]);
  const [showFolders, setShowFolders] = useState(false);
  const [readingFolder, setReadingFolder] = useState(null) ;
  const [previewFolder, setPreviewFolder] = useState(null);
  const fileInputRef = useRef(null);
  const [folders, setFolders] = useState([]);
  const [previewData, setPreviewData] = useState(null);
  const [filter, setFilter] = useState("all");
  const [stats, setStats] = useState({total: 0,processed: 0,failed: 0,});
  const [currentFile, setCurrentFile] = useState("");
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [processing, setProcessing] = useState(false);
  const [processingSteps, setProcessingSteps] = useState([
  { name: "Reading Resume", done: false },
  { name: "Extracting Text", done: false },
]);
  const [zipError, setZipError] = useState(false);


  useEffect(() => {

    async function initialize() {

        await resetApplication();
        //setZipFile(null);
       // setDestination("");
       // setStatusMessage("Select a file and click Extract.");
        //setShowFolders(false);
        //setPreviewFolder(null);
       // setPreviewData(null);
        setRecentFiles([]);
        setFolders([]);
        setStats({
            total: 0,
            processed: 0,
            failed: 0,
        });
        setShowFolders(false);
    }
    initialize();
}, []);

  async function loadStatistics() {
  try {
    const data = await getStatistics();

    setStats({
      total: data.total,
      processed: data.processed,
      failed: data.failed,
    });
  } catch (err) {
    console.error("Statistics error:", err);
  }
}

  async function loadRecentFiles() {
  try {
    const files = await getRecentFiles();
    setRecentFiles(files);
  } catch (err) {

    console.error("Recent files error:", err);

  }
}


  const filteredRecentFiles =
   filter === "pdf"
    ? recentFiles.filter(file =>
        file.filename.toLowerCase().endsWith(".pdf")
      )
    : filter === "docx"
    ? recentFiles.filter(file =>
        file.filename.toLowerCase().endsWith(".docx")
      )
    : recentFiles;
  

  useEffect(() => {

    loadStatistics();
    loadRecentFiles();

  }, []);

  const handleBrowse = (event) => {
    const file = event.target.files?.[0]
    if (file) {
      setZipFile(file)
      setZipError(false);

      setStatusMessage(`Ready to extract: ${file.name}`)
      setShowFolders(false)
      setPreviewFolder(null)
    }
  }

  const handleExtract = async () => {
  /*if (!zipFile) {

    setZipError(true);

    setTimeout(() => {
        setZipError(false);
    }, 2500);

    return;
}
  if (!zipFile) {
    setStatusMessage("Please choose a ZIP file");
    return;
  }*/

  if (!zipFile) {
    alert("Please select a ZIP file.");
    return;
}

  try {
    setIsExtracting(true);
    setPercentage(10);
    //setPercentage(40);
  
    // check existing folders first
const existingFolders = await listFolders();
const targetFolder =
    destination.trim() ||
    zipFile.name.replace(".zip", "");

const folderExists = existingFolders.some(
    f =>
        f.folder_name.toLowerCase() ===
        targetFolder.toLowerCase()
);

if (folderExists) {
    alert("This folder already exists.");
    return;
}

const { upload_url, filename } = await getUploadUrl(zipFile.name);
await uploadToB2(upload_url, zipFile);

await extractZip(
    filename.replace(".zip", ""),
    targetFolder
);

setPercentage(80);

// reload folders AFTER extraction
const updatedFolders = await listFolders();

setFolders(updatedFolders);

setShowFolders(true);

await loadRecentFiles();
    setPercentage(100);
    setStatusMessage("Extraction completed.");

  } catch (err) {
    console.error(err);
    setStatusMessage(
        err.message || "Extraction failed.");
  } finally {

    setTimeout(() => {
      setIsExtracting(false);
      setPercentage(0);
    }, 500);
  }
};

  function updateSteps(message) {
    setProcessingSteps([
        {
            name: "Reading Resume",
            done: message !== ""
        },
        {
            name: "Extracting Text",
            done: message.includes("Extracting")
        }, 
    ]);
}

  const handleGenerate = async (folderName) => {
    let interval;
    try {
        setReadingFolder(folderName);
        setProcessing(true);
        interval = setInterval(async () => {
            const p = await getProgress();
            setProgress(p.progress);
            setProgressMessage(p.message);
            setCurrentFile(p.current_file || "");
            // Update processing steps
            updateSteps(p.message);
            if (p.status === "done") {
                clearInterval(interval);
            }
        }, 300);
        const preview = await getPreview(folderName);
        setPreviewData(preview);
        setPreviewFolder(folderName);
        await loadStatistics();
        await loadRecentFiles();
    } catch (err) {
        alert(err.message);
    } finally {
        clearInterval(interval);
        setReadingFolder(null);
        setProcessing(false);

    }

};
/*
const handleDeleteFolder = async (folder_name) => {
    if (!window.confirm(`Delete "${folder_name}"?`))
        return;

    try {
        await deleteFolder(folder_name);
        setFolders(prev =>
            prev.filter(f => f.folder_name !== folder_name)
        );
        setRecentFiles(prev =>
            prev.filter(f => f.folder_name !== folder_name)
        );
    } catch (err) {
        console.error(err);
        alert("Unable to delete folder.");
    }
};
*/
  return (
    <div style={container}>
      {/* PAGE HEADING */}
      <div style={containerTitle}>
        <h1 style={containerTitleText}>Automatic Resume Tracker</h1>
      </div>

      <div style={contentWrapper}>
        {/* LEFT SIDEBAR */}
        <motion.div
          style={leftSidebar}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h2 style={sidebarTitle}>Recent Files</h2>
          
          {recentFiles.length === 0 ? (
    <div style={sidebarItem}>No recent files</div>
) : (
    filteredRecentFiles.map((file) => (
        <div
            key={file.path}
            style={sidebarItem}
            onClick={() => openRecentFile(file.path)}
        >
            {file.filename}
        </div>
    ))
)}

          <h2 style={{ ...sidebarTitle, marginTop: "30px" }}>Filters</h2>
          <div
    style={sidebarItem}
    onClick={() => setFilter("all")}
>
    ✓ All Files
</div>

<div
    style={sidebarItem}
    onClick={() => setFilter("pdf")}
>
    PDF Only
</div>

<div
    style={sidebarItem}
    onClick={() => setFilter("docx")}
>
    DOCX Only
</div>
        </motion.div>

        {/* CENTER CONTENT */}
        <div style={centerContent}>
          <motion.div
            style={card}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div style={header}>
              <p style={subtitle}>Extract Zip files</p>
            </div>

            <div style={field}>
              <label style={label}>Choose ZIP file</label>
              <input type= "File" accept=".zip" ref={fileInputRef} onChange={handleBrowse} style={{display:"none"}} 
              disabled={readingFolder !== null}
              />
              
              <motion.button
                type="button"
                style={fileUploadBtn}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => fileInputRef.current?.click()}
                
              >
                
                <span style={fileUploadEmoji}>📁</span>
                {zipFile ? zipFile.name : "No file chosen"}
              </motion.button>
              {zipFile ? <span style={{ color: "#94a3b8" }}>✓ {zipFile.name}</span> : null}
            </div>

            <div style={field}>
              <label style={label}>Destination folder</label>
              <input
                type="text"
                placeholder="output folder"
                value={destination}
                onChange={(event) => setDestination(event.target.value)}
                style={input}
                disabled={readingFolder !== null}
              />
            </div>
            
            <motion.button
              style={{...button, opacity: readingFolder?0.5:1, cursor: readingFolder ? "not-allowed" : "pointer",
}}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleExtract}
              disabled={readingFolder !== null}
              
            >
              {isExtracting ? `Extracting... ${percentage}%` : "Extract"}
              
            </motion.button>
            {zipError && (
    <div style={zipErrorStyle}>
        Please select a ZIP file.
    </div>
)}

            {isExtracting && (
              <div style={{ marginTop: "15px", width: "100%" }}>
                <progress value={percentage} max={100} style={{ width: "100%", height: "8px" }} />
                <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>{percentage}%</span>
              </div>
            )}
            
            <AnimatePresence mode="wait">
              <motion.div
                key={statusMessage}
                style={statusBox}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                {statusMessage}
              </motion.div>
            </AnimatePresence>
          </motion.div>
        </div>
        
        {/* RIGHT SIDEBAR */}
        <motion.div
          style={rightSidebar}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h2 style={{ ...sidebarTitle, marginTop: "2px" }}>Extracted zip file</h2>
                    {showFolders ? (    
                     folders.map((folder) => (
                     <div style={folderRow} key={folder.folder_name}>
                     <Folder size={20} color="#38bdf8"/>

                     <span style={folderName}>
                       {folder.folder_name}
                      </span>
      
                     <div
                      style={{
                      display: "flex",
                      alignItems: "center",
                       gap: "8px",
                       }}
                       >
                      <button
                        style={generateBtn}
                         onClick={() => handleGenerate(folder.folder_name)}
                        >
                        {readingFolder === folder.folder_name ? (
                         <Loader2 size={13} className="spin" />
                            ) : (
                           <FileSpreadsheet size={13} />
                           )}

                          {readingFolder === folder.folder_name ? "Reading" : "Generate"}
                          </button>

    
                        </div>
                        </div>
                        ))
                         ) : (
                           <p style={{ fontSize: "0.7rem", color: "#64748b" }}>
                             Extract a zip to see its folders here.
                              </p>
                             )}
          <h2 style={{...sidebarTitle, marginTop: "50px"}}>Statistics</h2>
          <div
            style={{
             ...sidebarItem,
             background: "rgba(56,189,248,.15)",
              color: "#38bdf8",
              fontWeight: 600
         }}
         >

         📊 Total: {stats.total}
       </div>

        <div
         style={{
           ...sidebarItem,
           background: "rgba(34,197,94,.15)",
           color: "#22c55e",
           fontWeight: 600
          }}
           >
            ✓ Processed: {stats.processed}
            </div>

          <div
             style={{
                    ...sidebarItem,
                     background: "rgba(239,68,68,.15)",
                     color: "#ef4444",
                     fontWeight: 600
                     }}
                    >
                     ✗ Failed: {stats.failed}
                    </div>
                    {processing && (
             <div style={processingCard}>
             <h3>Resume Processing</h3>
             <div style={progressOuter}>
              <div
                 style={{
                      ...progressInner,
                     width: `${progress}%`,
                 }}
            />
                 </div>

               <div>{progress}% Completed</div>

               <div style={processingFile}>
                 📄 {currentFile}
               </div>

               <div style={stepsContainer}>
                {processingSteps.map((step) => (
                 <div
                  key={step.name}
                 style={{
                 ...stepItem,
                 ...(step.done ? completedStep : pendingStep),
                  }}
                  >
                  {step.done ? "✔" : "⏳"} {step.name}
               </div>
            ))}
           </div>

          </div>
          )}
                            </motion.div>
                             </div>
        

                           <AnimatePresence>
                              {previewFolder && (
                              <Preview folderName={previewFolder} previewData={previewData} onClose={() => setPreviewFolder(null)} />
                           )}
                           </AnimatePresence>
      

                            {/* Spinner keyframes for the Loader2 icon */}
                         <style>{`
.spin{
    animation: spin .8s linear infinite;
}

@keyframes spin{
    to{
        transform:rotate(360deg);
    }
}

@keyframes glowText{
    from{
        opacity:.5;
        text-shadow:
            0 0 5px #ff4d4f,
            0 0 10px #ff4d4f,
            0 0 15px #ff4d4f;
                         }
    to{
        opacity:1;
        text-shadow:
            0 0 10px #ff4d4f,
            0 0 20px #ff4d4f,
            0 0 30px #ff4d4f,
            0 0 40px #ff4d4f;
    }
}
`}</style>
                             </div>
                             )
                              }
