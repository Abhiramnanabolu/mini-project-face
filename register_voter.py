import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import psycopg2
from PIL import Image, ImageTk
import io

class VoterRegistrationApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Voter Registration")
        self.geometry("800x600")
        self.configure(bg="#f0f0f0")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TButton", 
                             background="#4CAF50", 
                             foreground="white", 
                             font=("Helvetica", 12, "bold"),
                             padding=10)
        self.style.map("TButton", background=[("active", "#45a049")])
        self.style.configure("TLabel", 
                             background="#f0f0f0", 
                             font=("Helvetica", 14))
        self.style.configure("TEntry", 
                             font=("Helvetica", 12))

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="30 30 30 30")
        main_frame.pack(expand=True, fill=tk.BOTH)

        title_label = ttk.Label(main_frame, 
                                text="Voter Registration", 
                                font=("Helvetica", 24, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        name_label = ttk.Label(main_frame, text="Full Name:")
        name_label.grid(row=1, column=0, sticky="w", pady=(0, 10))

        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.grid(row=1, column=1, sticky="ew", pady=(0, 10))

        photo_button = ttk.Button(main_frame, 
                                  text="Capture Photo", 
                                  command=self.capture_photo)
        photo_button.grid(row=2, column=0, columnspan=2, pady=(20, 20))

        self.photo_label = ttk.Label(main_frame)
        self.photo_label.grid(row=3, column=0, columnspan=2)

        register_button = ttk.Button(main_frame, 
                                     text="Register Voter", 
                                     command=self.register_voter)
        register_button.grid(row=4, column=0, columnspan=2, pady=(20, 0))

        main_frame.columnconfigure(1, weight=1)

    def capture_photo(self):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()

        if ret:
            self.photo = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.photo = Image.fromarray(self.photo)
            self.photo = self.photo.resize((300, 225))
            self.photo_tk = ImageTk.PhotoImage(self.photo)
            self.photo_label.config(image=self.photo_tk)
            self.photo_label.image = self.photo_tk
        else:
            messagebox.showerror("Error", "Failed to capture photo")

    def register_voter(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter your name")
            return

        if not hasattr(self, 'photo'):
            messagebox.showerror("Error", "Please capture a photo")
            return

        try:
            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            img_byte_arr = io.BytesIO()
            self.photo.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            cur.execute(
                "INSERT INTO voters (name, image) VALUES (%s, %s)",
                (name, psycopg2.Binary(img_byte_arr))
            )

            conn.commit()
            cur.close()
            conn.close()

            messagebox.showinfo("Success", "Voter registered successfully!")
            self.name_entry.delete(0, tk.END)
            self.photo_label.config(image='')
            del self.photo

        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Failed to register voter: {e}")

if __name__ == "__main__":
    app = VoterRegistrationApp()
    app.mainloop()