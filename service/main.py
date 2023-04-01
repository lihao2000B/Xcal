from collections import defaultdict
from queue import Queue
from fastapi import FastAPI
from fastapi import Body
from loguru import logger
import shutil
import subprocess
import requests
import zipfile
from pathlib import Path
import os
import json
import time
from pyexpat import model
from typing import List
from collections import defaultdict
from pathlib import Path
from queue import Queue
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, status
from io import TextIOWrapper, BytesIO

SERVICE_BASE_PATH = Path(os.path.dirname(os.path.realpath(__file__))) / "workdir"
BASE_URL = os.getenv("QUEUE_BASE_URL","http://work-queue.user-hao-li:8009")

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "CalX"}


# core
@app.post("/begin_job")
async def create_job(
    script_files: List[UploadFile] = File(..., description="Multiple files as UploadFile"),
    data_files: List[UploadFile] = File(..., description="Multiple files as UploadFile"),
    job_name: str = Form(...),
    min_data_group: int = Form(1, description="min data num which can not split"),
    work_data_num: int = Form(10000, description="data group num in a group")
):
    # send script_data
    SERVICE_BASE_PATH.mkdir(parents=True)
    payload={'job_name': job_name}
    files = []
    for file in script_files:
        with Path(SERVICE_BASE_PATH / file.filename).open("wb+") as fin:
            fin.write(await file.read())
        fin.close()

        files.append(
            (
                'files',
                (
                    file.filename,
                    open(SERVICE_BASE_PATH / file.filename, 'rb'),
                    file.content_type
                )
            )
        )

    """
    files=[ 
        ('files',('work.py',open('work.py','rb'),'application/octet-stream')),
        ('files',('123.xlsx',open('123.xlsx','rb'),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
    ]
    """
    headers = {}
    
    script_response = requests.request("POST", BASE_URL + "/create_job", headers=headers, data=payload, files=files)

    if script_response.status_code != 200:
        if SERVICE_BASE_PATH.exists():
            shutil.rmtree(SERVICE_BASE_PATH)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job already existed",
        )

    # send data
    for file in data_files:
        data_list = str((await file.read()).decode()).split(" ")
        group_count = 0
        work_data = ""
        for data in data_list:
            if group_count < min_data_group * work_data_num:
                if group_count != 0:
                    work_data += " "
                work_data += data
                group_count = group_count + 1
            if group_count == min_data_group * work_data_num:
                # process data
                if (SERVICE_BASE_PATH / file.filename).exists():
                    os.remove(SERVICE_BASE_PATH / file.filename)

                with (SERVICE_BASE_PATH / file.filename).open("wb+") as temp_file:
                    temp_file.write(work_data.encode())

                files = []
                payload={'job_name': job_name}
                files.append(
                    (
                        'data_files',
                        (
                            file.filename,
                            open(SERVICE_BASE_PATH / file.filename, 'rb'),
                            file.content_type
                        )
                    )
                )

                headers = {}
                # send data
                data_response = requests.request("POST", BASE_URL + "/push_data", headers=headers, data=payload, files=files)
                
                # init data
                os.remove(SERVICE_BASE_PATH / file.filename)
                work_data = ""
                group_count = 0
        if group_count != 0:
            # process data
            if (SERVICE_BASE_PATH / file.filename).exists():
                os.remove(SERVICE_BASE_PATH / file.filename)

            with (SERVICE_BASE_PATH / file.filename).open("wb+") as temp_file:
                temp_file.write(work_data.encode())

            files = []
            payload={'job_name': job_name}
            files.append(
                (
                    'data_files',
                    (
                        file.filename,
                        open(SERVICE_BASE_PATH / file.filename, 'rb'),
                        file.content_type
                    )
                )
            )

            headers = {}
            # send data
            data_response = requests.request("POST", BASE_URL + "/push_data", headers=headers, data=payload, files=files)
            
            # init data
            os.remove(SERVICE_BASE_PATH / file.filename)
            work_data = ""
            group_count = 0
        

    if SERVICE_BASE_PATH.exists():
        shutil.rmtree(SERVICE_BASE_PATH)

    return {
        "script_response": script_response.json(),
        "data_response": data_response.json(),
        "script_files": [file.filename for file in script_files],
        "data_files": [file.filename for file in data_files]
    }


@app.get("/get_result")
def get_result(
    job_name: str = Form(...)
):
    # get result
    payload = json.dumps(job_name)
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("GET", BASE_URL + "/get_result", headers=headers, data=payload)

    result = response.json()
    
    if result["finish"] is True:
        # clear job workdir and memory
        clear_response = requests.request("GET", BASE_URL + "/finish_job", headers=headers, data=payload)
    
        if clear_response.status_code != 200:
            result.update(
                {
                    "clear_job": False
                }
            )
        else: 
            result.update(
                {
                    "clear_job": True
                }
            )
    result.update(
        {
            "clear_job": False
        }
    )

    return result


# 清理文件
# 清理内存
# 但无法终止工作进程，可以阻止接收结果
@app.get("/shutdown")
def shutdown():
    # 清理工作目录，job以工作目录是否存在为生存依据
    if SERVICE_BASE_PATH.exists():
        shutil.rmtree(SERVICE_BASE_PATH)
    
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("GET", BASE_URL + "/shutdown", headers=headers)
    result = response.json()
    return result


@app.get("/shutdown/{job_name}")
def shutdown_job(job_name: str):
    payload = json.dumps(job_name)
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("GET", BASE_URL + "/finish_job", headers=headers, data=payload)
    result = response.json()
    return result
    