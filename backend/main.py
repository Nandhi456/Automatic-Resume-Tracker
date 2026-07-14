import os
import re
from typing import Any, Dict, List
import docx
import pandas as pd
#import spacy
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from schemas import (ExtractRequest, ExtractResponse, FolderFile, RecentFiles, Statistics, PreviewData, SearchRequest)
import pymupdf 
import zipfile
import shutil
from fastapi.responses import FileResponse
from datetime import datetime
from pathlib import Path
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from datetime import datetime




app = FastAPI(title="Resume Tracker API")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "https://automatic-resume-tracker.vercel.app"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

LAST_RESULT={}

APP_STATS = {
    "total": 0,
    "processed": 0,
    "failed": 0,
}

JOB_STATUS = {
    "status": "idle",
    "progress": 0,
    "message": "",
    "current_file": ""
}
 
#nlp = spacy.load("en_core_web_sm")


def extract_text_from_pdf(path):
    text = ""
    try:
        doc = pymupdf.open(path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception:
        return ""
    return text.strip()


def extract_text_from_docx(path):
    try:
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs]).strip()
    except:
        return ""



def extract_email(text):
    matches = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}", text)
    return matches[0] if matches else ""

def extract_phone(text):

    match = re.search(
        r'(\+\d{1,3}[\s-]?)?\d{10}',
        text
    )

    if match:
        return match.group().strip()

    return ""


def extract_linkedin(text):

    match = re.search(
        r'(https?://)?(www\.)?linkedin\.com/[^\s|]+',
        text,
        re.I
    )

    if match:
        return match.group(0)

    return ""

# ✅ Improved name extraction
def extract_name(text):

    lines = text.split("\n")

    blacklist = [
        "phone","mobile","email","linkedin",
        "skills","education","experience",
        "objective","summary","profile",
        "curriculum vitae","resume",
        "core competencies",
        "software developer",
        "station controller",
        "requirement engineer",
        "validation",
        "bangalore",
        "hyderabad",
        "india",
        "customer requirements",
        "Inc"
    ]

    for line in lines[:20]:

        line = line.strip()

        if not line:
            continue

        lower_line = line.lower()

        if any(word in lower_line for word in blacklist):
            continue

        if '@' in line:
            continue

        if re.search(r'\d', line):
            continue

        words = line.split()

        if 2 <= len(words) <= 5:

            if all(
                word.replace('.', '').isalpha()
                for word in words
            ):
                return line

    return ""

from datetime import datetime

