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
        self.geometry("1200x800") 
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

        self.camera = cv2.VideoCapture(0)
        self.camera_active = False

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

        self.tree = ttk.Treeview(left_frame, columns=("ID", "Name", "Status"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Status", text="Status")
        self.tree.column("ID", width=50, anchor=tk.CENTER)
        self.tree.column("Name", width=200, anchor=tk.W)
        self.tree.column("Status", width=100, anchor=tk.CENTER)
        self.tree.pack(expand=True, fill=tk.BOTH)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<<TreeviewSelect>>", self.on_voter_select)

        self.db_image_label = ttk.Label(right_frame)
        self.db_image_label.pack(pady=20)

        self.camera_label = ttk.Label(right_frame)
        self.camera_label.pack(pady=20)

        self.verify_button = ttk.Button(right_frame, text="Verify Face", command=self.verify_face)
        self.verify_button.pack(pady=10)
        self.verify_button.state(['disabled'])

        self.end_voting_button = ttk.Button(right_frame, text="End Voting", command=self.show_results)
        self.end_voting_button.pack(pady=10)

    def load_voters(self):
        try:
            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            cur.execute("SELECT id, name, vote_status FROM voters ORDER BY id")
            voters = cur.fetchall()

            for voter in voters:
                status = "Voted" if voter[2] else "Not Voted"
                self.tree.insert("", tk.END, values=(voter[0], voter[1], status))

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

            cur.execute("SELECT id, name, vote_status FROM voters WHERE LOWER(name) LIKE %s ORDER BY id", (f'%{search_term}%',))
            voters = cur.fetchall()

            for voter in voters:
                status = "Voted" if voter[2] else "Not Voted"
                self.tree.insert("", tk.END, values=(voter[0], voter[1], status))

            cur.close()
            conn.close()

        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Error searching voters: {e}")

    def on_voter_select(self, event):
        selected_item = self.tree.selection()[0]
        voter_id, voter_name, vote_status = self.tree.item(selected_item)['values']

        try:
            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            cur.execute("SELECT image, vote_status FROM voters WHERE id = %s", (voter_id,))
            result = cur.fetchone()
            image_data, vote_status = result[0], result[1]

            cur.close()
            conn.close()

            image = Image.open(io.BytesIO(image_data))
            image = image.resize((300, 300))  
            photo = ImageTk.PhotoImage(image)

            self.db_image_label.config(image=photo)
            self.db_image_label.image = photo 

            if not vote_status:
                self.verify_button.state(['!disabled'])
                self.start_camera()
            else:
                self.verify_button.state(['disabled'])
                self.stop_camera()
                messagebox.showinfo("Already Voted", f"{voter_name} has already cast their vote.")

            self.current_voter_id = voter_id
            self.current_voter_name = voter_name

        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Error loading voter image: {e}")

    def start_camera(self):
        self.camera_active = True
        self.update_camera()

    def stop_camera(self):
        self.camera_active = False
        self.camera_label.config(image='')

    def update_camera(self):
        if self.camera_active:
            ret, frame = self.camera.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (300, 300))
                photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
                self.camera_label.config(image=photo)
                self.camera_label.image = photo
            self.after(10, self.update_camera)

    def verify_face(self):
        try:
            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            cur.execute("SELECT image, vote_status FROM voters WHERE id = %s", (self.current_voter_id,))
            result = cur.fetchone()
            db_image_data, vote_status = result[0], result[1]

            cur.close()
            conn.close()

            if vote_status:
                messagebox.showinfo("Already Voted", f"{self.current_voter_name} has already cast their vote.")
                return

            db_image = Image.open(io.BytesIO(db_image_data))
            db_image_array = np.array(db_image)

            ret, frame = self.camera.read()

            if not ret:
                messagebox.showerror("Error", "Failed to capture image from camera")
                return

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
            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            cur.execute("SELECT vote_status FROM voters WHERE id = %s", (self.current_voter_id,))
            vote_status = cur.fetchone()[0]

            if vote_status:
                messagebox.showinfo("Already Voted", f"{self.current_voter_name} has already cast their vote.")
                vote_window.destroy()
                return

            messagebox.showinfo("Cast Vote", "Please press a button or enter 1, 2, or 3 on the Arduino to cast your vote.")
            
            vote = None
            while vote not in [1, 2, 3]:
                if self.arduino.in_waiting > 0:
                    vote_str = self.arduino.readline().decode('utf-8').strip()
                    if vote_str in ['1', '2', '3']:
                        vote = int(vote_str)
                
                if vote not in [1, 2, 3]:
                    self.update() 
                    self.after(100)  

            cur.execute("UPDATE party SET votes = votes + 1 WHERE id = %s", (vote,))

            cur.execute("UPDATE voters SET vote_status = TRUE WHERE id = %s", (self.current_voter_id,))

            conn.commit()
            cur.close()
            conn.close()

            messagebox.showinfo("Success", "Vote cast successfully")
            vote_window.destroy()
            self.verify_button.state(['disabled'])
            self.db_image_label.config(image='')
            self.stop_camera()

            for item in self.tree.get_children():
                if self.tree.item(item)["values"][0] == self.current_voter_id:
                    self.tree.item(item, values=(self.current_voter_id, self.current_voter_name, "Voted"))
                    break

        except (psycopg2.Error, ValueError, serial.SerialException) as e:
            messagebox.showerror("Error", f"Failed to cast vote: {e}")

    def show_results(self):
        try:
            conn = psycopg2.connect(
                dbname="evm_face",
                user="postgres",
                password="12345678",
                host="localhost"
            )
            cur = conn.cursor()

            cur.execute("SELECT party_name, votes FROM party ORDER BY votes DESC")
            results = cur.fetchall()
            
            if not results:
                messagebox.showinfo("Results", "No votes have been cast yet.")
                return

            cur.close()
            conn.close()

            results_window = tk.Toplevel(self)
            results_window.title("Voting Results")
            results_window.geometry("400x400") 
            results_window.transient(self)  
            results_window.grab_set() 

            canvas = tk.Canvas(results_window)
            scrollbar = ttk.Scrollbar(results_window, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            title_label = ttk.Label(
                scrollable_frame, 
                text="Voting Results", 
                font=("Helvetica", 18, "bold")
            )
            title_label.pack(pady=20)

            total_votes = sum(votes for _, votes in results)
            total_label = ttk.Label(
                scrollable_frame,
                text=f"Total Votes Cast: {total_votes}",
                font=("Helvetica", 12)
            )
            total_label.pack(pady=10)

            for party_name, votes in results:
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                result_label = ttk.Label(
                    scrollable_frame,
                    text=f"{party_name}: {votes} votes ({percentage:.1f}%)",
                    font=("Helvetica", 12)
                )
                result_label.pack(pady=5)

            winner = results[0]
            winner_frame = ttk.Frame(scrollable_frame)
            winner_frame.pack(pady=20)
            
            winner_label = ttk.Label(
                winner_frame,
                text=f"Winner: {winner[0]}\nVotes: {winner[1]}",
                font=("Helvetica", 14, "bold")
            )
            winner_label.pack()

            canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            scrollbar.pack(side="right", fill="y")

        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Failed to retrieve voting results: {e}")

    def __del__(self):
        if hasattr(self, 'camera'):
            self.camera.release()

if __name__ == "__main__":
    app = EVMApp()
    app.mainloop()