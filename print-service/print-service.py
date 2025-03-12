import requests
import time
import io
import win32print
import win32ui
from PIL import Image, ImageWin
from dotenv import load_dotenv
import os

# Get the full path of the .env file in the same directory as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")

# Load environment variables from the specified .env file
load_dotenv(env_path)

BASE_URL = os.getenv("PHOTO_BOOTH_BASE_URL")
USERNAME = os.getenv("PHOTO_BOOTH_USERNAME")
PASSWORD = os.getenv("PHOTO_BOOTH_PASSWORD")

def get_token():
    while True:
        try:
            response = requests.post(f"{BASE_URL}/api/v1/auth/token", json={"username": USERNAME, "password": PASSWORD})
            response.raise_for_status()
            return response.json()['token']
        except Exception as e:
            time.sleep(10)
            print(f"Error: {e}")

def print_image_from_bytes(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))

    printer_name = win32print.GetDefaultPrinter()

    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    hDC.StartDoc("Image_Print")
    hDC.StartPage()

    printable_area = hDC.GetDeviceCaps(8), hDC.GetDeviceCaps(10)
    printer_size = hDC.GetDeviceCaps(110), hDC.GetDeviceCaps(111)

    scale = min(printable_area[0] / img.size[0], printable_area[1] / img.size[1])

    scaled_width, scaled_height = [int(scale * i) for i in img.size]
    x = int((printer_size[0] - scaled_width) / 2)
    y = int((printer_size[1] - scaled_height) / 2)

    dib = ImageWin.Dib(img)
    dib.draw(hDC.GetHandleOutput(), (x, y, x + scaled_width, y + scaled_height))

    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()

def make_request_with_retry(url, method="get", headers=None, json=None):
    while True:
        if method.lower() == "get":
            res = requests.get(url, headers=headers)
        elif method.lower() == "post":
            res = requests.post(url, json=json, headers=headers)
        elif method.lower() == "delete":
            res = requests.delete(url, headers=headers)
        
        if res.status_code == 429:
            print("Rate limit exceeded, retrying after 1 second...")
            time.sleep(1)
            continue

        if res.status_code == 401 or res.status_code == 403:
            raise Exception("Not authenticated")

        res.raise_for_status()
        return res

def main():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        try:
            res = make_request_with_retry(f"{BASE_URL}/api/v1/print", headers=headers)
            prints = res.json()
            if not prints:
                time.sleep(1)
                continue

            oldest_print = sorted(prints, key=lambda x: x["created_at"])[0]
            img_id = oldest_print["img_id"]
            print_id = oldest_print["id"]

            img_res = make_request_with_retry(f"{BASE_URL}/api/v1/image/{img_id}", headers=headers)
            print_image_from_bytes(img_res.content)
            print(f"Printed image: {img_id}")

            del_res = make_request_with_retry(f"{BASE_URL}/api/v1/print/{print_id}", method="delete", headers=headers)
            print(f"Deleted print: {img_id}")

        except Exception as e:
            if "Not authenticated" in str(e):
                print("Token expired. Getting new token.")
                token = get_token()
                headers = {"Authorization": f"Bearer {token}"}
            else:
                print(f"Error: {e}")

        time.sleep(1)

if __name__ == '__main__':
    main()
