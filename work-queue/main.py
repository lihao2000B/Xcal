from pyexpat import model
import time
from typing import List
from collections import defaultdict
from pathlib import Path
from queue import Queue
from fastapi import FastAPI
from fastapi import Body
from loguru import logger
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
import os
import shutil
import zipfile
from starlette.background import BackgroundTask

app = FastAPI()

# **** job ****
work_queue = Queue()
work_result_dict = defaultdict(Queue)
work_data_dict = defaultdict(list)
job_work_count = defaultdict(int)
work_job_id_dict = defaultdict(int)
work_job_status = defaultdict(dict)


# **** worker ****
worker_status = defaultdict(str)
worker_time_stamp = defaultdict(str)
worker_list = list()
worker_id = 0

JOB_BASE_PATH = Path(os.path.dirname(os.path.realpath(__file__))) / "job"

def init():
    while not work_queue.empty():
        work_queue.get()
    work_result_dict.clear()
    work_data_dict.clear()
    job_work_count.clear()
    work_job_status.clear()
    work_job_id_dict.clear()
    if JOB_BASE_PATH.exists():
        shutil.rmtree(JOB_BASE_PATH)


@app.get("/")
def read_root():
    return {"Hello": "Queue"}


@app.get("/shutdown")
def shut_down():
    init()
    return {
        "clear": True
    }


@app.post("/create_job")
async def create_job(
    files: List[UploadFile] = File(..., description="Multiple files as UploadFile"),
    job_name: str = Form(...),
):
    job_path = JOB_BASE_PATH / job_name

    try:
        job_path.mkdir(parents=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job already existed",
        )

    for file in files:
        job_file_path = job_path / file.filename
        with job_file_path.open("wb+") as f:
            f.write(await file.read())

    work_data_dict[job_name] = [file.filename for file in files]
    job_work_count[job_name] = 0
    while not work_result_dict[job_name].empty():  
        work_result_dict[job_name].get()

    return {"filenames": [file.filename for file in files]}


@app.post("/push_data")
async def append_data(
    data_files: List[UploadFile] = File(..., description="Multiple files as UploadFile"),
    job_name: str = Form(...),
):
    job_path = JOB_BASE_PATH / job_name

    if not job_path.exists():
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job not existed, create job first",
        )
    
    job_work_count[job_name] = job_work_count[job_name] + 1
    zip_file = zipfile.ZipFile(job_path / (job_name + str(job_work_count[job_name]) + ".zip"), "w")
    zip_file.comment = job_name.encode()
    for file in work_data_dict[job_name]:
        file_path = job_path / file
        # file_path 是文件路径，file是在压缩包内的名称
        zip_file.write(file_path, file)

    (job_path / str(job_work_count[job_name])).mkdir(parents=True)
    for data_file in data_files:
        job_file_path = job_path / str(job_work_count[job_name]) / data_file.filename
        with job_file_path.open("wb+") as f:
            f.write(await data_file.read())
        zip_file.write(job_file_path, data_file.filename)

    zip_file.close()

    work_job_id_dict[job_name] = work_job_id_dict[job_name] + 1
    temp_id = work_job_id_dict[job_name]
    work_job_info = {
        "job_name": job_name,
        "work_zip_file": zip_file.filename,
        "work_job_id": "work_" + str(temp_id)
    }
    
    # update work status
    if not (("work_" + str(temp_id)) in work_job_status[job_name].keys()):
        work_job_status[job_name]["work_" + str(temp_id)] = {}

    work_job_status[job_name]["work_" + str(temp_id)].update(
        {
            "status": "waiting",
            "work_end_time_stamp": "NULL",
            "work_begin_time_stamp": "NULL"
        }
    )

    work_queue.put(work_job_info)
    return {
        "work_queue_len": job_work_count[job_name]
    }
        

