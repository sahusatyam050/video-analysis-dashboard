import requests
import time

print("Starting crawl...")
resp = requests.post("http://127.0.0.1:8000/crawl", json={"url": "https://www.indoplay.io", "duration": 40})
task_id = resp.json()["task_id"]
print("Task ID:", task_id)

while True:
    status_resp = requests.get(f"http://127.0.0.1:8000/status/{task_id}")
    data = status_resp.json()
    status = data.get("status")
    c_state = data.get("crawler_state")
    
    print(f"Status: {status}, Crawler State: {c_state}")
    
    if c_state == "waiting_for_otp":
        print("Crawler is waiting for OTP! Simulating OTP submission...")
        requests.post(f"http://127.0.0.1:8000/submit_otp/{task_id}", json={"otp": "123456"})
        print("OTP submitted.")
        time.sleep(2) # let it process
    
    if status == "complete":
        print("Crawl complete!")
        break
    elif status == "error":
        print("Error:", data.get("error_message"))
        break
        
    time.sleep(2)
