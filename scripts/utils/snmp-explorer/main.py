import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import os

class SNMPExplorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SNMP OID Explorer")
        self.root.geometry("1000x600")

        # Data storage
        self.oid_data = []

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        # Top Frame for controls
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        self.load_btn = ttk.Button(top_frame, text="Load Zabbix XML", command=self.load_xml)
        self.load_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(top_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_data)
        self.search_entry = ttk.Entry(top_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(top_frame, text="Ready")
        self.status_label.pack(side=tk.RIGHT, padx=5)

        # Treeview for displaying data
        columns = ("name", "oid", "key", "description")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("name", text="Name")
        self.tree.heading("oid", text="OID")
        self.tree.heading("key", text="Key")
        self.tree.heading("description", text="Description")

        self.tree.column("name", width=250)
        self.tree.column("oid", width=200)
        self.tree.column("key", width=150)
        self.tree.column("description", width=300)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Right click menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Copy OID", command=self.copy_oid)
        self.context_menu.add_command(label="Copy All Details", command=self.copy_details)
        
        self.tree.bind("<Button-3>", self.show_context_menu)

    def load_xml(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            self.oid_data = []
            
            # Helper to extract data from item elements
            def extract_item(item_element):
                name = item_element.findtext("name", "")
                oid = item_element.findtext("snmp_oid", "")
                key = item_element.findtext("key", "")
                desc = item_element.findtext("description", "")
                
                if oid: # Only add items with OIDs
                    return {
                        "name": name,
                        "oid": oid,
                        "key": key,
                        "description": desc
                    }
                return None

            # Traverse Zabbix export format
            # 1. Standard Items in Templates
            for item in root.findall(".//items/item"):
                data = extract_item(item)
                if data:
                    self.oid_data.append(data)
            
            # 2. Item Prototypes in Discovery Rules
            for prototype in root.findall(".//discovery_rules/discovery_rule/item_prototypes/item_prototype"):
                data = extract_item(prototype)
                if data:
                    self.oid_data.append(data)

            self.update_tree(self.oid_data)
            self.status_label.config(text=f"Loaded {len(self.oid_data)} OIDs")
            
        except ET.ParseError:
            messagebox.showerror("Error", "Invalid XML file.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process file: {str(e)}")

    def update_tree(self, data):
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for item in data:
            self.tree.insert("", tk.END, values=(
                item["name"],
                item["oid"],
                item["key"],
                item["description"].replace('\n', ' ')[:100] + "..." if len(item["description"]) > 100 else item["description"].replace('\n', ' ')
            ))

    def filter_data(self, *args):
        query = self.search_var.get().lower()
        if not query:
            self.update_tree(self.oid_data)
            return

        filtered = []
        for item in self.oid_data:
            if (query in item["name"].lower() or 
                query in item["oid"].lower() or 
                query in item["key"].lower() or 
                query in item["description"].lower()):
                filtered.append(item)
        
        self.update_tree(filtered)

    def show_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.context_menu.post(event.x_root, event.y_root)

    def copy_oid(self):
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            oid = item['values'][1]
            self.root.clipboard_clear()
            self.root.clipboard_append(oid)
            self.status_label.config(text="OID copied to clipboard")

    def copy_details(self):
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            vals = item['values']
            text = f"Name: {vals[0]}\nOID: {vals[1]}\nKey: {vals[2]}\nDescription: {vals[3]}"
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_label.config(text="Details copied to clipboard")

if __name__ == "__main__":
    root = tk.Tk()
    app = SNMPExplorerApp(root)
    root.mainloop()
