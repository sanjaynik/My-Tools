import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageOps
from pyzbar.pyzbar import decode, ZBarSymbol
from concurrent.futures import ThreadPoolExecutor
import threading

# Function to convert PDF pages to JPEG images with enhanced quality
def convert_pdf_to_images(pdf_path, dpi=150):  # Lowered DPI to reduce memory usage
    try:
        images = convert_from_path(pdf_path, dpi=dpi, fmt='jpeg')
        messagebox.showinfo("Conversion Successful", "PDF has been converted to images successfully.")
        return images
    except Exception as e:
        messagebox.showerror("Conversion Error", f"An error occurred during conversion: {e}")
        return []

# Function to enhance image for better barcode detection
def enhance_image(image):
    # Convert image to grayscale and enhance it
    image = ImageOps.grayscale(image)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)  # Adjusted contrast level

    sharpness = ImageEnhance.Sharpness(image)
    image = sharpness.enhance(1.5)  # Adjusted sharpness level

    # Resize the image for better detection using a more efficient filter
    image = image.resize((int(image.width * 1.2), int(image.height * 1.2)), Image.LANCZOS)

    brightness = ImageEnhance.Brightness(image)
    image = brightness.enhance(1.1)  # Adjusted brightness level

    return image

# Function to save a single image and check for barcodes
def save_single_image(image_info):
    image, save_folder, index = image_info
    try:
        # Enhance the image to improve barcode detection
        image = enhance_image(image)

        # Detect barcode in the image
        barcodes = decode(image, symbols=[
            ZBarSymbol.QRCODE, 
            ZBarSymbol.CODE128, 
            ZBarSymbol.EAN13, 
            ZBarSymbol.EAN8, 
            ZBarSymbol.UPCA,
            ZBarSymbol.UPCE,
            ZBarSymbol.CODE39
        ])  # Expanded barcode symbols list

        if barcodes:
            barcode_value = barcodes[0].data.decode('utf-8')
            image_name = f'{barcode_value}.jpeg'
        else:
            image_name = f'page_{index + 1}.jpeg'

        # Save the image
        image_path = os.path.join(save_folder, image_name)
        image.save(image_path, format='JPEG')
        print(f"Saved image: {image_path}")
        return True

    except Exception as e:
        print(f"Error saving image {index + 1}: {e}")
        return False

# Function to save images to the selected folder using parallel processing
def save_images(images, save_folder, progress_var, progress_bar, status_label):
    try:
        if not images:
            messagebox.showwarning("No Images", "No images available to save.")
            return

        total_images = len(images)

        # Reset progress bar and status label
        progress_var.set(0)
        progress_bar['value'] = 0
        status_label.config(text="Starting save process...")
        progress_bar.update_idletasks()
        status_label.update_idletasks()

        for i, image in enumerate(images):
            image_info = (image, save_folder, i)
            result = save_single_image(image_info)

            # Forcefully clear memory after each image
            image.close()

            # Update the progress bar as each image is saved
            progress = ((i + 1) / total_images) * 100
            progress_var.set(progress)
            progress_bar['value'] = progress

            # Update the status label with the current count
            status_text = f"Saving image {i + 1} of {total_images}..."
            status_label.config(text=status_text)

            # Update the GUI
            progress_bar.update_idletasks()
            status_label.update_idletasks()

        messagebox.showinfo("Save Successful", "All images have been saved successfully.")
        status_label.config(text="Save completed successfully.")
    except MemoryError as e:
        messagebox.showerror("Memory Error", f"MemoryError: The system ran out of memory while saving images. Consider lowering the DPI or processing fewer pages.")
        status_label.config(text="Memory error occurred.")
    except Exception as e:
        messagebox.showerror("Save Error", f"An error occurred while saving images: {e}")
        status_label.config(text="Error occurred during save process.")

# GUI Application
class PDFtoJPEGConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF to JPEG Converter with Barcode Detection")
        self.root.geometry("500x400")  # Set a suitable window size

        # Initialize paths and images
        self.pdf_path = ""
        self.images = []

        # Create GUI components
        self.create_widgets()

    def create_widgets(self):
        # Frame for PDF selection
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10, padx=20, fill=tk.X)

        # Button to select the PDF file
        self.select_file_btn = tk.Button(file_frame, text="Select PDF File", command=self.select_file)
        self.select_file_btn.pack(side=tk.LEFT)

        # Label to display the selected file name
        self.selected_file_label = tk.Label(file_frame, text="No file selected.", wraplength=300, anchor="w")
        self.selected_file_label.pack(side=tk.LEFT, padx=10)

        # Button to convert PDF to JPEG images
        self.convert_btn = tk.Button(self.root, text="Convert to JPEG", command=self.convert)
        self.convert_btn.pack(pady=10, padx=20, fill=tk.X)

        # Button to save the JPEG images
        self.save_btn = tk.Button(self.root, text="Save Images", command=self.save)
        self.save_btn.pack(pady=10, padx=20, fill=tk.X)

        # Progress bar for the save process
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(pady=10, fill=tk.X, padx=20)

        # Live count label
        self.status_label = tk.Label(self.root, text="Status: Idle")
        self.status_label.pack(pady=5)

        # Button to exit the application
        self.exit_btn = tk.Button(self.root, text="Exit", command=self.root.quit)
        self.exit_btn.pack(pady=10, padx=20, fill=tk.X)

    def select_file(self):
        # Open file dialog to select a PDF file
        self.pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if self.pdf_path:
            # Extract the file name from the path
            file_name = os.path.basename(self.pdf_path)
            # Update the label with the selected file name
            self.selected_file_label.config(text=f"Selected File: {file_name}")
            # Optionally, remove the messagebox to reduce pop-ups
            # messagebox.showinfo("Selected File", f"Selected: {self.pdf_path}")

    def convert(self):
        # Convert the selected PDF file to JPEG images
        if not self.pdf_path:
            messagebox.showwarning("Input Required", "Please select a PDF file to convert.")
            return

        self.images = convert_pdf_to_images(self.pdf_path, dpi=150)

    def save(self):
        # Save the converted images to a selected folder
        if not self.images:
            messagebox.showwarning("No Images", "Please convert the PDF before saving.")
            return

        save_folder = filedialog.askdirectory()
        if save_folder:
            # Disable the save button to prevent multiple clicks
            self.save_btn.config(state=tk.DISABLED)

            # Create and start a new thread for saving images
            save_thread = threading.Thread(target=save_images, args=(
                self.images, save_folder, self.progress_var, self.progress_bar, self.status_label
            ))
            save_thread.start()

            # Re-enable the save button once saving is done
            self.root.after(100, self.check_thread, save_thread)

    def check_thread(self, thread):
        if thread.is_alive():
            self.root.after(100, self.check_thread, thread)
        else:
            self.save_btn.config(state=tk.NORMAL)

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = PDFtoJPEGConverterApp(root)
    root.mainloop()
