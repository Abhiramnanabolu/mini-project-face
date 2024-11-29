import tkinter as tk
from tkinter import ttk
import psycopg2
from PIL import Image, ImageTk
import io

class VoterDisplayApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Voter Display")
        self.geometry("800x600")
        self.configure(bg="#f0f0f0")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 12))
        self.style.configure("Treeview", font=("Helvetica", 11))
        self.style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

        self.create_widgets()
        self.load_voters()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20 20 20 20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        title_label = ttk.Label(main_frame, text="Registered Voters", font=("Helvetica", 24, "bold"))
        title_label.pack(pady=(0, 20))

        self.tree = ttk.Treeview(main_frame, columns=("ID", "Name"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.column("ID", width=50, anchor=tk.CENTER)
        self.tree.column("Name", width=200, anchor=tk.W)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<<TreeviewSelect>>", self.on_voter_select)

        # Image display
        self.image_label = ttk.Label(main_frame)
        self.image_label.pack(pady=20)

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
            print(f"Error loading voters: {e}")

    def on_voter_select(self, event):
        selected_item = self.tree.selection()[0]
        voter_id = self.tree.item(selected_item)['values'][0]

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
            image = image.resize((300, 225))  # Resize for display
            photo = ImageTk.PhotoImage(image)

            self.image_label.config(image=photo)
            self.image_label.image = photo  # Keep a reference

        except psycopg2.Error as e:
            print(f"Error loading voter image: {e}")

if __name__ == "__main__":
    app = VoterDisplayApp()
    app.mainloop()