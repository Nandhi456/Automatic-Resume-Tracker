import os
import re
from typing import Any, Dict, List
import docx
import pandas as pd
#import spacy
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from schemas import (ExtractRequest, ExtractResponse, FolderFile, Statistics, PreviewData, SearchRequest)
import pymupdf 
import zipfile
import shutil
from fastapi.responses import FileResponse 
from datetime import datetime
from pathlib import Path
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from datetime import datetime
import boto3
from botocore.config import Config
import io
import traceback
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
import json


app = FastAPI(title="Resume Tracker API")

@app.get("/healthz")
def health():
    return {"status": "ok"}
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "https://automatic-resume-tracker.vercel.app", "https://automatic-resume-tracker-owtq.vercel.app"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

B2_KEY_ID = os.environ["B2_KEY_ID"]
B2_APPLICATION_KEY = os.environ["B2_APPLICATION_KEY"]
B2_BUCKET_NAME = os.environ["B2_BUCKET_NAME"]
B2_ENDPOINT = os.environ["B2_ENDPOINT"]

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{B2_ENDPOINT}",
    aws_access_key_id=B2_KEY_ID,
    aws_secret_access_key=B2_APPLICATION_KEY,
    config=Config(signature_version="s3v4"),
)



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


def extract_text_from_pdf(file_bytes):
    text = ""
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception:
        return ""
    return text.strip()


def extract_text_from_docx(file_bytes):
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs]).strip()
    except:
        return ""

def save_result_to_b2(folder_name, data):
    try:
        s3.put_object(
            Bucket=B2_BUCKET_NAME,
            Key=f"results/{folder_name}.json",
            Body=json.dumps(data).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as e:
        print("SAVE RESULT ERROR:", e)

def load_result_from_b2(folder_name):
    try:
        obj = s3.get_object(Bucket=B2_BUCKET_NAME, Key=f"results/{folder_name}.json")
        return json.loads(obj["Body"].read().decode("utf-8"))
    except Exception:
        return None

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

def process_resumes(files_data):
    # files_data: list of (filename, file_bytes) tuples
    raw_data = []
    failed_files = []

    total = len(files_data)

    if not files_data:
        JOB_STATUS["status"] = "done"
        JOB_STATUS["progress"] = 100

    JOB_STATUS["status"] = "processing"

    for i, (file, file_bytes) in enumerate(files_data):

        JOB_STATUS["progress"] = int((i / total) * 100) if total else 100
        JOB_STATUS["current_file"] = file
        JOB_STATUS["message"] = f"Reading {file}"
        JOB_STATUS["message"] = "Extracting text..."

        if file.lower().endswith(".pdf"):
            text = extract_text_from_pdf(file_bytes)
        elif file.lower().endswith(".docx"):
            text = extract_text_from_docx(file_bytes)
        else:
            failed_files.append((file, "Unsupported format"))
            continue

        if not text or len(text) < 50:
            failed_files.append((file, "No readable text"))
            continue

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

        if len(name) > 40 or name.lower() in ["resume", "curriculum vitae"]:
            name = ""

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

    raw_df = pd.DataFrame(raw_data)
    if raw_df.empty:
        return {
            "folder_name": "",
            "columns": [],
            "rows": [],
            "total_files": total,
            "raw_records": 0,
            "cleaned_records": 0,
            "removed": 0,
            "failed_files": len(failed_files),
        }

    JOB_STATUS["progress"] = 70
    JOB_STATUS["message"] = "Cleaning extracted data..."

    clean_df = raw_df.copy()
    clean_df = clean_df[clean_df["Score"] >= 2]
    clean_df = clean_df[(clean_df["Email"] != "") | (clean_df["Phone"] != "")]
    clean_df = clean_df[(clean_df["Experience"] >= 0) & (clean_df["Experience"] <= 40)]
    clean_df = clean_df[~((clean_df["Name"] == "") & (clean_df["Email"] == ""))]
    clean_df = clean_df.sort_values(by="Score", ascending=False)
    clean_df = clean_df.drop_duplicates(subset=["Email"], keep="first")
    clean_df = clean_df.drop_duplicates(subset=["Phone"], keep="first")
    clean_df = clean_df.map(lambda x: x.strip() if isinstance(x, str) else x)
    clean_df.insert(0, "S.No", range(1, len(clean_df) + 1))

    APP_STATS["total"] = total
    APP_STATS["processed"] = len(clean_df)
    APP_STATS["failed"] = len(failed_files)

    JOB_STATUS["progress"] = 100
    JOB_STATUS["status"] = "done"
    JOB_STATUS["message"] = "Completed"

    return {
        "folder_name": "",
        "columns": clean_df.columns.tolist(),
        "rows": clean_df.to_dict(orient="records"),
        "total_files": total,
        "raw_records": len(raw_df),
        "cleaned_records": len(clean_df),
        "removed": len(raw_df) - len(clean_df),
        "failed_files": len(failed_files),
    }
    
@app.get("/api/get_upload_url")
async def get_upload_url(filename: str):
    try:
        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": B2_BUCKET_NAME, "Key": filename},
            ExpiresIn=3600,
        )
        return {"upload_url": presigned_url, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate URL: {e}")
        

@app.post("/api/extract")
async def extract_zip_file(payload: ExtractRequest):

    folder_name = payload.folder_name
    destination_name = payload.destination_name or folder_name

    try:
        obj = s3.get_object(Bucket=B2_BUCKET_NAME, Key=folder_name + ".zip")
        zip_bytes = obj["Body"].read()

        file_count = 0
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_ref:
            names = zip_ref.namelist()

            # Handle nested single-folder zips
            top_level = set(n.split("/")[0] for n in names if n)
            prefix_to_strip = ""
            if len(top_level) == 1:
                only_entry = list(top_level)[0]
                if all(n.startswith(only_entry + "/") or n == only_entry for n in names):
                    prefix_to_strip = only_entry + "/"

            for name in names:
                if name.endswith("/"):
                    continue  # skip directory entries

                file_bytes = zip_ref.read(name)
                clean_name = name[len(prefix_to_strip):] if prefix_to_strip else name
                filename_only = clean_name.split("/")[-1]
                if not filename_only:
                    continue

                b2_key = f"extracted/{destination_name}/{filename_only}"
                s3.upload_fileobj(io.BytesIO(file_bytes), B2_BUCKET_NAME, b2_key)
                file_count += 1

        return ExtractResponse(
            folder_name=destination_name,
            file_count=file_count)

    except Exception as e:
        error_detail = traceback.format_exc()
        print("EXTRACT ERROR:", error_detail)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}\n\n{error_detail}")

