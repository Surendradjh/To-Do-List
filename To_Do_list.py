import tkinter as tk
from tkinter import Toplevel, StringVar, OptionMenu, ttk
import pandas as pd
import datetime
import mysql.connector as mysql
import ssl

# linking mysql
db = mysql.connect(
    host='localhost',
    user='root',
    password='Pa1ss2wo3rd4@',
    # ssl_disabled=True
)

cursor = db.cursor()

cursor.execute('create database if not exists to_do_database')
cursor.execute('use to_do_database')

cursor.execute("""
                CREATE TABLE IF NOT EXISTS to_do_table (
                    id INT AUTO_INCREMENT PRIMARY KEY NOT NULL,
                    task TEXT NOT NULL,
                    Task_created_Time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    Time_Allocated DATETIME,
                    Status varchar(50) default 'still have time'
                )
                """)

cursor.execute("CREATE TABLE IF NOT EXISTS previous_tasks (id INT NOT NULL PRIMARY KEY, task TEXT, task_time DATETIME DEFAULT CURRENT_TIMESTAMP)")


cursor.execute("drop trigger if exists update_status_before_insert")
cursor.execute("drop trigger if exists previous_tasks_insertion")
cursor.execute("""
                CREATE TRIGGER previous_tasks_insertion
                after delete ON to_do_table
                FOR EACH ROW
                BEGIN
                    insert into previous_tasks(id,task)values(old.id,old.task);
                END
                """)

# Create the main application window
root = tk.Tk()
root.title("To-Do List Application")
root.geometry("600x400")  # Set the window size

# List to store references of open popup windows
popup_windows = []

# Function to close all open popup windows
def close_all_popups():
    for window in popup_windows:
        window.destroy()  # Close the window
    popup_windows.clear()  # Clear the list after closing the windows

# Function to add a task
def add_task():
    close_all_popups()  # Close other popups
    
    add_window = Toplevel(root)
    add_window.title("Add Task")
    add_window.geometry("300x200")
    popup_windows.append(add_window)  # Add this window to the list of popups
    
    tk.Label(add_window, text="Task Name:").grid(row=0, column=0, padx=10, pady=10)
    task_name_var = tk.StringVar()
    task_name_entry = tk.Entry(add_window, textvariable=task_name_var, width=25)
    task_name_entry.grid(row=0, column=1, padx=10, pady=10)
    
    tk.Label(add_window, text="Completion Time:").grid(row=1, column=0, padx=10, pady=10)
    completion_time_var = tk.StringVar()
    completion_time_entry = tk.Entry(add_window, textvariable=completion_time_var, width=15)
    completion_time_entry.grid(row=1, column=1, padx=10, pady=10)

    tk.Label(add_window, text="Time Unit:").grid(row=2, column=0, padx=10, pady=10)
    time_unit_var = StringVar(value="Minutes")
    time_unit_menu = OptionMenu(add_window, time_unit_var, "Minutes", "Hours", "Days")
    time_unit_menu.grid(row=2, column=1, padx=10, pady=10)

    def save_task():
        task_name = task_name_var.get()
        completion_time = completion_time_var.get()
        time_unit = time_unit_var.get()
        if task_name and completion_time.isdigit():
            current_time = datetime.datetime.now()

            if time_unit == 'Minutes':
                if int(completion_time) >= 60:
                    hours = int(completion_time) // 60
                    minutes = int(completion_time) % 60
                    completion_time = current_time + datetime.timedelta(hours=hours, minutes=minutes)
                else:
                    completion_time = current_time + datetime.timedelta(minutes=int(completion_time))
            elif time_unit == 'Hours':
                completion_time = current_time + datetime.timedelta(hours=int(completion_time))
            elif time_unit == 'Days':
                completion_time = current_time + datetime.timedelta(days=int(completion_time))

            cursor.execute("INSERT INTO to_do_table (task, Time_Allocated) VALUES (%s, %s)",
                           (task_name, str(completion_time)))
            db.commit()

            add_window.destroy()
            popup_windows.remove(add_window)

    save_button = tk.Button(add_window, text="Save Task", command=save_task)
    save_button.grid(row=3, column=0, columnspan=2, pady=10)

