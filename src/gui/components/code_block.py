import customtkinter as ctk

class CodeBlock(ctk.CTkFrame):
    def __init__(self, master, code_text, **kwargs):
        super().__init__(master, fg_color="#111111", corner_radius=5, **kwargs)
        
        self.code_text = code_text
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        
        # Header (Optional: could add lang label here)
        self.header_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", height=25, corner_radius=5)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        # Copy Button
        self.btn_copy = ctk.CTkButton(
            self.header_frame, 
            text="Copy", 
            width=50, 
            height=20,
            fg_color="transparent",
            font=("Roboto", 10),
            hover_color="#3a3a3a",
            command=self.copy_to_clipboard
        )
        self.btn_copy.grid(row=0, column=1, padx=5, pady=2, sticky="e")
        
        # Code Content
        # Using a Textbox for scrollable code, or Label for simple block. 
        # Textbox is better for long code. Disabling edit.
        self.code_display = ctk.CTkTextbox(
            self, 
            fg_color="#111111", 
            text_color="#dce4ee",
            font=("Consolas", 12),
            wrap="none", # Horizontal scroll for code
            height=100, # Initial height, dynamic resizing is tricky with Textbox
            corner_radius=0
        )
        self.code_display.insert("1.0", code_text)
        self.code_display.configure(state="disabled") # Read-only
        self.code_display.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Dynamic resizing: count lines to set height roughly
        num_lines = code_text.count('\n') + 1
        new_height = min(max(num_lines * 20, 40), 400) # Min 40, Max 400
        self.code_display.configure(height=new_height)
        
    def copy_to_clipboard(self):
        self.clipboard_clear()
        self.clipboard_append(self.code_text)
        self.update() # Required to finalize clipboard
        self.btn_copy.configure(text="Copied!")
        self.after(2000, lambda: self.btn_copy.configure(text="Copy"))
