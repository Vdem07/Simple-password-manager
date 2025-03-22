import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import pyperclip  # Модуль для копирования в буфер обмена

class PasswordManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Password Manager")
        self.password_data = []
        self.storage_file = "passwords.csv"  # Имя файла для хранения данных
        self.visible_passwords = {}  # Словарь для отслеживания видимости паролей
        self.load_data()  # Загрузка данных при запуске приложения
        self.setup_ui()

    def setup_ui(self):
        # Фрейм для кнопок управления
        control_frame = tk.Frame(self.root)
        control_frame.pack(padx=10, pady=10, fill="x")

        # Кнопки управления
        tk.Button(control_frame, text="Импорт из CSV", command=self.import_csv).pack(side="left", padx=5)
        tk.Button(control_frame, text="Экспорт в CSV", command=self.save_to_csv).pack(side="left", padx=5)
        tk.Button(control_frame, text="Добавить запись", command=self.add_entry).pack(side="left", padx=5)
        tk.Button(control_frame, text="Редактировать запись", command=self.edit_entry).pack(side="left", padx=5)
        tk.Button(control_frame, text="Удалить запись", command=self.delete_entry).pack(side="left", padx=5)

        # Добавляем фрейм для поиска
        search_frame = tk.Frame(self.root)
        search_frame.pack(padx=10, pady=5, fill="x")
        
        # Метка и поле для поиска
        tk.Label(search_frame, text="Поиск:").pack(side="left", padx=5)
        self.search_entry = tk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=5)
        
        # Привязываем обработчик событий для автоматического поиска при вводе
        self.search_entry.bind("<KeyRelease>", self.search_entries)
        
        # Кнопка сброса поиска
        tk.Button(search_frame, text="Сбросить", command=self.reset_search).pack(side="left", padx=5)

        # Фрейм для таблицы и полосы прокрутки
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Добавление горизонтальной полосы прокрутки
        h_scroll = ttk.Scrollbar(tree_frame, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")

        # Добавление вертикальной полосы прокрутки
        v_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")

        # Таблица для отображения паролей
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("url", "username", "password", "comment", "tags"),
            show="headings",
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set
        )
        self.tree.heading("url", text="URL")
        self.tree.heading("username", text="Username")
        self.tree.heading("password", text="Password")
        self.tree.heading("comment", text="Comment")
        self.tree.heading("tags", text="Tags")
        
        # Настраиваем выравнивание для колонок
        self.tree.column("url", anchor="w")       # Левое выравнивание для URL
        self.tree.column("username", anchor="w")  # Левое выравнивание для имени пользователя
        self.tree.column("password", anchor="w")  # Левое выравнивание для пароля
        self.tree.column("comment", anchor="center")  # Центральное выравнивание для комментариев
        self.tree.column("tags", anchor="center")     # Центральное выравнивание для тегов
        
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        # Привязка полос прокрутки к таблице
        h_scroll.config(command=self.tree.xview)
        v_scroll.config(command=self.tree.yview)

        # Привязка функции вызова контекстного меню
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Привязка обновления видимости при двойном клике
        self.tree.bind("<Double-1>", self.toggle_password_visibility)

        # Создание контекстного меню
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Копировать логин", command=lambda: self.copy_selected("username"))
        self.context_menu.add_command(label="Копировать пароль", command=lambda: self.copy_selected("password"))
        self.context_menu.add_command(label="Показать/скрыть пароль", command=self.toggle_password_visibility)

        # Заполнение данных из self.password_data
        self.refresh_table()

    def search_entries(self, event=None):
        # Получаем текст для поиска
        search_text = self.search_entry.get().lower()
        
        # Если поисковая строка пустая, просто обновляем таблицу
        if not search_text:
            self.refresh_table()
            return
        
        # Очищаем таблицу
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        # Проходим по всем записям и ищем совпадения в URL или логине
        for i, entry in enumerate(self.password_data):
            url = str(entry["url"]).lower()
            username = str(entry["username"]).lower()
            
            # Если текст найден в URL или логине
            if search_text in url or search_text in username:
                # Маскируем пароль, если он не в списке видимых
                masked_password = entry["password"]
                if i not in self.visible_passwords:
                    masked_password = "*" * len(entry["password"])
                
                # Заменяем nan на черточку для комментариев и тегов
                comment = entry["comment"]
                tags = entry["tags"]
                
                if pd.isna(comment) or comment == "":
                    comment = "-"
                if pd.isna(tags) or tags == "":
                    tags = "-"
                
                # Добавляем найденную запись в таблицу
                item_id = self.tree.insert("", "end", values=(
                    entry["url"], 
                    entry["username"], 
                    masked_password, 
                    comment,
                    tags
                ))
                
                # Обновляем ID для видимых паролей
                if i in self.visible_passwords:
                    self.visible_passwords[i] = item_id
    
    def reset_search(self):
        # Очищаем поле поиска
        self.search_entry.delete(0, tk.END)
        
        # Обновляем таблицу
        self.refresh_table()

    def load_data(self):
        # Загрузка данных из файла при запуске приложения
        if os.path.exists(self.storage_file):
            try:
                data = pd.read_csv(self.storage_file)
                # Заменяем nan на пустые строки
                data = data.fillna("")
                self.password_data = data.to_dict(orient="records")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при загрузке данных из {self.storage_file}: {e}")

    def save_data(self):
        # Сохранение данных в файл
        try:
            data = pd.DataFrame(self.password_data)
            data.to_csv(self.storage_file, index=False)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении данных: {e}")

    def refresh_table(self):
        # Очистка таблицы и повторное заполнение
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        for i, entry in enumerate(self.password_data):
            # Маскируем пароль, если он не в списке видимых
            masked_password = entry["password"]
            if i not in self.visible_passwords:
                masked_password = "*" * len(entry["password"])
            
            # Заменяем nan на черточку для комментариев и тегов
            comment = entry["comment"]
            tags = entry["tags"]
            
            # Проверяем на nan и пустые строки
            if pd.isna(comment) or comment == "":
                comment = "-"
            if pd.isna(tags) or tags == "":
                tags = "-"
            
            item_id = self.tree.insert("", "end", values=(
                entry["url"], 
                entry["username"], 
                masked_password, 
                comment,  # Используем обработанное значение
                tags      # Используем обработанное значение
            ))
            
            # Запоминаем ID элемента для обновления видимости
            if i in self.visible_passwords:
                self.visible_passwords[i] = item_id

    def toggle_password_visibility(self, event=None):
        # Переключение видимости пароля
        selected_item = None
        if event:
            # Если вызвано из двойного клика
            selected_item = self.tree.identify_row(event.y)
            if not selected_item:
                return
            self.tree.selection_set(selected_item)
        else:
            # Если вызвано из меню
            selected_items = self.tree.selection()
            if not selected_items:
                messagebox.showwarning("Ошибка", "Выберите запись для отображения пароля.")
                return
            selected_item = selected_items[0]
        
        # Получаем индекс записи
        item_index = self.tree.index(selected_item)
        item = self.tree.item(selected_item)
        values = list(item["values"])
        
        # Проверяем, видим ли сейчас пароль
        real_password = self.password_data[item_index]["password"]
        if item_index in self.visible_passwords:
            # Скрываем пароль
            values[2] = "*" * len(real_password)
            self.tree.item(selected_item, values=values)
            del self.visible_passwords[item_index]
        else:
            # Показываем пароль
            values[2] = real_password
            self.tree.item(selected_item, values=values)
            self.visible_passwords[item_index] = selected_item

    def import_csv(self):
        # Импорт данных из CSV-файла
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not file_path:
            return
        try:
            data = pd.read_csv(file_path)
            new_data = data.to_dict(orient="records")
            self.password_data.extend(new_data)  # Добавляем данные к существующим
            self.refresh_table()
            self.save_data()  # Сохраняем обновленные данные
            messagebox.showinfo("Успешно", "Данные успешно импортированы из CSV!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при импорте данных: {e}")

    def save_to_csv(self):
        # Сохранение данных в CSV-файл
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not file_path:
            return
        try:
            data = pd.DataFrame(self.password_data)
            data.to_csv(file_path, index=False)
            messagebox.showinfo("Успешно", "Данные успешно сохранены в CSV!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении данных: {e}")

    def add_entry(self):
        # Окно для добавления новой записи
        self.edit_entry_window(None)

    def edit_entry(self):
        # Получаем выбранную запись для редактирования
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите запись для редактирования.")
            return
        
        # Получаем индекс записи
        index = self.tree.index(selected_item[0])
        # Используем реальные данные из password_data, а не отображаемые в таблице
        
        # Обрабатываем nan значения
        comment = self.password_data[index]["comment"]
        tags = self.password_data[index]["tags"]
        
        if pd.isna(comment):
            comment = ""
        if pd.isna(tags):
            tags = ""
        
        real_values = (
            self.password_data[index]["url"],
            self.password_data[index]["username"],
            self.password_data[index]["password"],  # Используем реальный пароль
            comment,  # Используем обработанное значение
            tags      # Используем обработанное значение
        )
        
        self.edit_entry_window(real_values)

    def edit_entry_window(self, entry):
        # Окно для добавления/редактирования записи
        window = tk.Toplevel(self.root)
        window.title("Добавить / Редактировать запись")

        # Поля для ввода информации
        tk.Label(window, text="URL").grid(row=0, column=0, padx=5, pady=5)
        url_entry = tk.Entry(window, width=40)
        url_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(window, text="Username").grid(row=1, column=0, padx=5, pady=5)
        username_entry = tk.Entry(window, width=40)
        username_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(window, text="Password").grid(row=2, column=0, padx=5, pady=5)
        password_entry = tk.Entry(window, width=40, show="*")  # Скрываем пароль при вводе
        password_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Добавляем переключатель для показа/скрытия пароля
        show_password_var = tk.BooleanVar()
        show_password_check = tk.Checkbutton(
            window, 
            text="Показать пароль", 
            variable=show_password_var,
            command=lambda: password_entry.config(show="" if show_password_var.get() else "*")
        )
        show_password_check.grid(row=2, column=2, padx=5, pady=5)

        tk.Label(window, text="Comment").grid(row=3, column=0, padx=5, pady=5)
        comment_entry = tk.Entry(window, width=40)
        comment_entry.grid(row=3, column=1, padx=5, pady=5)

        tk.Label(window, text="Tags").grid(row=4, column=0, padx=5, pady=5)
        tags_entry = tk.Entry(window, width=40)
        tags_entry.grid(row=4, column=1, padx=5, pady=5)

        # Если редактируется существующая запись, заполняем поля значениями
        if entry:
            url_entry.insert(0, entry[0])
            username_entry.insert(0, entry[1])
            password_entry.insert(0, entry[2])
            comment_entry.insert(0, entry[3])
            tags_entry.insert(0, entry[4])

        # Функция для сохранения новой записи
        def save_entry():
            new_entry = {
                "url": url_entry.get(),
                "username": username_entry.get(),
                "password": password_entry.get(),
                "comment": comment_entry.get(),
                "tags": tags_entry.get()
            }
            
            if entry:
                # Редактируем существующую запись
                index = self.tree.index(self.tree.selection()[0])
                self.password_data[index] = new_entry
                
                # Если пароль был видимым, обновляем видимость
                if index in self.visible_passwords:
                    del self.visible_passwords[index]
            else:
                # Добавляем новую запись
                self.password_data.append(new_entry)
                
            self.refresh_table()
            self.save_data()  # Сохраняем обновленные данные
            window.destroy()

        # Кнопка для сохранения записи
        tk.Button(window, text="Сохранить", command=save_entry).grid(row=5, columnspan=2, pady=10)

    def delete_entry(self):
        # Удаление выбранной записи
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите запись для удаления.")
            return

        item = self.tree.item(selected_item)
        url = item["values"][0]  # Извлекаем URL из выбранной записи

        # Запрос подтверждения удаления
        confirm = messagebox.askyesno("Подтверждение", f"Вы действительно хотите удалить запись: {url}?")
        if confirm:
            index = self.tree.index(selected_item)
            
            # Если пароль был видимым, удаляем из видимых
            if index in self.visible_passwords:
                del self.visible_passwords[index]
                
            # Удаляем запись
            del self.password_data[index]
            
            # Обновляем ключи в словаре visible_passwords
            updated_visible = {}
            for k, v in self.visible_passwords.items():
                if k > index:
                    updated_visible[k-1] = v
                else:
                    updated_visible[k] = v
            self.visible_passwords = updated_visible
            
            self.refresh_table()
            self.save_data()  # Сохраняем обновленные данные
            messagebox.showinfo("Удалено", "Запись успешно удалена.")

    def show_context_menu(self, event):
        # Показ контекстного меню при клике правой кнопкой мыши
        selected_item = self.tree.identify_row(event.y)
        if selected_item:
            self.tree.selection_set(selected_item)
            self.context_menu.post(event.x_root, event.y_root)

    def copy_selected(self, field):
        # Копирование значения логина или пароля
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите запись для копирования.")
            return
            
        # Получаем индекс записи и оригинальное значение
        index = self.tree.index(selected_item[0])
        value_to_copy = self.password_data[index][field]
        
        pyperclip.copy(value_to_copy)
        messagebox.showinfo("Скопировано", f"{field.capitalize()} скопирован в буфер обмена.")

# Запуск приложения
if __name__ == "__main__":
    root = tk.Tk()
    app = PasswordManagerApp(root)
    root.mainloop()