# Function to view tasks and mark them as completed, delete, or update
def view_tasks():
    close_all_popups()  # Close other popups
    
    view_window = Toplevel(root)
    view_window.title("View and Manage Tasks")
    view_window.geometry("1000x400")
    popup_windows.append(view_window)  # Add this window to the list of popups

    # Create a frame to hold the Treeview and the Scrollbars
    frame = tk.Frame(view_window)
    frame.grid(row=0, column=0, columnspan=2, sticky='nsew')  # Adjusted to use `grid`

    # Scrollbars
    vsb = tk.Scrollbar(frame, orient="vertical")
    hsb = tk.Scrollbar(frame, orient="horizontal")
    
    task_tree = ttk.Treeview(frame, columns=("ID", "Task", "Created Time", "Allocated Time", "Status"),
                             show="headings", yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    task_tree.heading("ID", text="ID")
    task_tree.heading("Task", text="Task")
    task_tree.heading("Created Time", text="Created Time")
    task_tree.heading("Allocated Time", text="Allocated Time")
    task_tree.heading("Status", text="Status")

    task_tree.grid(row=0, column=0, sticky='nsew')
    vsb.config(command=task_tree.yview)
    vsb.grid(row=0, column=1, sticky='ns')
    hsb.config(command=task_tree.xview)
    hsb.grid(row=1, column=0, sticky='ew')

    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    task_tree["selectmode"] = "extended"  # Enable multiple selection

    def display_tasks():
        cursor.execute("UPDATE to_do_table SET Status='out of time' WHERE time_allocated < CURRENT_TIMESTAMP")
        cursor.execute("DELETE FROM to_do_table WHERE task_created_time + INTERVAL 24 HOUR < CURRENT_TIMESTAMP")
        cursor.execute("SELECT * FROM to_do_table")
        tasks = cursor.fetchall()
        
        for task in tasks:
            task_tree.insert("", "end", values=task)

    def perform_deletion():
        selected_items = task_tree.selection()
        for item in selected_items:
            task_id = task_tree.item(item, "values")[0]
            cursor.execute("DELETE FROM to_do_table WHERE id = %s", (task_id,))
            db.commit()
            task_tree.delete(item)

    def mark_completed():
        selected_items = task_tree.selection()
        for item in selected_items:
            task_id = task_tree.item(item, "values")[0]
            cursor.execute("UPDATE to_do_table SET Status = 'Task completed' WHERE id = %s", (task_id,))
            db.commit()
            task_tree.item(item, values=(task_id, task_tree.item(item, "values")[1], 
                                         task_tree.item(item, "values")[2],
                                         task_tree.item(item, "values")[3], 'Task completed'))
    
    def update_task():
        selected_items = task_tree.selection()
        for item in selected_items:
            task_id = task_tree.item(item, "values")[0]
            task_name = task_tree.item(item, "values")[1]
            allocated_time =5 # datetime.datetime.strptime(allocated_time_str, "%Y-%m-%d %H:%M:%S")  - datetime.datetime.now()#task_tree.item(item, "values")[3]
            
            # Open the update window
            update_window = Toplevel(root)
            close_all_popups()
            update_window.title("Update Task")
            update_window.geometry("300x200")
            popup_windows.append(update_window)

            tk.Label(update_window, text="Task Name:").grid(row=0, column=0, padx=10, pady=10)
            update_task_name_var = tk.StringVar(value=task_name)
            update_task_name_entry = tk.Entry(update_window, textvariable=update_task_name_var, width=25)
            update_task_name_entry.grid(row=0, column=1, padx=10, pady=10)
            
            tk.Label(update_window, text="New Completion Time:").grid(row=1, column=0, padx=10, pady=10)
            update_completion_time_var = tk.StringVar(value=allocated_time)
            update_completion_time_entry = tk.Entry(update_window, textvariable=update_completion_time_var, width=15)
            update_completion_time_entry.grid(row=1, column=1, padx=10, pady=10)

            tk.Label(update_window, text="Time Unit:").grid(row=2, column=0, padx=10, pady=10)
            update_time_unit_var = StringVar(value="Minutes")
            update_time_unit_menu = OptionMenu(update_window, update_time_unit_var, "Minutes", "Hours", "Days")
            update_time_unit_menu.grid(row=2, column=1, padx=10, pady=10)

            def save_update():

                new_task_name = update_task_name_var.get()
                new_completion_time = update_completion_time_var.get()
                new_time_unit = update_time_unit_var.get()

                if new_task_name and new_completion_time.isdigit():
                    current_time = datetime.datetime.now()

                    if new_time_unit == 'Minutes':
                        new_completion_time = current_time + datetime.timedelta(minutes=int(new_completion_time))
                    elif new_time_unit == 'Hours':
                        new_completion_time = current_time + datetime.timedelta(hours=int(new_completion_time))
                    elif new_time_unit == 'Days':
                        new_completion_time = current_time + datetime.timedelta(days=int(new_completion_time))

                    cursor.execute("UPDATE to_do_table SET task = %s, Time_Allocated = %s WHERE id = %s",
                                   (new_task_name, str(new_completion_time), task_id))
                    db.commit()

                    update_window.destroy()
                    popup_windows.remove(update_window)
                    view_tasks()

        save_button = tk.Button(update_window, text="Update Task", command=save_update)
        save_button.grid(row=3, column=0, columnspan=2, pady=10)

    # Buttons for managing tasks in grid format
    delete_button = tk.Button(view_window, text="Delete Selected Tasks", command=perform_deletion)
    delete_button.grid(row=1, column=0, padx=1, pady=5)  # Button 1 (Row 1, Column 0)

    complete_button = tk.Button(view_window, text="Complete Selected Tasks", command=mark_completed)
    complete_button.grid(row=1, column=1, padx=1, pady=5)  # Button 2 (Row 1, Column 1)

    update_button = tk.Button(view_window, text="Update Selected Task", command=update_task)
    update_button.grid(row=2, column=0, padx=5, pady=5)  # Button 3 (Row 2, Column 0)

    previous_task_button=tk.Button(view_window,text="display_previous_Tasks",command=display_previous_tasks)
    previous_task_button.grid(row=2, column=1, padx=5, pady=5)
    display_tasks()



def display_previous_tasks():
    close_all_popups()
    previous_window = Toplevel(root)
    previous_window.title("Previous Tasks")
    previous_window.geometry("600x300")
    popup_windows.append(previous_window)

    frame = tk.Frame(previous_window)
    frame.pack(fill=tk.BOTH, expand=True)

    vsb = tk.Scrollbar(frame, orient="vertical")
    hsb = tk.Scrollbar(frame, orient="horizontal")
    
    previous_tree = ttk.Treeview(frame, columns=("ID", "Task", "Deleted Time"),
                                 show="headings", yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    previous_tree.heading("ID", text="ID")
    previous_tree.heading("Task", text="Task")
    previous_tree.heading("Deleted Time", text="Deleted Time")

    previous_tree.grid(row=0, column=0, sticky='nsew')
    vsb.config(command=previous_tree.yview)
    vsb.grid(row=0, column=1, sticky='ns')
    hsb.config(command=previous_tree.xview)
    hsb.grid(row=1, column=0, sticky='ew')

    # Load tasks from `previous_tasks`
    def display_previous_tasks():
        cursor.execute("SELECT * FROM previous_tasks")
        for task in cursor.fetchall():
            previous_tree.insert("", "end", values=task)

    display_previous_tasks()


# Create buttons
add_button = tk.Button(root, text="Add Task", command=add_task, width=20, height=2)
view_button = tk.Button(root, text="View and Delete Tasks", command=view_tasks, width=20, height=2)

# Place buttons on the window
add_button.pack(pady=10)
view_button.pack(pady=10)

# Run the application
root.mainloop()