@app.get("/finish_job")
def clear_job(
    job_name: str = Body(...)
):
    while not work_result_dict[job_name].empty():
        work_result_dict[job_name].get()
    work_data_dict[job_name].clear()
    job_work_count[job_name] = 0
    work_job_id_dict[job_name] = 0
    work_job_status[job_name].clear()

    temp_list = []
    while not work_queue.empty():
        temp_list.append(work_queue.get())
    
    for work in temp_list:
        if work["job_name"] != job_name:
            work_queue.put(work)
    
    job_path = JOB_BASE_PATH / job_name
    if job_path.exists():
        shutil.rmtree(job_path)
    return {
        "job_name": job_name,
        "len_job_work_count": job_work_count[job_name],
        "len_work_data_dict": len(work_data_dict[job_name])
    }


@app.get("/get_result")
def get_result(
    job_name: str = Body(...)
):
    result_list = []
    while not work_result_dict[job_name].empty():
        result_list.append(work_result_dict[job_name].get())
    
    status = False
    # 能够查询的时候进程已经被释放，count统计已经完成
    if len(result_list) == job_work_count[job_name]:
        status = True

    for result in result_list:
        work_result_dict[job_name].put(result)

    return {
        "finish": status,
        "result": result_list,
        "result_len": len(result_list),
        "total": job_work_count[job_name]
    }


@app.get("/worker")
def worker():
    return{
        "worker_list": worker_list,
        "worker_status": worker_status,
        "worker_time_stamp": worker_time_stamp
    }


@app.get("/job_status")
def job_status(
    job_name: str = Body(...)
):
    return{
        "work_job_count": work_job_id_dict[job_name],
        "work_job_status": work_job_status[job_name]
    }


# ****** worker function ******
@app.post("/finish_work")
def append_queue(
    job_name: str = Body(...),
    job_result: dict = Body(...),
    work_job_id: str = Body(...),
):
    if job_work_count[job_name] == 0:
        return {
            "queue_len": 0
        }
    
    # update work status
    work_end_time_stamp = time.asctime()
    work_job_status[job_name][work_job_id].update(
        {
            "status": "finish",
            "work_end_time_stamp": work_end_time_stamp,
            
        }
    )

    work_result_dict[job_name].put(job_result)
    return {
        "queue_len": work_result_dict[job_name].qsize()
    }


@app.get("/pop_work")
def pop_queue():
    if work_queue.empty():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Empty",
        )
    try:
        work_job_info = work_queue.get()
        
        work_zip_file = work_job_info["work_zip_file"]
        job_name = work_job_info["job_name"]

        # update work_job status
        work_begin_time_stamp = time.asctime()
        work_job_id = work_job_info["work_job_id"]
        work_job_status[job_name][work_job_id].update(
            {
                "status": "running",
                "work_begin_time_stamp": work_begin_time_stamp
            }
        )

        job_path = JOB_BASE_PATH / job_name

        return FileResponse(
            path=job_path / work_zip_file,
            headers={
                "work_job_id": work_job_id
            }
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="file not exist",
        )


@app.post("/sync_status")
def sync_status(
    worker_id: str = Body(...),
    worker_statu: str = Body(...)
):
    time_stamp = time.asctime()
    try:
        logger.info(f"Status sync worker_id: {worker_id} worker_status: {worker_statu} worker_time_stamp: {time_stamp}")
        
        worker_status[worker_id] = worker_statu
        worker_time_stamp[worker_id] = time_stamp
        
        return {
            "ack": True
        }
    except Exception:
        return{
            "ack": False
        }


@app.get("/worker_init")
def worker_init():
    global worker_id
    worker_id = worker_id + 1

    time_stamp = time.asctime()

    worker_list.append(str(worker_id))
    worker_status[str(worker_id)] = "waiting"
    worker_time_stamp[str(worker_id)] = time_stamp

    logger.info(f"Worker init, Id: {worker_id}")

    return {
        "id": str(worker_id)
    }


if JOB_BASE_PATH.exists():
    init()
