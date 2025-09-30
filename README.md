# Paper Note Tool

A lightweight literature note-taking tool built with **Streamlit**.  
It supports adding, editing, deleting, importing, and exporting papers, and automatically saves the data into CSV / JSON / Excel (xlsx) files for easy backup or later analysis.

Once this tool is running, it will simpy run on your browser.

Features include:
- Tag filtering
- Keyword search
- Duplicate entry detection (based on Title + Authors)
- Sorting by year or by fields
- etc.

## Disclaimer
This tool has been fully tested only on **macOS**.  
Windows instructions were written with the help of ChatGPT and may differ depending on your system configuration.  
If you encounter errors, please carefully read the error message, adjust accordingly, or open an Issue with details (error log, Python version, OS).

---

## 1. Go to your working directory
All commands must be run inside your project folder.

**macOS / Linux**
```bash
cd ~/Desktop #change the directory as you need
mkdir paper-note-tool && cd paper-note-tool
```

**Windows (PowerShell)**
```powershell
cd ~\Desktop #change the directory as you need
mkdir paper-note-tool; cd paper-note-tool
```

---

## 2. Install dependencies

**macOS / Linux**
```bash
pip install streamlit pandas xlsxwriter
```

**Windows (PowerShell)**
```powershell
pip install streamlit pandas xlsxwriter
```

---

## 3. Create or copy the script

### Option 1: Copy the provided script
If you already have `paper_note_tool.py` from this repository, simply place it into your project folder.

### Option 2: Create the script manually
If you prefer to create it yourself:

**macOS / Linux**
```bash
nano paper_note_tool.py
```
Paste the code into the nano editor.  
- To **save**: press `Ctrl+O`, then press `Enter`.  
- To **exit**: press `Ctrl+X`.

⚠️ Note: It is recommended to use an editor like **VS Code** or **Notepad++**, since terminal editors (like nano) may not handle special characters well.

**Windows**  
Use Notepad or VS Code to create a file named `paper_note_tool.py` in your project folder, then paste the code and save.

---

## 4. Run
Run inside the project folder:
```bash
streamlit run paper_note_tool.py
```

This will display a local address (by default `http://localhost:8501`).  
Open it in your browser.

---

## 5. Data storage
The app will create a folder named `paper_notes_data/` inside your project directory.  
It contains three files:
- `papers.csv`
- `papers.json`
- `papers.xlsx`

The app will automatically save and back up these files every time you add, edit, or delete a paper.

---

## Troubleshooting

### A. `streamlit: command not found` / `'streamlit' is not recognized`
This means the Streamlit executable is not on your PATH.

**Immediate alternative:**

**macOS / Linux**
```bash
python3 -m streamlit run paper_note_tool.py
```

**Windows**
```powershell
python -m streamlit run paper_note_tool.py
```

#### What does `-m` mean?
The flag `-m` tells Python to **run a module**.

For example:
```bash
python3 -m pip install ...
```
ensures you are using the `pip` module from the same Python interpreter you are calling.  
This avoids the common issue where `pip` installs packages into a different Python version.

Similarly:
```bash
python3 -m streamlit run ...
```
guarantees that Streamlit runs from the correct Python environment, even if the executable is not in PATH.

---

**Permanent fix (macOS / Linux):**

1. Find your Python user base path:
   ```bash
   python3 -m site --user-base
   ```
   Example output:
   - macOS: `~/Library/Python/3.11`
   - Linux: `~/.local`

2. Executables are **usually** inside the `bin` folder under that path.  
   Example: `~/Library/Python/3.11/bin`

3. Open your shell configuration file:
   - If you use zsh (default on macOS):
     ```bash
     nano ~/.zshrc
     ```
   - If you use bash:
     ```bash
     nano ~/.bash_profile
     ```

4. In the nano editor, scroll to the bottom and add this line (replace with your actual path):
   ```bash
   export PATH="$HOME/Library/Python/3.11/bin:$PATH"
   ```

5. Save: `Ctrl+O` → `Enter`  
   Exit: `Ctrl+X`

6. Reload your configuration:
   ```bash
   source ~/.zshrc
   ```  
   or  
   ```bash
   source ~/.bash_profile
   ```

---

**Permanent fix (Windows):**

1. Check where Streamlit is installed:
   ```powershell
   pip show streamlit
   where streamlit
   ```

2. Note the `Scripts` folder path, e.g.:
   ```
   C:\Users\<YourName>\AppData\Local\Programs\Python\Python311\Scripts\
   ```

3. Add this folder to your **System Environment Variables → Path**.  
   After updating, close and reopen PowerShell.

---

### B. `pip` and `python` mismatch
If you installed packages but Python still says “module not found,” your `pip` may belong to a different Python version.

**Solution: always use the `-m` form to ensure they match.**

**macOS / Linux**
```bash
python3 -m pip install streamlit pandas xlsxwriter
```

**Windows**
```powershell
python -m pip install streamlit pandas xlsxwriter
```

---

### C. Port already in use
If Streamlit says “Port 8501 is already in use,” it means another process is using that port.

Run the app on another port, for example 8502:
```bash
streamlit run paper_note_tool.py --server.port 8502
```

---

### D. CSV / Excel encoding issues
CSV files are saved with `utf-8-sig`, which Excel usually recognizes.  
If you still see garbled characters, open `papers.xlsx` instead.