def extract_experience(text):

    # --------------------------------
    # Case 1: Explicit experience
    # --------------------------------

    explicit = re.findall(
        r'(\d+)\s*\+?\s*(?:years?|yrs?)',
        text,
        re.I
    )

    if explicit:
        exp = max(map(int, explicit))

        if exp < 50:
            return exp

    # --------------------------------
    # Case 2: DD/MM/YYYY date ranges
    # --------------------------------

    ddmmyyyy = re.findall(
        r'(\d{2}/\d{2}/\d{4})\s*[–-]\s*(Current|Present|\d{2}/\d{2}/\d{4})',
        text,
        re.I
    )

    if ddmmyyyy:

        starts = []
        ends = []

        for start, end in ddmmyyyy:

            try:

                start_dt = datetime.strptime(
                    start,
                    "%d/%m/%Y"
                )

                if end.lower() in [
                    "current",
                    "present"
                ]:
                    end_dt = datetime.today()

                else:
                    end_dt = datetime.strptime(
                        end,
                        "%d/%m/%Y"
                    )

                starts.append(start_dt)
                ends.append(end_dt)

            except:
                pass

        if starts and ends:

            min_start = min(starts)
            max_end = max(ends)

            return round(
                (max_end - min_start).days
                / 365.25
            )

    # --------------------------------
    # Case 3: Month Year format
    # --------------------------------

    month_pattern = re.findall(

        r'((?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)\s+\d{4})\s*[–-]\s*(Present|Current|(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)\s+\d{4})',

        text,
        re.I
    )

    if month_pattern:

        starts = []
        ends = []

        for start, end in month_pattern:

            try:

                try:
                    start_dt = datetime.strptime(
                        start,
                        "%B %Y"
                    )
                except:
                    start_dt = datetime.strptime(
                        start,
                        "%b %Y"
                    )

                if end.lower() in [
                    "present",
                    "current"
                ]:
                    end_dt = datetime.today()

                else:

                    try:
                        end_dt = datetime.strptime(
                            end,
                            "%B %Y"
                        )
                    except:
                        end_dt = datetime.strptime(
                            end,
                            "%b %Y"
                        )

                starts.append(start_dt)
                ends.append(end_dt)

            except:
                pass

        if starts and ends:

            return round(
                (
                    max(ends) - min(starts)
                ).days / 365.25
            )

    # --------------------------------
    # Case 4: YYYY-YYYY
    # --------------------------------

    years = re.findall(
        r'(20\d{2})\s*[-–]\s*(20\d{2}|Present|Current)',
        text,
        re.I
    )

    if years:

        starts = []
        ends = []

        for start, end in years:

            starts.append(int(start))

            if str(end).lower() in [
                "present",
                "current"
            ]:
                ends.append(datetime.today().year)

            else:
                ends.append(int(end))

        return max(ends) - min(starts)

    return 0
import re

def get_experience_section(text):

    patterns = [

        r'professional\s+experience(.*?)(education|certifications|skills|languages|$)',

        r'work\s+experience(.*?)(education|certifications|skills|languages|$)',

        r'employment\s+history(.*?)(education|certifications|skills|languages|$)'

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I | re.S
        )

        if match:

            return match.group(1)

    return text


def extract_qualification(text):

    degrees = [

        r'\bB\.?\s*TECH\b',
        r'\bM\.?\s*TECH\b',
        r'\bB\.?\s*E\b',
        r'\bM\.?\s*E\b',
        r'\bMBA\b',
        r'\bPGDM\b',
        r'\bMCA\b',
        r'\bBCA\b',
        r'\bBSC\b',
        r'\bMSC\b',
        r'\bBA\b',
        r'\bMA\b',
        r'\bDME\b',
        r'\bDEE\b',
        r'\bDCS\b'
        r'\bDCE\b',



    ]

    results = []

    for pattern in degrees:

        matches = re.findall(
            pattern,
            text,
            re.I
        )

        for match in matches:

            match = match.upper().replace(" ", "")

            if match not in results:
                results.append(match)

    return ", ".join(results)

KNOWN_LOCATIONS = {

    # India
    "bangalore",
    "bengaluru",
    "hyderabad",
    "chennai",
    "mumbai",
    "delhi",
    "kolkata",
    "pune",
    "vijayawada",
    "visakhapatnam",
    "guntur",
    "tirupati",
    "chittoor",
    "rajahmundry",
    "kurnool",
    "ananthapuramu",
    "medak",
    "hubli",
    "hosur",
    "lucknow",

    # States
    "telangana",
    "karnataka",
    "tamil nadu",
    "andhra pradesh",
    "maharashtra",
    "west bengal",

    # Countries
    "india",
    "germany",
    "france",
    "usa",
    "china",
    "japan",
    "italy",
    "belgium",
    "spain",
    "australia",
    "sweden",
    "south korea",
    "czech republic",
    "united kingdom",
    "dubai"
}
def extract_location(text):

    locations = []
    seen = set()

    text_lower = text.lower()

    for loc in KNOWN_LOCATIONS:

        if re.search(
            r'\b' + re.escape(loc) + r'\b',
            text_lower
        ):

            proper_name = loc.title()

            if loc not in seen:
                locations.append(proper_name)
                seen.add(loc)

    return ", ".join(locations)

