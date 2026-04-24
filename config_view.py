import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports
import os
import json
import styles
from create_recipe import RecipeCreatorApp

"""
This class is a toplevel popup that lets the user select from serial ports
"""
class Configure(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Select Port")
        self.geometry("750x450")

        styles.apply_theme(self)

        # prevent user from interacting with parent window
        self.transient(parent)
        self.grab_set()

        self.result_port = None
        self.result_rate = 5
        self.result_recipe = None
        self.port_objects = []

        self.setup_scrollable_area()

        self.create_widgets() 
        self.refresh_ports()
        self.refresh_recipes()

        # handle x to close whole app
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_scrollable_area(self):
        # main container
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        # canvas
        self.canvas = tk.Canvas(container, bg=styles.COLOR_BG, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # scrollbar
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(yscrollcommand=scrollbar.set)

        # scrollable frame (holds all widgets)
        self.scrollable_frame = ttk.Frame(self.canvas, padding=20)
        
        # window inside canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # bindings for resizing and scrolling
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        
        self.enable_scrolling()
        self.bind("<Destroy>", self._cleanup_scroll)

    def enable_scrolling(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)


    def _cleanup_scroll(self, event):
        # When the window closes, stop listening to the mouse wheel
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        try:
            # CRITICAL: This single line prevents the "invalid command name" crash.
            # If the canvas is dead, stop immediately.
            if not self.canvas.winfo_exists():
                return
            
            # Scroll logic
            if event.delta:
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
            elif event.num == 4:
                self.canvas.yview_scroll(-1, "units")
        except tk.TclError:
            pass

    def create_widgets(self):
        # # Main Container
        # main_frame = ttk.Frame(self, padding=20)
        # main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Header ---
        ttk.Label(self.scrollable_frame, text="Connection Setup", style="Header.TLabel").pack(pady=(0, 20))

        # --- Port Selection Section ---
        port_frame = ttk.LabelFrame(self.scrollable_frame, text="1. Select Arduino Port", padding=15)
        port_frame.pack(fill=tk.X, pady=10)

        # Row 1: Combobox and Refresh Button side-by-side
        row1 = ttk.Frame(port_frame)
        row1.pack(fill=tk.X)

        self.port_var = tk.StringVar()
        self.combo = ttk.Combobox(row1, textvariable=self.port_var, state="readonly", font=styles.FONT_MAIN)
        self.combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # Refresh Button (Standard Style)
        ttk.Button(row1, text="↻ Refresh", command=self.refresh_ports).pack(side=tk.RIGHT)

        # --- Sample Rate Section ---
        rate_frame = ttk.LabelFrame(self.scrollable_frame, text="2. Sample Rate (Seconds)", padding=15)
        rate_frame.pack(fill=tk.X, pady=10)

        self.rate_var = tk.IntVar(value=5)
        # We manually set font to match styles.
        self.rate_spin = tk.Spinbox(rate_frame, from_=1, to=3600, 
                                    textvariable=self.rate_var, 
                                    font=("Helvetica", 14), # Slightly larger for touch
                                    justify='center',
                                    bd=1, relief="flat") 
        self.rate_spin.pack(fill=tk.X, ipady=5) # ipady makes it taller for fingers

        # --- Select Recipes ---
        recipe_frame = ttk.LabelFrame(self.scrollable_frame, text="3. Recipe Selection (Optional)", padding=15)
        recipe_frame.pack(fill=tk.X, pady=10)

        row_recipe = ttk.Frame(recipe_frame)
        row_recipe.pack(fill=tk.X)

        self.recipe_var = tk.StringVar()
        self.combo_recipes = ttk.Combobox(row_recipe, textvariable=self.recipe_var, state="readonly", font=styles.FONT_MAIN)
        self.combo_recipes.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Button(row_recipe, text="↻", width=3, command=self.refresh_recipes).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row_recipe, text="New Recipe", command=self.open_recipe_creator).pack(side=tk.RIGHT)

        # --- Action Buttons ---
        btn_frame = ttk.Frame(self.scrollable_frame, padding=(0, 20, 0, 0))
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Start Button (Green/Accent)
        start_btn = ttk.Button(btn_frame, text="Connect & Start", command=self.on_start)
        start_btn.pack(fill=tk.X, ipady=10)


    def refresh_ports(self):
        self.port_object = serial.tools.list_ports.comports()
        display_list = [f"{p.device} - {p.description}" for p in self.port_object]
        self.combo['values'] = display_list

        if display_list:
            self.combo.current(0)
        else:
            self.combo.set("No ports detected.")

    def refresh_recipes(self):
        try:
            if not self.winfo_exists(): return
        except tk.TclError:
            return
        
        if not os.path.exists(styles.RECIPE_DIR):
            os.makedirs(styles.RECIPE_DIR)
        
        files = [f for f in os.listdir(styles.RECIPE_DIR) if f.endswith(".json")]
        
        try:
            if not files:
                display_list = ["No recipes found"]
                self.combo_recipes['values'] = display_list
                self.combo_recipes.set("No recipes found")
            else:
                display_list = ["Select Recipe"] + files
                self.combo_recipes['values'] = display_list
                self.combo_recipes.current(0)
        except tk.TclError:
            pass

    def open_recipe_creator(self):
        creator_window = tk.Toplevel(self)
        app = RecipeCreatorApp(creator_window)
        
        # wait for the creator to close, then refresh the list
        self.wait_window(creator_window)
        
        try:
            if self.winfo_exists():
                self.refresh_recipes()
                self.enable_scrolling()
        except tk.TclError:
            pass
    
    def on_start(self):
        selection = self.port_var.get()

        # check port selection
        if not selection or "No ports detected" in selection:
            messagebox.showwarning("Warning", "Please plug in your Arduino and click Refresh.")
            return # stop here so the window stays open

        # check sample rate
        try:
            rate = int(self.rate_var.get())
            if rate <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Setup Error", "Sample rate must be a positive number.")
            return # stop here so the window stays open
        
        # Extract just the device path (e.g., "COM3" or "/dev/ttyACM0") from the string
        # Assuming format "DEVICE - DESCRIPTION"
        actual_port = selection.split(" - ")[0]

        # get recipe stuff
        recipe_selection = self.recipe_var.get()
        if recipe_selection and "None" not in recipe_selection and "No recipes" not in recipe_selection:
            self.result_recipe = recipe_selection # Save filename (e.g., "E_Coli.json")
        else:
            self.result_recipe = None

        self.result_port = actual_port
        self.result_rate = rate

        self.destroy()

    def on_close(self):
        self.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    styles.apply_theme(root) # Apply theme to root for testing
    root.withdraw() # Hide root
    
    app = Configure(root)
    root.wait_window(app)
    
    if app.result_port:
        print(f"Selected: {app.result_port} @ {app.result_rate}s")
        root.destroy()