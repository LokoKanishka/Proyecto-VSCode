import customtkinter as ctk
from src.utils.settings_manager import SettingsManager

class ConfigPanel(ctk.CTkFrame):
    def __init__(self, master, width=300, fg_color="#2b2b2b", **kwargs):
        super().__init__(master, width=width, corner_radius=0, fg_color=fg_color, **kwargs)
        
        self.settings_manager = SettingsManager
        self.current_settings = self.settings_manager.load_settings()
        
        self.grid_propagate(False)  # Enforce width
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self.label_header = ctk.CTkLabel(
            self, 
            text="Model Configuration", 
            font=("Roboto Medium", 16)
        )
        self.label_header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Model Selection
        self.label_model = ctk.CTkLabel(self, text="Select Model:", font=("Roboto", 12))
        self.label_model.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        
        # Try to discover models locally
        self.available_models = ["Llama 3", "Phi-3", "Mistral", "Gemma"] # Default Fallback
        
        # We need a temporary engine instance or direct bridge to list models
        # For simplicity, we import OllamaEngine here or check if available
        try:
            from src.engine.ollama_engine import OllamaEngine
            models = OllamaEngine().list_models()
            if models:
                self.available_models = models
        except Exception as e:
            print(f"Could not list models: {e}")
        
        self.option_model = ctk.CTkOptionMenu(
            self, 
            values=self.available_models,
            fg_color="#5e5cd6",  # Accent
            button_color="#4b49ac",
            button_hover_color="#3a388a",
            command=self.on_setting_change
        )
        self.option_model.set(self.current_settings["model"])
        self.option_model.grid(row=2, column=0, padx=20, pady=(5, 10), sticky="ew")
        
        # Temperature
        self.label_temp = ctk.CTkLabel(self, text=f"Temperature: {self.current_settings['temperature']}", font=("Roboto", 12))
        self.label_temp.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.slider_temp = ctk.CTkSlider(
            self, 
            from_=0, 
            to=1, 
            number_of_steps=20, 
            progress_color="#5e5cd6",
            command=self.update_temp_label
        )
        self.slider_temp.set(self.current_settings["temperature"])
        self.slider_temp.grid(row=4, column=0, padx=20, pady=(5, 10), sticky="ew")
        
        # Max Tokens
        self.label_tokens = ctk.CTkLabel(self, text=f"Max Tokens: {self.current_settings['max_tokens']}", font=("Roboto", 12))
        self.label_tokens.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.slider_tokens = ctk.CTkSlider(
            self, 
            from_=256, 
            to=8192, 
            number_of_steps=100, 
            progress_color="#5e5cd6",
            command=self.update_tokens_label
        )
        self.slider_tokens.set(self.current_settings["max_tokens"])
        self.slider_tokens.grid(row=6, column=0, padx=20, pady=(5, 10), sticky="ew")
        
        # System Prompt
        self.label_sys = ctk.CTkLabel(self, text="System Prompt:", font=("Roboto", 12))
        self.label_sys.grid(row=7, column=0, padx=20, pady=(20, 0), sticky="w")
        
        self.txt_sys_prompt = ctk.CTkTextbox(
            self, 
            height=150, 
            fg_color="#1c1c1c", 
            text_color="#dce4ee"
        )
        self.txt_sys_prompt.insert("1.0", self.current_settings["system_prompt"])
        self.txt_sys_prompt.grid(row=8, column=0, padx=20, pady=(5, 20), sticky="ew")
        
        # Save Trigger (Simulate auto-save on change)
        self.txt_sys_prompt.bind("<KeyRelease>", self.on_text_change)

    def update_temp_label(self, value):
        self.label_temp.configure(text=f"Temperature: {value:.2f}")
        self.current_settings["temperature"] = value
        self.save_config()

    def update_tokens_label(self, value):
        val = int(value)
        self.label_tokens.configure(text=f"Max Tokens: {val}")
        self.current_settings["max_tokens"] = val
        self.save_config()

    def on_setting_change(self, value):
        self.current_settings["model"] = value
        self.save_config()
        
    def on_text_change(self, event):
        self.current_settings["system_prompt"] = self.txt_sys_prompt.get("1.0", "end-1c")
        self.save_config()

    def save_config(self):
        self.settings_manager.save_settings(self.current_settings)