def extract_skills(text):
    keywords = [
        "python", "java", "c++", "embedded", "linux",
        "hardware", "sql", "machine learning", "c", "matlab", ".net", "dotnet", "qt", "qml", "java script", 'html', 'reactjs'
    ]
    text_lower = text.lower()
    found = list(set([k for k in keywords if k in text_lower]))
    return ", ".join(found)


def categorize(text):

    text = text.lower()

    if any(
        k in text
        for k in [
            "embedded",
            "firmware",
            "rtos",
            "qt",
            "qml"
        ]
    ):
        return "Embedded"

    if any(
        k in text
        for k in [
            "hardware",
            "pcb",
            "electronics"
        ]
    ):
        return "Hardware"

    if any(
        k in text
        for k in [
            "cyber security",
            "soc",
            "siem"
        ]
    ):
        return "Cyber Security"

    if any(
        k in text
        for k in [
            "devops",
            "docker",
            "kubernetes",
            "jenkins"
        ]
    ):
        return "DevOps"

    if any(
        k in text
        for k in [
            "machine learning",
            "data science",
            "tensorflow",
            "pytorch"
        ]
    ):
        return "Data Science"
    return "Software"

def clean_excel_text(value):
    if isinstance(value, str):
        value = ILLEGAL_CHARACTERS_RE.sub("", value)
        value = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', value)
        value = value.strip()
    return value

def process_resumes(folder_path):
    files = os.listdir(folder_path)
    raw_data=[]
    failed_files=[]

    files=os.listdir(folder_path)

