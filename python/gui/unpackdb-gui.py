#!/usr/bin/env python3

import zlib
import os.path
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

PROCESSED_TABLES = []

def unpack(data):
    """
    Распаковывает данные из базы данных.
    """
    return zlib.decompress(data[6:]).decode()


def format_row(text):
    """
    Форматирует строку.
    """
    mapping_symbols = {
        "\n": "",
        "\r": "",
        "[": "",
        "]": "",
        "'": "",
    }

    for k, v in mapping_symbols.items():
        text = text.replace(k, v)

    return text


def process(data):
    """
    Обрабатывает данные.
    """

    unpacked_text = {}
    for i, row in enumerate(data):
        r = ""
        for x in row:
            if x[0] == 0xFE and x[1] == 0xFF:
                r += unpack(x)
        unpacked_text[data[i][1]] = format_row(r)

    return unpacked_text


def handle_table(dbfile, table_name, chunk_size=5000):
    """
    Обрабатывает таблицу.
    """

    with sqlite3.connect(dbfile) as con:
        try:
            select_count_q = f"SELECT COUNT(*) FROM {table_name}"
            cursor = con.cursor()
            cursor.execute(select_count_q)
            num_records = int(cursor.fetchone()[0])

            # Пересоздание копии таблицы.
            cursor.execute(f"DROP TABLE IF EXISTS Unpack_{table_name};")
            cursor.execute(f"CREATE TABLE Unpack_{table_name} AS SELECT id, body FROM {table_name} LIMIT 0;")

            processed_records = 0
            while processed_records < num_records:
                select_chunk_q = f"SELECT body, id FROM {table_name} LIMIT {chunk_size} OFFSET {processed_records}"
                cursor.execute(select_chunk_q)
                chunk = cursor.fetchall()
                modified_data = process(chunk)
                insert_q = f"INSERT INTO Unpack_{table_name} (id, body) VALUES (?, ?)"
                cursor.executemany(insert_q, modified_data.items())
                processed_records += chunk_size
                con.commit()

            PROCESSED_TABLES.append(table_name)
            messagebox.showinfo("Готово", "Таблица успешно обработана!")
            show_processed_tables()
            
            if checkbox_show_content.get():
                show_table_content(dbfile, f"Unpack_{table_name}")

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", e)
            return


def get_table_list(dbfile):
    """
    Возвращает список таблиц.
    """

    with sqlite3.connect(dbfile) as con:
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC;")
        tables = cursor.fetchall()
        table_list = [table[0] for table in tables]
        return table_list


def open_database():
    """
    Открывает базу данных.
    """

    try:
        dbfile = filedialog.askopenfilename(title="Выберите файл SQLite", 
                                            filetypes=[("SQLite files", "*.sqlite")], 
                                            initialdir="/home")
        if dbfile:
            entry_loaded_db.config(state=tk.NORMAL)
            entry_loaded_db.delete(0, tk.END)
            entry_loaded_db.insert(0, dbfile)
            entry_loaded_db.config(state=tk.DISABLED)
            btn_process.config(state=tk.NORMAL)
            entry_table_name.set("")

            table_list = get_table_list(dbfile)
            entry_table_name.set("Выбор таблицы")
            entry_table_name_menu = ttk.Combobox(root, 
                                                textvariable=entry_table_name, 
                                                values=table_list, width=200)
            entry_table_name_menu.pack(after=btn_open_database)
                
            messagebox.showinfo("Успех", f"Загружена база {os.path.basename(dbfile)}")
    except sqlite3.Error as e:
        messagebox.showerror("Ошибка", e)
        return


def process_table():
    """
    Обрабатывает таблицу.
    """

    dbfile = entry_loaded_db.get()
    table_name = entry_table_name.get()
    if dbfile and table_name:
        handle_table(dbfile, table_name)


def show_processed_tables():
    """
    Обновляет список обработанных таблиц.
    """

    list_processed_tables.delete(0, tk.END)
    for table_name in PROCESSED_TABLES:
        list_processed_tables.insert(tk.END, f"Unpack_{table_name}")


def show_table_content(dbfile, table_name):
    """
    Показывает содержимое таблицы с нумерацией строк.
    """

    select_all_q = f"SELECT * FROM {table_name}"

    with sqlite3.connect(dbfile) as con:
        cursor = con.cursor()
        cursor.execute(select_all_q)
        rows = cursor.fetchall()
    
        table_content_window = tk.Toplevel()
        table_content_window.title(f"Содержимое таблицы {table_name}")
        table_content_window.geometry("800x600")

        table_frame = ttk.Frame(table_content_window)
        table_frame.pack(pady=10, expand=True, fill="both")

        columns = tuple(range(len(rows[0]) + 1))

        tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")

        column_settings = {
            0: {"anchor": "center", "stretch": True, "width": 20, "text": "№"},
            1: {"anchor": "center", "stretch": True, "width": 200, "text": "ID"},
            2: {"anchor": "center", "stretch": True, "width": 800, "text": "Body"},
        }
        for column, settings in column_settings.items():
            tree.column(column, anchor=settings["anchor"], stretch=settings["stretch"], width=settings["width"])
            tree.heading(column, text=settings["text"])

        for i, row in enumerate(rows, start=1):
            tree.insert('', 'end', values=[i] + list(row))

        tree_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side="right", fill="y")

        tree.pack(expand=True, fill="both")

        def copy_selection():
            """
            Копирует выделенную строку в буфер обмена.
            """

            table_content_window.clipboard_clear()
            selected_row = tree.selection()
            if selected_row:
                selected_text = "\t".join(tree.item(selected_row)['values'][1:])
                table_content_window.clipboard_clear()
                table_content_window.clipboard_append(selected_text)

        tree.bind("<Control-c>", lambda event: copy_selection())
        copy_button = ttk.Button(table_content_window, text="Копировать", command=copy_selection)
        copy_button.pack()

        table_content_window.mainloop()


root = tk.Tk()
root.title("Обработка таблиц")
root.geometry("1280x720")

lbl_loaded_db = tk.Label(root, text="Загруженная база:")
lbl_loaded_db.pack(pady=10)

entry_loaded_db = tk.Entry(root, width=200)
entry_loaded_db.pack(pady=5)
entry_loaded_db.config(state=tk.DISABLED)

btn_open_database = tk.Button(root, text="Загрузить базу", command=open_database)
btn_open_database.pack(pady=10)

entry_table_name = tk.StringVar()
entry_table_name.set("Выбранная таблица")  

checkbox_show_content = tk.BooleanVar()
checkbox_show_content.set(True)
chk_show_content = tk.Checkbutton(root, text="""Показать распакованное содержимое копии таблицы после обработки""", 
                                 variable=checkbox_show_content)
chk_show_content.pack(pady=5)

btn_process = tk.Button(root, text="Обработать таблицу", command=process_table, state=tk.DISABLED)
btn_process.pack(pady=10)

lbl_processed_tables = tk.Label(root, text="Список обработанных таблиц:")
lbl_processed_tables.pack(pady=5)

scroll_processed_tables = tk.Scrollbar(root)
scroll_processed_tables.pack(side=tk.RIGHT, fill=tk.Y)

list_processed_tables = tk.Listbox(root, yscrollcommand=scroll_processed_tables.set, width=200)
list_processed_tables.pack(pady=5)

scroll_processed_tables.config(command=list_processed_tables.yview)

root.mainloop()