@app.get("/api/folders")
async def folder_names():
    folders = {}

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=B2_BUCKET_NAME, Prefix="extracted/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            parts = key[len("extracted/"):].split("/")
            if len(parts) >= 2 and parts[1]:
                folder = parts[0]
                folders[folder] = folders.get(folder, 0) + 1

    return [{"folder_name": name, "file_count": count} for name, count in folders.items()]

@app.get("/api/recent_files")
async def recent_files():
    files = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=B2_BUCKET_NAME, Prefix="extracted/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            filename = key.split("/")[-1]
            if filename.lower().endswith((".pdf", ".docx")):
                parts = key[len("extracted/"):].split("/")
                folder = parts[0] if parts else ""
                files.append({
                    "filename": filename,
                    "folder": folder,
                    "path": key,
                    "modified": obj["LastModified"].timestamp()
                })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return files

@app.get("/api/statistics")
async def statistics():

    return {
        "job_id": "latest",
        "status": "done",
        "processed": APP_STATS["processed"],
        "total": APP_STATS["total"],
        "failed": APP_STATS["failed"],
    }


@app.get("/api/generate")
async def folders(folder_name: str):
    return {"folder_name": folder_name, "status": "ready"}


@app.get("/api/{folder_name}/preview", response_model=PreviewData)
async def preview(folder_name: str):
    try:
        prefix = f"extracted/{folder_name}/"
        files_data = []

        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=B2_BUCKET_NAME, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                filename = key.split("/")[-1]
                if not filename:
                    continue
                file_obj = s3.get_object(Bucket=B2_BUCKET_NAME, Key=key)
                file_bytes = file_obj["Body"].read()
                files_data.append((filename, file_bytes))

        if not files_data:
            return {"error": "Folder not found"}

        data = process_resumes(files_data)
        data["folder_name"] = folder_name
        LAST_RESULT[folder_name] = data
        save_result_to_b2(folder_name, data)

        return data

    except Exception as e:
        error_detail = traceback.format_exc()
        print("PREVIEW ERROR:", error_detail)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}\n\n{error_detail}") 
        
@app.post("/api/{folder_name}/search")
async def search(folder_name: str, payload: SearchRequest):

    try:
        data = LAST_RESULT.get(folder_name) or load_result_from_b2(folder_name)

        if data is None:
            raise HTTPException(
                status_code=400,
                detail="Generate preview first."
            )

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
async def export_to_excel(folder_name: str):

    data = LAST_RESULT.get(folder_name) or load_result_from_b2(folder_name)

    if data is None:
        raise HTTPException(400, "Generate preview first")

    df = pd.DataFrame(data["rows"])

    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{folder_name}.xlsx"'}
    )
    
@app.get("/api/open")
async def open_file(path: str):
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": B2_BUCKET_NAME, "Key": path},
            ExpiresIn=3600,
        )
        return RedirectResponse(url)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}")

@app.post("/api/reset")
async def reset():

    LAST_RESULT.clear()

    JOB_STATUS["status"] = "idle"
    JOB_STATUS["progress"] = 0
    JOB_STATUS["message"] = ""
    JOB_STATUS["current_file"] = ""

    APP_STATS["total"] = 0
    APP_STATS["processed"] = 0
    APP_STATS["failed"] = 0
    
    # Clear everything in B2 bucket (uploaded zips + extracted files)
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=B2_BUCKET_NAME):
            objects_to_delete = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if objects_to_delete:
                s3.delete_objects(
                    Bucket=B2_BUCKET_NAME,
                    Delete={"Objects": objects_to_delete}
                )
    except Exception as e:
        print("B2 RESET ERROR:", e)

    return {"message": "Application reset successfully"}

@app.get("/api/progress")
async def progress():

    return JOB_STATUS

