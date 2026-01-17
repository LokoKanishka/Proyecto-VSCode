import customtkinter as ctk
from .code_block import CodeBlock

class MessageBubble(ctk.CTkFrame):
    def __init__(self, master, text, is_user=False, **kwargs):
        super().__init__(master, corner_radius=15, **kwargs)
        
        self.is_user = is_user
        
        # Style configuration
        if is_user:
            self.configure(fg_color="#5e5cd6") # Accent color
            text_color = "#ffffff"
            anchor = "e"
        else:
            self.configure(fg_color="#333333") # Darker gray
            text_color = "#dce4ee"
            anchor = "w"

        self.grid_columnconfigure(0, weight=1)
        self.widgets = [] # Keep track of internal widgets
        
        # Initial render
        self.render_content(text, text_color)

    def render_content(self, text, text_color):
        """Parses text for ```code blocks``` and renders widgets."""
        # Clear previous widgets
        for widget in self.widgets:
            widget.destroy()
        self.widgets = []

        parts = text.split("```")
        
        row_idx = 0
        for i, part in enumerate(parts):
            if not part: continue
            
            # Even indices = Normal Text (0, 2, 4...)
            # Odd indices = Code Block (1, 3, 5...)
            is_code = (i % 2 == 1)
            
            if is_code:
                # Code Block
                # Strip language ident if present (e.g. "python\nprint()")
                content = part
                if '\n' in content:
                    first_line, rest = content.split('\n', 1)
                    if first_line.strip().replace("_","").isalnum(): # Simple check for lang name
                        content = rest
                elif content.strip().replace("_","").isalnum(): # Just a lang name? ignore
                     content = part 
                
                # Trim valid code content
                content = content.strip("\n")
                
                block = CodeBlock(self, content)
                block.grid(row=row_idx, column=0, padx=10, pady=5, sticky="ew")
                self.widgets.append(block)
                
            else:
                # Normal Text
                # Avoid empty text parts
                if not part.strip(): continue
                
                label = ctk.CTkLabel(
                    self, 
                    text=part, 
                    text_color=text_color, 
                    wraplength=400, 
                    justify="left",
                    font=("Roboto", 14)
                )
                label.grid(row=row_idx, column=0, padx=15, pady=5, sticky="w")
                self.widgets.append(label)
                
            row_idx += 1

    def update_text(self, new_text):
        """Updates content dynamically."""
        # For full Markdown parsing, we need to re-render.
        # This might be heavy for per-character updates.
        # Optimization: Only re-render if connection status changes or periodically?
        # For now, re-render is safe for small contexts.
        
        # Determine text color again (stored or re-derived)
        text_color = "#ffffff" if self.is_user else "#dce4ee"
        self.render_content(new_text, text_color)

