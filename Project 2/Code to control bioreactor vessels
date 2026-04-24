import tkinter as tk
from tkinter import ttk, messagebox
import queue
import threading
import styles
import json
import os
from comms import Worker, MockWorker
from config_view import Configure 

TESTING = False

# unused right now, but will be used to differentiate between different vessels
class Vessel:
    def __init__(self, port):
        self.port=port
        self.temp = None
        self.cell_dens = None
        self.ph = None
        self.do = None
        self.agitotor_toggle_motor = False
        self.pump_on = False


"""
This class handles the GUI
"""
class VesselApp:
    def __init__(self, root, test_mode=False):
        self.root = root
        self.test_mode = test_mode
        root.geometry("750x450")
        self.recipe = None
        
        styles.apply_theme(self.root)
        self.root.title("Bioreactor Control")
        
        if not self.test_mode:
            # select the port and sample rate
            setup_data = self.ask_for_setup()
            if not setup_data:
                try:
                    # Only try to destroy if it still exists
                    if self.root.winfo_exists():
                        self.root.destroy()
                except tk.TclError:
                    pass # It's already gone, ignore the error
                return
            
            self.port = setup_data["port"]
            self.rate = setup_data["rate"]
            self.recipe = self.load_recipe(setup_data.get("recipe"))
        else:
            self.port = "SIMULATED_PORT"
            self.rate = 9600
            self.recipe = self.load_recipe("Example_E_coli_Run_01.json") # load ecoli recipe for testing

        # vars
        self.temp_var = tk.StringVar(value="--")
        self.motor_var = tk.StringVar(value="Motor: UNKNOWN")
        self.is_motor_on = False
        self.celldensity_var = tk.StringVar(value="--")
        self.dissolvedoxy_var = tk.StringVar(value="--")
        self.potentialhydrogen_var = tk.StringVar(value="--")
        self.heater_var = tk.StringVar(value="Heater: UNKNOWN")
        self.is_heater_on = False
        

        # TODO: ADD NEW SENSOR/CONTROLLER VARIABLES HERE

        # --- GUI VARIABLES AND QUEUES ---
        self.out_q = queue.Queue() # queue data from worker -> GUI
        self.cmd_q = queue.Queue() # queue for commands from GUI -> worker
        self.stop_event = threading.Event() # signal shut down to worker

        self.create_widgets()

        # start worker
        if self.test_mode:
            self.worker = MockWorker(self.out_q, self.cmd_q, self.stop_event)
        else:
            self.worker = Worker(self.out_q, self.cmd_q, self.stop_event, 
                                 self.port, 9600, self.rate)
        self.worker.start()

        # start worker polling loop
        self.root.after(100, self._poll_queue)

    def ask_for_setup(self):
        selector = Configure(self.root)
        self.root.wait_window(selector.top if hasattr(selector, 'top') else selector)

        # make sure no close without selection
        if hasattr(selector, 'result_port') and selector.result_port:
            return {
                "port": selector.result_port,
                "rate": selector.result_rate,
                "recipe": selector.result_recipe
            }
        return None
    
    def create_widgets(self):
        # --- Main Container ---
        main_frame = ttk.Frame(self.root, padding=styles.PAD_X)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Sensor Section ---
        sensor_frame = ttk.LabelFrame(main_frame, text="Sensor Readings", padding=styles.PAD_Y)
        sensor_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(sensor_frame, text="Temperature (°F):").grid(row=0, column=0, padx=5, sticky="w")
        ttk.Label(sensor_frame, textvariable=self.temp_var, style="Header.TLabel").grid(row=0, column=1, padx=20, sticky="w")

        ttk.Label(sensor_frame, text="Cell Density (cells/mL):").grid(row=1, column=0, padx=5, sticky="w")
        ttk.Label(sensor_frame, textvariable=self.celldensity_var, style="Header.TLabel").grid(row=1,column=1, padx=20, sticky="w")
        
        ttk.Label(sensor_frame, text="DO (mg/L):").grid(row=2, column=0, padx=5, sticky="w")
        ttk.Label(sensor_frame, textvariable=self.dissolvedoxy_var, style="Header.TLabel").grid(row=2,column=1, padx=20, sticky="w")

        ttk.Label(sensor_frame, text="Ph:").grid(row=3, column=0, padx=5, sticky="w")
        ttk.Label(sensor_frame, textvariable=self.potentialhydrogen_var, style="Header.TLabel").grid(row=3,column=1, padx=20, sticky="w")



        # TODO: ADD NEW SENSOR LABELS

        # --- Control Section ---
        control_frame = ttk.LabelFrame(main_frame, text="Manual Controls", padding=styles.PAD_Y)
        control_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(control_frame, textvariable=self.motor_var).pack(pady=5)

        self.btn_motor = ttk.Button(control_frame, text="Turn Motor ON", command=self.toggle_motor)
        self.btn_motor.pack(pady=10, ipady=10) # ipady makes button taller for touch


        ttk.Label(control_frame, textvariable=self.heater_var).pack(pady=5)

        self.btn_heater = ttk.Button(control_frame, text="Turn Heater ON", command=self.toggle_heater)
        self.btn_heater.pack(pady=10, ipady=10)
        # TODO: ADD NEW CONTROL BUTTONS
    
    # loads JSON recipe to a dictionary file as selected in the confi file
    def load_recipe(self, filename):
        if not filename:
            print("[App] No recipe selected. Running in manual mode.")
            return None
            
        filepath = os.path.join(styles.RECIPE_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                recipe_data = json.load(f)
                print(f"[App] Successfully loaded recipe: {filename}")
                print(recipe_data)
                return recipe_data
        except Exception as e:
            messagebox.showerror("Recipe Error", f"Failed to load {filename}:\n{e}")
            return None
        
    def evaluate_thresholds(self, current_data):
        # compare current readings against targets from recipe
        if not self.recipe:
            print("There is no recipe loaded")
            return # no recipe, do nothing - manual mode?
        
        # get dictionaries from recipe json
        setpoints = self.recipe.get("setpoints", {})

        # temperature threshold
        temp_settings = setpoints.get("temperature", {})
        if "tempF" in current_data and "target" in temp_settings: # make sure we have temp set up in the data and the recipe
            current_temp = float(current_data["tempF"])
            target_temp = float(temp_settings["target"])
            # pull the tolerance directly from the nested temperature settings in the recipe JSON
            tolerance = float(temp_settings.get("tolerance", 0.5))

            if current_temp < (target_temp - tolerance) and not self.is_heater_on:
                self.cmd_q.put({"target": "heater", "action": "on"})
            elif current_temp > (target_temp) and self.is_heater_on: # don't include the tolerance bc it will likely keep heating once the heating pad is off
                self.cmd_q.put({"target": "heater", "action": "off"})

        # PH threshold
        ph_settings = setpoints.get("ph", {})
        if "ph" in current_data and "target" in ph_settings:
            current_ph = float(current_data["ph"])
            target_ph = float(ph_settings["target"])
            tolerance = float(ph_settings.get("tolerance", 0.1))
            
            if current_ph < (target_ph - tolerance):
                print(f"[Threshold] pH low ({current_ph}). TODO: Trigger Fluidics Base Pump.")
                # self.cmd_q.put({"target": "pump_base", "action": "on"})
            elif current_ph > (target_ph + tolerance): # TODO: do i include tolerance, or is change in PH instant?
                print(f"[Threshold] pH high ({current_ph}). TODO: Trigger Fluidics Acid Pump.")

        # DO Threshold
        do_settings = setpoints.get("do", {})
        if "do" in current_data and "target" in do_settings:
            current_do = float(current_data["do"])
            target_do = float(do_settings["target"])
            tolerance = float(do_settings.get("tolerance", 5.0))
            
            if current_do < (target_do - tolerance) and not self.is_motor_on:
                print(f"[Threshold] DO low ({current_do}). Turning on agitator motor.")
                self.cmd_q.put({"target": "motor", "action": "on"})
            # turn motor off
            elif current_do >= target_do and self.is_motor_on:
                print(f"[Threshold] DO target reached ({current_do}). Turning off agitator motor.")
                self.cmd_q.put({"target": "motor", "action": "off"})

    # updates GUI from worker data
    def _poll_queue(self):
        while not self.out_q.empty(): # while there's stuff in the out_q
            try:
                msg = self.out_q.get_nowait()

                if msg["type"] == "sensors":
                    data = msg["data"]
                    if "tempF" in data:
                        self.temp_var.set(f"{data['tempF']} °F")

                    if "do" in data:
                        self.dissolvedoxy_var.set(f"{float(data['do']):.2f} mg/L")
                    
                    if "cd" in data:
                        self.celldensity_var.set(f"{float(data['cd']):.2f} OD600")

                    if "ph" in data:
                        self.potentialhydrogen_var.set(f"{float(data['ph']):.2f}")

                    self.evaluate_thresholds(data)

                elif msg["type"] == "states":
                    data = msg["data"]
                    # match keys: "motor" -> "True" or "False"
                    if "motor" in data:
                        self.update_motor_state(data["motor"])

                    if "heater" in data:
                        self.update_heater_state(data["heater"])
                    # TODO: NEW IF BLOCK TO CHECK FOR CONTROLLER STATES
                
                elif msg["type"] == "error":
                    messagebox.showerror("System Error", msg["msg"])

            except queue.Empty:
                pass
        
        # schedule next poll
        self.root.after(100, self._poll_queue)

    def update_motor_state(self, state_str):
        # Convert "True"/"False" string to bool
        is_on = (str(state_str).lower() == "true")
        self.is_motor_on = is_on
        
        self.motor_var.set(f"Motor: {'ON' if is_on else 'OFF'}")
        
        if is_on:
            self.btn_motor.config(text="Turn Motor OFF", style="Danger.TButton") # Red button to stop
        else:
            self.btn_motor.config(text="Turn Motor ON", style="TButton") # Green button to start
            
            
    def toggle_motor(self):
        # send a request to the worker
        self.cmd_q.put({"target": "motor", "action": "toggle"})
    
    def update_heater_state(self, state_str):
        is_on = (str(state_str).lower() == "true")
        self.is_heater_on = is_on
        
        self.heater_var.set(f"Heater: {'ON' if is_on else 'OFF'}")
        
        if is_on:
            self.btn_heater.config(text="Turn Heater OFF", style="Danger.TButton") # Red button to stop
        else:
            self.btn_heater.config(text="Turn Heater ON", style="TButton") # Green button to start

    def toggle_heater(self):
        self.cmd_q.put({"target": "heater", "action": "toggle"})
    # TODO: MORE TOGGLE FUNCTIONS GO HERE

    # TODO: MORE HELPER FUNCTIONS TO TOGGLE BUTTON ON UI (LIKE update_motor_state)

    # shut down worker thread when app stops
    def shutdown(self):
        self.stop_event.set()
        if hasattr(self, 'worker'):
            self.worker.join(timeout=1.0)

if __name__ == "__main__":
    root = tk.Tk()
    if TESTING:
        app = VesselApp(root, test_mode=True)
    else:
        app = VesselApp(root)
    
    def on_closing():
        app.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
