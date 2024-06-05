import tkinter as tk
from tkinter import BOTH, SINGLE, Listbox, simpledialog, messagebox
import requests
import webbrowser
import os
import configparser


def get_gitlab_token():
    """Gets the GitLab personal access token.

    Attempts to read the token from the config file. If not found, prompts
    the user for the token and saves it to the config file.

    Returns:
        str: The GitLab personal access token, or None if the user cancels.
    """
    config_dir = os.path.join(os.path.expanduser("~"), ".config", "GitThereFast")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()

    try:
        config.read(config_file)
        return config.get("GitLab", "token")
    except (configparser.NoSectionError, configparser.NoOptionError):
        token = simpledialog.askstring(
            "GitLab Token",
            "Enter a GitLab Personal Access Token\n\n"
            "You can generate one at 'https://gitlab.com/-/profile/personal_access_tokens' with 'read_api' scope.",
            show="*")
        if token:
            try:
                os.makedirs(config_dir, exist_ok=True)
                with open(config_file, "w") as f:
                    config.add_section("GitLab")
                    config.set("GitLab", "token", token)
                    config.write(f)
                return token
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save token: {e}")
        return None


class ListboxDialog(tk.simpledialog.Dialog):
    """Custom dialog with a listbox for selection."""
    def __init__(self, parent, title, choices):
        self.choices = choices
        super().__init__(parent, title)

    def body(self, master):
        self.listbox = Listbox(master, selectmode=SINGLE, takefocus=True, activestyle="none")
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
                self.listbox.activate(index - 1)

    def on_down_key(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.choices) - 1:
                self.listbox.selection_clear(index)
                self.listbox.selection_set(index + 1)
                self.listbox.activate(index + 1)

    def on_return_key(self, event):
        self.apply()

    def apply(self):
        selection = self.listbox.curselection()
        if selection:
            self.result = selection[0]  # Return the index of the selected item


def open_gitlab_project():
    """Prompts the user for a project name, searches for it on GitLab,
    and opens the project's URL in a web browser.
    """
    token = get_gitlab_token()
    if not token:
        return

    root = tk.Tk()
    root.withdraw()

    project_name = tk.simpledialog.askstring("GitLab Project Opener", "Enter project name:")
    if not project_name:
        return

    gitlab_url = "https://gitlab.com/api/v4/projects"
    params = {"search": project_name, "simple": True, "membership": True}
    headers = {"PRIVATE-TOKEN": token}

    response = requests.get(gitlab_url, params=params, headers=headers)
    if response.status_code == 200:
        projects = response.json()
        if len(projects) == 1:
            project_url = projects[0]["web_url"]
            webbrowser.open(project_url)
        elif len(projects) > 1:
            # Show listbox dialog for selection
            project_names = [p["name"] for p in projects]
            dialog = ListboxDialog(root, "Multiple Projects Found", project_names)
            if dialog.result is not None: # User made a selection
                chosen_index = dialog.result
                project_url = projects[chosen_index]["web_url"]
                webbrowser.open(project_url)
        else:
            messagebox.showinfo("GitLab Project Opener", "No matching projects found.")
    else:
        messagebox.showerror("Error", f"GitLab API request failed with code {response.status_code}")


if __name__ == "__main__":
    open_gitlab_project()
