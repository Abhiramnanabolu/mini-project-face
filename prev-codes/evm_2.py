import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
import cv2
import numpy as np
from PIL import Image, ImageTk
import io
import serial
from deepface import DeepFace

class EVMApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Electronic Voting Machine")
        self.geometry("1200x600")
        self.configure(bg="#f0f0f0")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TButton", background="#4CAF50", foreground="white", font=("Helvetica", 12, "bold"), padding=10)
        self.style.map("TButton", background=[("active", "#45a049")])
        self.style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 12))
        self.style.configure("Treeview", font=("Helvetica", 11))
        self.style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

        self.create_widgets()
        self.load_voters()

        try:
            self.arduino = serial.Serial('COM4', 9600, timeout=1)
        except:
            messagebox.showerror("Error", "Could not connect to Arduino")

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20 20 20 20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        title_label = ttk.Label(left_frame, text="Electronic Voting Machine", font=("Helvetica", 24, "bold"))
        title_label.pack(pady=(0, 20))

        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        search_label = ttk.Label(search_frame, text="Search:")
        search_label.pack(side=tk.LEFT, padx=(0, 10))

        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.search_voters)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Create Treeview
        self.tree = ttk.Treeview(left_frame, columns=("ID", "Name"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.column("ID", width=50, anchor=tk.CENTER)
        self.tree.column("Name", width=200, anchor=tk.W)
        self.tree.pack(expand=True, fill=tk.BOTH)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Bind select event
        self.tree.bind("<<TreeviewSelect>>", self.on_voter_select)

        # Right frame widgets
        self.image_label = ttk.Label(right_frame)
        self.image_label.pack(pady=20)

        self.verify_button = ttk.Button(right_frame, text="Verify Face", command=self.verify_face)
        self.verify_button.pack(pady=10)
        self.verify_button.state(['disabled'])

    def load_voters(self):
        try:
            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            cur.execute("SELECT id, name FROM voters ORDER BY id")
            voters = cur.fetchall()

            for voter in voters:
                self.tree.insert("", tk.END, values=voter)

            cur.close()
            conn.close()

        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Error loading voters: {e}")

    def search_voters(self, *args):
        search_term = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())

        try:
            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            cur.execute("SELECT id, name FROM voters WHERE LOWER(name) LIKE %s ORDER BY id", (f'%{search_term}%',))
            voters = cur.fetchall()

            for voter in voters:
                self.tree.insert("", tk.END, values=voter)

            cur.close()
            conn.close()

        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Error searching voters: {e}")

    def on_voter_select(self, event):
        selected_item = self.tree.selection()[0]
        voter_id, voter_name = self.tree.item(selected_item)['values']

        try:
            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            cur.execute("SELECT image FROM voters WHERE id = %s", (voter_id,))
            image_data = cur.fetchone()[0]

            cur.close()
            conn.close()

            # Convert binary data to image
            image = Image.open(io.BytesIO(image_data))
            image = image.resize((300, 300))  # Resize for display
            photo = ImageTk.PhotoImage(image)

            self.image_label.config(image=photo)
            self.image_label.image = photo  # Keep a reference

            self.verify_button.state(['!disabled'])
            self.current_voter_id = voter_id
            self.current_voter_name = voter_name

        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Error loading voter image: {e}")

    def verify_face(self):
        try:
            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            cur.execute("SELECT image FROM voters WHERE id = %s", (self.current_voter_id,))
            db_image_data = cur.fetchone()[0]

            cur.close()
            conn.close()

            # Convert binary data to image
            db_image = Image.open(io.BytesIO(db_image_data))
            db_image_array = np.array(db_image)

            # Capture image from camera
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()

            if not ret:
                messagebox.showerror("Error", "Failed to capture image from camera")
                return

            # Verify face
            try:
                result = DeepFace.verify(db_image_array, frame, enforce_detection=False)
                if result["verified"]:
                    messagebox.showinfo("Success", "Face verified successfully")
                    self.prompt_to_vote()
                else:
                    messagebox.showerror("Error", "Face verification failed")
            except Exception as e:
                messagebox.showerror("Error", f"Face verification error: {e}")

        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Database error: {e}")

    def prompt_to_vote(self):
        vote_window = tk.Toplevel(self)
        vote_window.title("Cast Your Vote")
        vote_window.geometry("400x200")

        label = ttk.Label(vote_window, text=f"Hello, {self.current_voter_name}! Please cast your vote.")
        label.pack(pady=20)

        vote_button = ttk.Button(vote_window, text="Cast Vote", command=lambda: self.cast_vote(vote_window))
        vote_button.pack()

    def cast_vote(self, vote_window):
        try:
            # Read vote from Arduino
            self.arduino.write(b'GET_VOTE')
            vote = int(self.arduino.readline().decode('utf-8').strip())

            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            # Update party votes
            cur.execute("UPDATE party SET votes = votes + 1 WHERE id = %s", (vote,))

            # Update voter status
            cur.execute("UPDATE voters SET vote_status = TRUE WHERE id = %s", (self.current_voter_id,))

            conn.commit()
            cur.close()
            conn.close()

            messagebox.showinfo("Success", "Vote cast successfully")
            vote_window.destroy()
            self.verify_button.state(['disabled'])
            self.image_label.config(image='')

        except (psycopg2.Error, ValueError, serial.SerialException) as e:
            messagebox.showerror("Error", f"Failed to cast vote: {e}")

if __name__ == "__main__":
    app = EVMApp()
    app.mainloop()

