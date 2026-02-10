from PyPDF2 import PdfReader, PdfWriter
import tkinter as tk
from tkinter import filedialog, messagebox
import os

def dividir_pdf():
    ruta_pdf = filedialog.askopenfilename(
        title="Selecciona un PDF",
        filetypes=[("Archivos PDF", "*.pdf")]
    )

    if not ruta_pdf:
        return

    try:
        inicio = int(entry_inicio.get()) - 1
        fin = int(entry_fin.get())  
    except ValueError:
        messagebox.showerror("Error", "El rango debe ser numerico")
        return

    lector = PdfReader(ruta_pdf)
    total_paginas = len(lector.pages)

    if inicio < 0 or fin > total_paginas or inicio >= fin:
        messagebox.showerror(
            "Error",
            f"Rango invalido. El PDF tiene {total_paginas} paginas"
        )
        return

    escritor = PdfWriter()

    for i in range(inicio, fin):
        escritor.add_page(lector.pages[i])

    carpeta_salida = os.path.dirname(ruta_pdf)
    salida = os.path.join(carpeta_salida, "pdf_rango.pdf")

    with open(salida, "wb") as f:
        escritor.write(f)

    messagebox.showinfo("Listo", "PDF dividido por rango correctamente")

ventana = tk.Tk()
ventana.title("Dividir PDF por rango")
ventana.geometry("300x180")

tk.Label(ventana, text="Pagina inicio").pack()
entry_inicio = tk.Entry(ventana)
entry_inicio.pack()

tk.Label(ventana, text="Pagina fin").pack()
entry_fin = tk.Entry(ventana)
entry_fin.pack()

tk.Button(
    ventana,
    text="Seleccionar PDF y dividir",
    command=dividir_pdf
).pack(pady=10)

ventana.mainloop()
