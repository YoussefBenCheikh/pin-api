from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from apscheduler.jobstores.base import JobLookupError

from utils.scheduler import scheduler
from schemas.pin_schema import PinRequest
from services.pin_service import create_pin

router = APIRouter(prefix="/pins", tags=["pins"])

@router.post("/schedule-pin")
def schedule_pin(pin: PinRequest):
    if pin.scheduled_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="scheduled_time must be in the future")

    job = scheduler.add_job(
        create_pin,
        "date",
        run_date=pin.scheduled_time,
        args=[pin],
    )
    return {"message": "Pin scheduled", "job_id": job.id, "run_at": pin.scheduled_time}


@router.get("/scheduled")
def list_scheduled_pins():
    jobs = scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "next_run_time": job.next_run_time,
            "func": str(job.func_ref),
            "args": [str(a) for a in job.args],
        }
        for job in jobs
    ]


@router.delete("/scheduled/{job_id}")
def cancel_scheduled_pin(job_id: str):
    try:
        scheduler.remove_job(job_id)
        return {"message": f"Job {job_id} cancelled"}
    except JobLookupError:
        raise HTTPException(status_code=404, detail="Job not found")
