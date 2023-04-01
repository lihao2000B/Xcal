import shutil
import subprocess
import requests
import zipfile
from pathlib import Path
import os
import json
import time

WORK_BASE_PATH = Path(os.path.dirname(os.path.realpath(__file__))) / "workdir"
BASE_URL = os.getenv("QUEUE_BASE_URL","http://work-queue.user-hao-li:8009")

def worker():
    while True:
        try:
            payload = ""
            headers = {}
            response = requests.request("GET", BASE_URL + "/pop_work", headers=headers, data=payload)
            if response.status_code == 200:
                if WORK_BASE_PATH.exists():
                    shutil.rmtree(WORK_BASE_PATH)
                WORK_BASE_PATH.mkdir(parents=True)
                with (WORK_BASE_PATH / "temp.zip").open("wb+") as f:
                    f.write(response.content)
                zip_file = zipfile.ZipFile(WORK_BASE_PATH / "temp.zip", "r")
                job_name = zip_file.comment.decode()
                zip_file.extractall(WORK_BASE_PATH)

                work_subprocess = subprocess.Popen(
                    ["python", "work.py"],
                    cwd=WORK_BASE_PATH,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                )
                output, error = work_subprocess.communicate()

                if error:
                    payload = json.dumps({
                        "job_name": job_name,
                        "job_result": {
                            "output": error,
                            "status": False
                        }
                    })
                    headers = {
                        'Content-Type': 'application/json'
                    }

                    response = requests.request("POST", BASE_URL + "/finish_work", headers=headers, data=payload)
                
                else:
                    payload = json.dumps({
                        "job_name": job_name,
                        "job_result": {
                            "output": output,
                            "status": True
                        }
                    })
                    headers = {
                        'Content-Type': 'application/json'
                    }

                    response = requests.request("POST", BASE_URL + "/finish_work", headers=headers, data=payload)

                zip_file.close()
                f.close()
                if WORK_BASE_PATH.exists():
                    shutil.rmtree(WORK_BASE_PATH)
            else:
                time.sleep(60)
        except Exception:
            time.sleep(60)


if __name__ == "__main__":
    worker()