# Handle ZIPs that extract into a nested folder
    if len(files) == 1:
       nested = os.path.join(folder_path, files[0])

       if os.path.isdir(nested):
        folder_path = nested
        #files = os.listdir(folder_path)
        #raw_data = []
        #failed_files = []

    files = os.listdir(folder_path)
    total=len(files)

    if not files:
       JOB_STATUS["status"] = "done"
       JOB_STATUS["progress"] = 100


    JOB_STATUS["status"] = "processing"

    for i, file in enumerate(files):

        JOB_STATUS["progress"] = int((i / total) * 100)
        JOB_STATUS["current_file"] = file
        JOB_STATUS["message"] = f"Reading {file}"

   # print(f"📁 Found {len(files)} files\n")

        path = os.path.join(folder_path, file)

        if os.path.isdir(path):
            continue

       # print(f"📄 Processing: {file}")
        JOB_STATUS["message"] = "Extracting text..."

        # ---- Extract text ----
        if file.endswith(".pdf"):
            text = extract_text_from_pdf(path)
        elif file.endswith(".docx"):
            text = extract_text_from_docx(path)
        else:
            failed_files.append((file, "Unsupported format"))
            continue

        if not text or len(text) < 50:
            failed_files.append((file, "No readable text"))
            continue

        # ---- Extract fields ----
        name = extract_name(text)
        email = extract_email(text)
        phone = extract_phone(text)
        linkedin = extract_linkedin(text)
        exp_text = get_experience_section(text)
        exp = extract_experience(exp_text)
        qual = extract_qualification(text)
        location = extract_location(text)
        skills = extract_skills(text)
        category = categorize(text)

        JOB_STATUS["message"] = "Extracting candidate details..."

        # ---- Clean invalid values ----
        if len(name) > 40 or name.lower() in ["resume", "curriculum vitae"]:
            name = ""

        # ---- Confidence Score ----
        score = 0
        if name: score += 1
        if email: score += 1
        if phone: score += 1
        if skills: score += 1

        row = {
            "FileName": file,
            "Name": name,
            "Email": email,
            "Phone": phone,
            "LinkedIn": linkedin,
            "Qualification": qual,
            "Experience": exp,
            "Category": category,
            "Location": location,
            "Skills": skills,
            "Score": score
        }

        raw_data.append(row)

    # ===============================
    # ✅ RAW DATAFRAME (Before cleaning)
    # ===============================
    raw_df = pd.DataFrame(raw_data)
    if raw_df.empty:
      return {
        "folder_name": folder_path,
        "columns": [],
        "rows": [],
        "total_files": len(files),
        "raw_records": 0,
        "cleaned_records": 0,
        "removed": 0,
        "failed_files": len(failed_files),
    }

   # print(f"\n📊 Raw extracted records: {len(raw_df)}")

    # ===============================
    # ✅ CLEANING PIPELINE
    # ===============================

    JOB_STATUS["progress"] = 70
    JOB_STATUS["message"] = "Cleaning extracted data..."

    clean_df = raw_df.copy()

    # 1. Remove low-quality records
    clean_df = clean_df[clean_df["Score"] >= 2]

    # 2. Ensure at least email OR phone exists
    clean_df = clean_df[
        (clean_df["Email"] != "") | (clean_df["Phone"] != "")
    ]

    # 3. Remove invalid experience
    clean_df = clean_df[(clean_df["Experience"] >= 0) & (clean_df["Experience"] <= 40)]

    # 4. Remove empty names if email also weak
    clean_df = clean_df[~((clean_df["Name"] == "") & (clean_df["Email"] == ""))]

    # 5. Remove duplicates (email priority, then phone)
    clean_df = clean_df.sort_values(by="Score", ascending=False)

    clean_df = clean_df.drop_duplicates(subset=["Email"], keep="first")
    clean_df = clean_df.drop_duplicates(subset=["Phone"], keep="first")

    # 6. Final cleanup (strip spaces)
    clean_df = clean_df.map(
    lambda x: x.strip() if isinstance(x, str) else x
)

    # ===============================
    # ✅ ADD SERIAL NUMBER
    # ===============================
    clean_df.insert(0, "S.No", range(1, len(clean_df) + 1))

    

    # ===============================
    # ✅ SAVE CLEAN OUTPUT
    # ===============================

    # ===============================
    # ✅ PROCESSING REPORT
    # ===============================
    report = pd.DataFrame({
        "Failed File": [f[0] for f in failed_files],
        "Reason": [f[1] for f in failed_files]
    })

    

    APP_STATS["total"] = len(files)
    APP_STATS["processed"] = len(clean_df)
    APP_STATS["failed"] = len(failed_files)

    
    JOB_STATUS["progress"] = 100
    JOB_STATUS["status"] = "done"
    JOB_STATUS["message"] = "Completed"


    # ===============================
    # ✅ SUMMARY
    # ===============================
    return {
    "folder_name": folder_path,
    "columns": clean_df.columns.tolist(),
    "rows": clean_df.to_dict(orient="records"),
    "total_files": len(files),
    "raw_records": len(raw_df),
    "cleaned_records": len(clean_df),
    "removed": len(raw_df) - len(clean_df),
    "failed_files": len(failed_files),
}


@app.get("/api/folders")
def folder_names():
    folders = []
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            path = os.path.join(UPLOAD_DIR, f)
            if os.path.isdir(path):
                folders.append({
                    "folder_name": f,
                    "file_count": len(os.listdir(path))   # <-- one extra listdir per folder
                })
    return folders


