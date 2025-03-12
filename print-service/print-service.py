import requests
import win32print
import win32ui
from PIL import Image, ImageWin
import io
import time

def print_image_from_bytes(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))

    printer_name = win32print.GetDefaultPrinter()

    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    hDC.StartDoc("Print Job")
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


def main():
    api_base = "http://172.30.60.251/api/v1"

    while True:
        try:
            response = requests.get(f"{api_base}/print")
            response.raise_for_status()

            prints = response.json()
            if prints:
                oldest_print = min(prints, key=lambda x: x['created_at'])
                image_id = oldest_print['img_id']

                image_response = requests.get(f"{api_base}/image/{image_id}")
                image_response.raise_for_status()

                print_image_from_bytes(image_response.content)

        except requests.RequestException as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(1)


if __name__ == "__main__":
    main()
