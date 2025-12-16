from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from datetime import datetime, timezone

app = FastAPI(title="Pinterest OAuth Demo (no DB)")

scheduler = BackgroundScheduler()
scheduler.start()


# --- Request body schema ---
class PinRequest(BaseModel):
    access_token: str
    board_id: str
    title: str
    description: str
    link: str
    image_url: str
    scheduled_time: datetime


# --- Function to call Pinterest API ---
def create_pin(pin: PinRequest):
    url = "https://api-sandbox.pinterest.com/v5/pins"
    headers = {"Authorization": f"Bearer {pin.access_token}"}
    payload = {
        "board_id": pin.board_id,
        "title": pin.title,
        "description": pin.description,
        "link": pin.link,
        "media_source": {
            "source_type": "image_url",
            "url": pin.image_url,
        },
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code >= 400:
        print("❌ Error creating pin:", response.text)
    else:
        print("✅ Pin created:", response.json())


# --- API route to schedule a pin ---
@app.post("/schedule-pin")
def schedule_pin(pin: PinRequest):
    if pin.scheduled_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="scheduled_time must be in the future")


    scheduler.add_job(
        create_pin,
        "date",
        run_date=pin.scheduled_time,
        args=[pin],
    )

    return {"message": "Pin scheduled", "run_at": pin.scheduled_time}



from apscheduler.jobstores.base import JobLookupError

@app.get("/scheduled-pins")
def list_scheduled_pins():
    jobs = scheduler.get_jobs()
    results = []
    for job in jobs:
        results.append({
            "id": job.id,
            "next_run_time": job.next_run_time,
            "func": str(job.func_ref),
            "args": [str(a) for a in job.args],
        })
    return results


@app.delete("/scheduled-pins/{job_id}")
def cancel_scheduled_pin(job_id: str):
    try:
        scheduler.remove_job(job_id)
        return {"message": f"Job {job_id} cancelled"}
    except JobLookupError:
        raise HTTPException(status_code=404, detail="Job not found")