@app.post("/api/extract")
def extract_zip_file(payload: ExtractRequest):

    folder_name = payload.folder_name
    destination_name = payload.destination_name or folder_name

    zip_path = os.path.join(UPLOAD_DIR, folder_name + ".zip")
    extract_path = os.path.join(UPLOAD_DIR, destination_name)

    os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)

    file_count = len(os.listdir(extract_path))
 
    return ExtractResponse(
        folder_name=destination_name,
        file_count=file_count

@app.get("/api/folders")
def folder_names():

    folders = []

    if os.path.exists(UPLOAD_DIR):

        for f in os.listdir(UPLOAD_DIR):

            path = os.path.join(UPLOAD_DIR, f)

            if os.path.isdir(path):
                folders.append({
                    "folder_name": f,
                    "file_count": len(os.listdir(path))
                })

    return folders



@app.get("/api/recent_files")
def recent_files():

    files = []

    if not os.path.exists(UPLOAD_DIR):
        return []
    seen = set()


    for root, _, filenames in os.walk(UPLOAD_DIR):
        for filename in filenames:
            if filename.lower().endswith((".pdf", ".docx")):
                full_path = os.path.join(root, filename)
                if full_path in seen:
                   continue

                seen.add(full_path)
                files.append({
                    "filename": filename,
                    "folder": os.path.basename(root),
                    "path": full_path,
                    "modified": os.path.getmtime(full_path)
                })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return files

@app.get("/api/statistics")
def statistics():

    return {
        "job_id": "latest",
        "status": "done",
        "processed": APP_STATS["processed"],
        "total": APP_STATS["total"],
        "failed": APP_STATS["failed"],
    }


@app.get("/api/generate")
def folders(folder_name: str):
    return {"folder_name": folder_name, "status": "ready"}


@app.get("/api/{folder_name}/preview", response_model=PreviewData)
def preview(folder_name: str):

    folder_path = os.path.join(UPLOAD_DIR, folder_name)

    if not os.path.exists(folder_path):
        return {"error": "Folder not found"}

    data = process_resumes(folder_path)
    LAST_RESULT[folder_name] = data

    return data

@app.post("/api/{folder_name}/search")
def search(folder_name: str, payload: SearchRequest):

    try:

        if folder_name not in LAST_RESULT:
            raise HTTPException(
                status_code=400,
                detail="Generate preview first."
            )

        data = LAST_RESULT[folder_name]

        keyword = payload.keyword.lower().strip()

        matches = []

        for row in data["rows"]:

            if any(keyword in str(v).lower() for v in row.values()):
                matches.append(row)

        return matches
    
    except HTTPException:
         raise

    except Exception as e:

        print("SEARCH ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/api/{folder_name}/export_to_excel")
def export_to_excel(folder_name: str):

    folder_path = os.path.join(UPLOAD_DIR, folder_name)

    if folder_name not in LAST_RESULT:
       raise HTTPException(400, "Generate preview first")

    data = LAST_RESULT[folder_name]

    #data = process_resumes(folder_path)

    df = pd.DataFrame(data["rows"])

    export_path = os.path.join(
        EXPORT_DIR,

        f"{folder_name}.xlsx"
    )

    df.to_excel(export_path, index=False)

    return FileResponse(
        export_path,
        filename=f"{folder_name}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.get("/api/open")
def open_file(path: str):

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path)

@app.post("/api/reset")
def reset():

    LAST_RESULT.clear()

    JOB_STATUS["status"] = "idle"
    JOB_STATUS["progress"] = 0
    JOB_STATUS["message"] = ""
    JOB_STATUS["current_file"] = ""

    APP_STATS["total"] = 0
    APP_STATS["processed"] = 0
    APP_STATS["failed"] = 0

    if os.path.exists(UPLOAD_DIR):

        for item in os.listdir(UPLOAD_DIR):

            path = os.path.join(UPLOAD_DIR, item)

            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                print(e)

    return {"message": "Application reset successfully"
            }

@app.get("/api/progress")
def progress():

    return JOB_STATUS
"""
@app.delete("/api/folders/{folder_name}")
def delete_folder(folder_name: str):

    folder_path = os.path.join(UPLOAD_DIR, folder_name)

    if folder_name not in os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    shutil.rmtree(folder_path)

    LAST_RESULT.pop(folder_name, None)

    global RECENT_FILES

    RECENT_FILES = [
        f for f in RECENT_FILES
        if f.get("folder_name") != folder_name
    ]

    return {
        "success": True,
        "message": f"{folder_name} deleted successfully."
    }"""
