import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sympy import symbols, sympify, diff, lambdify
from scipy.integrate import quad
import platform
import json
from mpl_toolkits.mplot3d import Axes3D

SESSION_FILE = "calc_session.json"

class CalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Scientific Graphing Calculator")
        self.is_scientific = False
        self.is_fullscreen = False
        self.dark_mode = False
        self.variables = {}
        self.history = []
        self.current_user = None
        self.x_range = (-10, 10)
        self.y_range = (-10, 10)
        self.font_size = 18
        self.last_plot_type = None  # Track last plot type (2d or 3d)

        if platform.system() == "Windows":
            self.root.state("zoomed")
        else:
            self.root.attributes("-zoomed", True)

        self.create_widgets()
        self.bind_keys()
        self.load_session()

    def create_widgets(self):
        self.style = ttk.Style(self.root)
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        self.entry = ttk.Entry(self.main_frame, font=("Arial", self.font_size), justify="right")
        self.entry.grid(row=0, column=0, columnspan=7, sticky="nsew", padx=10, pady=10)

        button_layout = [
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('/', 1, 3), ('C', 1, 4), ('SavePNG', 1, 5), ('SavePDF', 1, 6),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('*', 2, 3), ('(', 2, 4), ('Int', 2, 5), ('Deriv', 2, 6),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('-', 3, 3), (')', 3, 4), ('Sci', 3, 5), ('Graph2D', 3, 6),
            ('0', 4, 0), ('.', 4, 1), ('=', 4, 2), ('+', 4, 3), ('FontSize', 4, 4), ('Theme', 4, 5), ('Graph3D', 4, 6),
            ('History', 5, 0), ('ClearHist', 5, 1), ('Zoom+', 5, 2), ('Zoom-', 5, 3), ('SignIn', 5, 4), ('SignOut', 5, 5),
            ('FullScreen', 5, 6), ('ExitFS', 5, 7),
        ]
        self.buttons = {}
        for (text, r, c) in button_layout:
            btn = ttk.Button(self.main_frame, text=text, command=lambda t=text: self.on_button_click(t))
            btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
            self.buttons[text] = btn

        self.history_box = tk.Listbox(self.main_frame, height=6, font=("Arial", 12))
        self.history_box.grid(row=8, column=0, columnspan=8, sticky="nsew", padx=10, pady=5)

        for i in range(9):
            self.main_frame.rowconfigure(i, weight=1)
        for i in range(9):
            self.main_frame.columnconfigure(i, weight=1)

        self.fig = plt.figure(figsize=(6, 5))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().grid(row=0, column=8, rowspan=9, sticky='nsew', padx=10, pady=10)
        self.main_frame.columnconfigure(8, weight=3)

    def bind_keys(self):
        self.root.bind("<Return>", lambda e: self.evaluate_expression())
        self.root.bind("<Escape>", lambda e: self.root.quit())
        self.root.bind("<Control-f>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Control-s>", lambda e: self.save_session())
        self.root.bind("<Control-h>", lambda e: self.show_history())
        self.root.bind("<Control-c>", lambda e: self.clear_history())

    def on_button_click(self, char):
        special = {
            'C': self.clear_input,
            '=': self.evaluate_expression,
            'Sci': self.toggle_scientific,
            'Graph2D': self.plot_2d,
            'Graph3D': self.plot_3d,
            'Zoom+': self.zoom_in,
            'Zoom-': self.zoom_out,
            'Theme': self.prompt_set_theme,
            'FontSize': self.set_font_size,
            'History': self.show_history,
            'ClearHist': self.clear_history,
            'SavePNG': self.save_graph_png,
            'SavePDF': self.save_graph_pdf,
            'Int': self.integrate_expression,
            'Deriv': self.derive_expression,
            'FullScreen': self.toggle_fullscreen,
            'ExitFS': self.exit_fullscreen,
            'SignIn': self.sign_in,
            'SignOut': self.sign_out
        }
        if char in special:
            special[char]()
        elif char in "0123456789.+-*/()":
            self.entry.insert(tk.END, char)
        elif char in ['sin', 'cos', 'tan', 'log']:
            self.entry.insert(tk.END, f'{char}(')
        else:
            messagebox.showerror("Error", f"Unknown button: {char}")

    def clear_input(self):
        self.entry.delete(0, tk.END)

    def evaluate_expression(self):
        expr = self.entry.get().replace("^", "**")
        try:
            result = eval(expr, {"__builtins__": None}, self.variables)
            self.entry.delete(0, tk.END)
            self.entry.insert(tk.END, str(result))
            self.history.append(f"{expr} = {result}")
            if len(self.history) > 50:
                self.history.pop(0)
            self.update_history_box()
            self.save_session()
        except Exception as e:
            messagebox.showerror("Evaluation Error", f"Invalid expression:\n{e}")

    def update_history_box(self):
        self.history_box.delete(0, tk.END)
        for item in self.history:
            self.history_box.insert(tk.END, item)

    def toggle_scientific(self):
        self.is_scientific = not self.is_scientific
        self.update_scientific_buttons()

    def update_scientific_buttons(self):
        sci_funcs = ['sin', 'cos', 'tan', 'log']
        if self.is_scientific:
            for i, func in enumerate(sci_funcs):
                btn = ttk.Button(self.main_frame, text=func, command=lambda f=func: self.entry.insert(tk.END, f + '('))
                btn.grid(row=6, column=i, sticky="nsew", padx=2, pady=2)
                self.buttons[func] = btn
        else:
            for func in sci_funcs:
                if func in self.buttons:
                    self.buttons[func].destroy()
                    del self.buttons[func]

    def plot_2d(self):
        expr = self.entry.get().replace("^", "**")
        try:
            x = symbols('x')
            func = lambdify(x, sympify(expr), modules=["numpy"])
            x_vals = np.linspace(self.x_range[0], self.x_range[1], 400)
            y_vals = func(x_vals)
            self.ax.clear()
            self.ax.plot(x_vals, y_vals, color='cyan' if self.dark_mode else 'blue')
            self.ax.set_xlabel("x", color='white' if self.dark_mode else 'black')
            self.ax.set_ylabel("y", color='white' if self.dark_mode else 'black')
            self.ax.tick_params(colors='white' if self.dark_mode else 'black')
            self.fig.patch.set_facecolor("#222" if self.dark_mode else "white")
            self.ax.set_facecolor("#333" if self.dark_mode else "white")
            self.canvas.draw()
            self.last_plot_type = '2d'
        except Exception as e:
            messagebox.showerror("2D Plot Error", f"Could not plot:\n{e}")

    def plot_3d(self):
        expr = self.entry.get().replace("^", "**")
        try:
            x, y = symbols("x y")
            func = lambdify((x, y), sympify(expr), modules=["numpy"])
            x_vals = np.linspace(self.x_range[0], self.x_range[1], 100)
            y_vals = np.linspace(self.y_range[0], self.y_range[1], 100)
            X, Y = np.meshgrid(x_vals, y_vals)
            Z = func(X, Y)
            self.fig.clf()
            ax3d = self.fig.add_subplot(111, projection="3d")
            surf = ax3d.plot_surface(X, Y, Z, cmap="viridis")
            ax3d.set_xlabel("x")
            ax3d.set_ylabel("y")
            ax3d.set_zlabel("z")
            # Set dark mode colors for 3d axes
            if self.dark_mode:
                ax3d.w_xaxis.set_pane_color((0.1, 0.1, 0.1, 1))
                ax3d.w_yaxis.set_pane_color((0.1, 0.1, 0.1, 1))
                ax3d.w_zaxis.set_pane_color((0.1, 0.1, 0.1, 1))
                self.fig.patch.set_facecolor("#222")
            else:
                self.fig.patch.set_facecolor("white")
            self.canvas.draw()
            self.ax = ax3d  # update ax reference for future commands
            self.last_plot_type = '3d'
        except Exception as e:
            messagebox.showerror("3D Plot Error", f"Could not plot:\n{e}")

    def zoom_in(self):
        self.x_range = (self.x_range[0] * 0.8, self.x_range[1] * 0.8)
        self.y_range = (self.y_range[0] * 0.8, self.y_range[1] * 0.8)
        self.redraw_plot()

    def zoom_out(self):
        self.x_range = (self.x_range[0] * 1.2, self.x_range[1] * 1.2)
        self.y_range = (self.y_range[0] * 1.2, self.y_range[1] * 1.2)
        self.redraw_plot()

    def redraw_plot(self):
        if self.last_plot_type == '2d':
            self.plot_2d()
        elif self.last_plot_type == '3d':
            self.plot_3d()

    def prompt_set_theme(self):
        choice = simpledialog.askstring("Theme", "Choose theme: light or dark")
        if choice and choice.lower() in ['light', 'dark']:
            self.set_theme(choice.lower())

    def set_theme(self, theme):
        if theme == "dark":
            self.dark_mode = True
            bg = "#222"
            fg = "#eee"
            entry_bg = "#333"
            entry_fg = "#eee"
        else:
            self.dark_mode = False
            bg = "white"
            fg = "black"
            entry_bg = "white"
            entry_fg = "black"

        self.root.config(bg=bg)
        self.main_frame.config(style="My.TFrame")
        self.style.configure("My.TFrame", background=bg)
        self.entry.config(background=entry_bg, foreground=entry_fg)
        self.history_box.config(bg=entry_bg, fg=entry_fg)
        for btn in self.buttons.values():
            btn.config(style="My.TButton")
        self.style.configure("My.TButton", background=bg, foreground=fg)

        # Update plot colors if visible
        self.redraw_plot()

    def set_font_size(self):
        size = simpledialog.askinteger("Font Size", "Enter font size (12-36):", minvalue=12, maxvalue=36)
        if size:
            self.font_size = size
            self.entry.config(font=("Arial", self.font_size))
            self.history_box.config(font=("Arial", max(10, self.font_size - 6)))

    def show_history(self):
        history_text = "\n".join(self.history[-20:])
        messagebox.showinfo("History", history_text if history_text else "No history yet.")

    def clear_history(self):
        self.history.clear()
        self.update_history_box()
        self.save_session()  # Save the cleared history so it persists

    def save_session(self):
        session = {
            "history": self.history,
            "variables": self.variables,
            "dark_mode": self.dark_mode,
            "font_size": self.font_size,
            "x_range": self.x_range,
            "y_range": self.y_range,
            "current_user": self.current_user
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(session, f)

    def load_session(self):
        try:
            with open(SESSION_FILE, "r") as f:
                session = json.load(f)
                self.history = session.get("history", [])
                self.variables = session.get("variables", {})
                self.dark_mode = session.get("dark_mode", False)
                self.font_size = session.get("font_size", 18)
                self.x_range = tuple(session.get("x_range", (-10, 10)))
                self.y_range = tuple(session.get("y_range", (-10, 10)))
                self.current_user = session.get("current_user")
                self.update_history_box()
                self.entry.config(font=("Arial", self.font_size))
                self.history_box.config(font=("Arial", max(10, self.font_size - 6)))
                self.set_theme("dark" if self.dark_mode else "light")
        except FileNotFoundError:
            pass  # No session file yet

    def save_graph_png(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if file_path:
            self.fig.savefig(file_path)
            messagebox.showinfo("Saved", f"Graph saved as {file_path}")

    def save_graph_pdf(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                 filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if file_path:
            self.fig.savefig(file_path)
            messagebox.showinfo("Saved", f"Graph saved as {file_path}")

    def integrate_expression(self):
        expr = self.entry.get().replace("^", "**")
        x = symbols('x')
        try:
            sym_expr = sympify(expr)
            result = quad(lambdify(x, sym_expr), self.x_range[0], self.x_range[1])
            messagebox.showinfo("Integration Result", f"Integral over {self.x_range}: {result[0]}")
        except Exception as e:
            messagebox.showerror("Integration Error", f"Error integrating expression:\n{e}")

    def derive_expression(self):
        expr = self.entry.get().replace("^", "**")
        x = symbols('x')
        try:
            sym_expr = sympify(expr)
            derivative = diff(sym_expr, x)
            self.entry.delete(0, tk.END)
            self.entry.insert(tk.END, str(derivative))
        except Exception as e:
            messagebox.showerror("Derivative Error", f"Error deriving expression:\n{e}")

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def exit_fullscreen(self):
        self.is_fullscreen = False
        self.root.attributes("-fullscreen", False)

    def sign_in(self):
        user = simpledialog.askstring("Sign In", "Enter username:")
        if user:
            self.current_user = user
            self.load_user_variables()
            messagebox.showinfo("Signed In", f"Signed in as {user}")

    def sign_out(self):
        if self.current_user:
            self.save_user_variables()
            messagebox.showinfo("Signed Out", f"Signed out from {self.current_user}")
            self.current_user = None
            self.variables.clear()

    def save_user_variables(self):
        if not self.current_user:
            return
        filename = f"user_{self.current_user}.json"
        with open(filename, "w") as f:
            json.dump(self.variables, f)

    def load_user_variables(self):
        if not self.current_user:
            return
        filename = f"user_{self.current_user}.json"
        try:
            with open(filename, "r") as f:
                self.variables = json.load(f)
        except FileNotFoundError:
            self.variables = {}

if __name__ == "__main__":
    root = tk.Tk()
    app = CalculatorApp(root)
    root.mainloop()
