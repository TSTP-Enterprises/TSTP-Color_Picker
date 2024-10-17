<h1>TSTP Color Picker - PyQt5 Desktop Application</h1>

<p align="center">
TSTP Color Picker is a feature-rich, PyQt5-based desktop application for Windows that allows users to easily select and manage custom colors. 
With its intuitive interface, users can select colors from a dialog, directly from the screen, or via a global hotkey. 
Colors are saved in a SQLite3 database and displayed in a sleek, dark-themed grid interface.
</p>
<p align="center">
  <img src="https://github.com/user-attachments/assets/b7f7bf40-718b-47ac-86ff-ccb47ba8094b" />
</p>

<h2>Key Features</h2>
<ul>
  <li><strong>Color Selection</strong>: Pick colors using a standard color dialog or capture colors directly from any screen/window.</li>
  <li><strong>Global Hotkey</strong>: Quickly pick a color under the cursor using <code>Alt+1</code> and save it to your color palette.</li>
  <li><strong>Customizable UI</strong>: A compact mode and system tray support for easy access to color selection.</li>
  <li><strong>SQLite Database Integration</strong>: Save, load, and manage colors in a SQLite database, with built-in duplicate detection and handling.</li>
  <li><strong>System Tray Integration</strong>: The application runs quietly in the system tray, allowing you to pick colors without opening the full interface.</li>
  <li><strong>3D Dark-Themed Design</strong>: The UI is styled with a 3D effect and a visually pleasing dark theme.</li>
  <li><strong>Color Management</strong>: View, copy, and manage saved colors with preview and copy functionality.</li>
</ul>

<h2>Requirements</h2>
<ul>
  <li><strong>Python 3.8+</strong></li>
  <li><strong>PyQt5</strong>: Install via <code>pip install PyQt5</code></li>
  <li><strong>pynput</strong>: Install via <code>pip install pynput</code></li>
  <li><strong>SQLite3</strong> (built into Python)</li>
</ul>

<h2>Installation</h2>
<ol>
  <li>Clone the repository:
    <pre><code>git clone https://github.com/your-repo/tstp-color-picker.git</code></pre>
  </li>
  <li>Navigate to the project directory:
    <pre><code>cd tstp-color-picker</code></pre>
  </li>
  <li>Install the dependencies:
    <pre><code>pip install -r requirements.txt</code></pre>
  </li>
  <li>Run the application:
    <pre><code>python color_picker.py</code></pre>
  </li>
</ol>

<h2>Logging and Error Handling</h2>
<p>
All application activities are logged to a <code>color_picker.log</code> file, ensuring smooth troubleshooting and debugging with robust error handling.
</p>

<h2>Future Features</h2>
<ul>
  <li>Multi-monitor support for capturing colors across screens.</li>
  <li>Advanced color management and export options.</li>
</ul>

<p>Feel free to contribute and make suggestions for new features!</p>
