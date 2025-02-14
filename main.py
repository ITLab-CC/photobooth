import sys
from PIL import Image
from img_processing import IMGReplacer

def main() -> None:
    # Define file paths
    input_image_path = "./image.png"           # Original image from which you want to remove background
    new_background_path = "./new_background.jpg"  # The new background you want to add
    output_final_path = "./final_image.png"     # Where you will store the final composite

    # Read images
    input_img = Image.open(input_image_path)
    background_img = Image.open(new_background_path)

    # Create an instance of IMGReplacer (assuming the class is in the same file or imported)
    replacer = IMGReplacer(refine_foreground=False)

    # 1) Remove background from the input image
    final_img = replacer.replace_background(input_img, background_img)

    # 2) Save the final composite image
    final_img.save(output_final_path)
    print(f"Final composite image saved to: {output_final_path}")


if __name__ == "__main__":
    # If you want to optionally pass paths via command line, you could do so here.
    # For simplicity, we’re using the hard-coded paths above.
    main()
