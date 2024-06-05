import threading
from tkinter import BOTH, SINGLE, Listbox, simpledialog, messagebox, Tk
import requests
import webbrowser
import os
import configparser
import json

import platform

def get_config_dir():
    """Gets the configuration directory based on the operating system."""
    if platform.system() == "Windows":
        appdata = os.getenv('APPDATA')
        if appdata is None:
            return os.path.join(os.path.expanduser("~"), "AppData", "Local", "GitThereFast")
        else:
            return os.path.join(appdata, "GitThereFast")
    else:
        return os.path.join(os.path.expanduser("~"), ".config", "GitThereFast")

CONFIG_DIR = get_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")
CACHE_FILE = os.path.join(CONFIG_DIR, "projects_cache.json")

def get_gitlab_token():
    config = configparser.ConfigParser()

    try:
        config.read(CONFIG_FILE)
        return config.get("GitLab", "token")
    except (configparser.NoSectionError, configparser.NoOptionError):
        root = Tk()
        root.withdraw()
        token = simpledialog.askstring("GitLab Token", "Enter a GitLab Personal Access Token\n\n"
                                       "You can generate one at 'https://gitlab.com/-/profile/personal_access_tokens' with 'read_api' scope.",
                                       show="*",
                                       parent=root)
        if token:
            try:
                os.makedirs(CONFIG_DIR, exist_ok=True)
                with open(CONFIG_FILE, "w") as f:
                    config.add_section("GitLab")
                    config.set("GitLab", "token", token)
                    config.write(f)
                return token
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save token: {e}")
        return None


def strip_common_prefix(strings=[]):
    split_strings = [s.split('/') for s in strings]
    min_length = min(len(parts) for parts in split_strings)

    common_prefix_length = 0
    for i in range(min_length):
        if all(parts[i] == split_strings[0][i] for parts in split_strings):
            common_prefix_length += 1
        else:
            break

    return ['/'.join(parts[common_prefix_length:]) for parts in split_strings]


class ListboxDialog(simpledialog.Dialog):
    """Custom dialog with a listbox for selection."""
    def __init__(self, parent, title, choices, width):
        self.choices = choices
        self.width = width
        super().__init__(parent, title)

    def body(self, master):
        self.listbox = Listbox(master, selectmode=SINGLE, width=self.width)
        for i, choice in enumerate(self.choices):
            self.listbox.insert(i, choice)
        self.listbox.pack(expand=True, fill=BOTH)

        # Bind arrow keys and Enter to update selection
        self.listbox.bind("<Up>", self.on_up_key)
        self.listbox.bind("<Down>", self.on_down_key)
        self.listbox.bind("<Return>", self.on_return_key)

        # Initially select the first item
        self.listbox.selection_set(0)
        self.listbox.activate(0)
        return self.listbox

    def on_up_key(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            if index > 0:
                self.listbox.selection_clear(index)
                self.listbox.selection_set(index - 1)
                self.listbox.activate(index)

    def on_down_key(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.choices) - 1:
                self.listbox.selection_clear(index)
                self.listbox.selection_set(index + 1)
                self.listbox.activate(index)

    def on_return_key(self, event):
        self.apply()

    def apply(self):
        selection = self.listbox.curselection()
        if selection:
            self.result = selection[0]  # Return the index of the selected item


def fetch_projects_from_gitlab(token):
    gitlab_url = "https://gitlab.com/api/v4/projects"
    params = {"per_page": 1000, "membership": True, "order_by": "last_activity_at", "sort": "desc", "archived": False}
    headers = {"PRIVATE-TOKEN": token}

    response = requests.get(gitlab_url, params=params, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def update_project_cache(token):
    projects = fetch_projects_from_gitlab(token)
    if projects:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(projects, f)
    return projects


def load_project_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return None


def open_gitlab_project():
    """Prompts the user for a project name, searches for it on GitLab,
    and opens the project's URL in a web browser.
    """
    token = get_gitlab_token()
    if not token:
        return

    root = Tk()
    root.eval('tk::PlaceWindow . center')
    root.withdraw()

    query = simpledialog.askstring("Git There Fast", "Enter project name:", parent=root)
    if not query:
        return

    # Load cached projects
    projects = load_project_cache()

    if not projects:
        # Fetch projects if cache is not available
        projects = update_project_cache(token)
    else:
        # Update the cache in the background
        threading.Thread(target=update_project_cache, args=(token,)).start()

    if not projects:
        messagebox.showerror("Error", "Failed to fetch projects from GitLab.")
        return

    projects = [p for p in projects if query.lower() in p['path_with_namespace'].lower()]

    if len(projects) == 1:
        project_url = projects[0]["web_url"]
        webbrowser.open(project_url)

    elif len(projects) > 1:
        full_paths = [p['path_with_namespace'] for p in projects]
        project_descriptions = strip_common_prefix(full_paths)

        # Calculate the width of the longest string for the listbox
        max_width = max(len(desc) for desc in project_descriptions) + 5

        dialog = ListboxDialog(root, "Select Project", project_descriptions, max_width)
        if dialog.result is not None:  # User made a selection
            chosen_index = dialog.result
            project_url = projects[chosen_index]["web_url"]
            webbrowser.open(project_url)
    else:
        messagebox.showinfo("Git There Fast", "No matching projects found.")


if __name__ == "__main__":
    open_gitlab_project()
