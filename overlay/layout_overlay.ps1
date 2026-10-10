# Corne layout overlay: F24 (EDIT + N on the keyboard) shows / hides layout.png.
# Clicking the image also hides it. The image is re-read on every show, so a fresh
# render (python overlay/render_layout.py) appears without restarting this script.
#
# Run:  powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File layout_overlay.ps1

$png = Join-Path $PSScriptRoot 'layout.png'

Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type -ReferencedAssemblies System.Windows.Forms, System.Drawing -TypeDefinition @'
using System;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

public class LayoutOverlay : Form
{
    [DllImport("user32.dll")] static extern bool RegisterHotKey(IntPtr hWnd, int id, uint mod, uint vk);
    [DllImport("user32.dll")] static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    const int WM_HOTKEY = 0x0312;
    const uint VK_F24 = 0x87;
    const uint MOD_NOREPEAT = 0x4000;

    readonly string path;
    readonly PictureBox pic = new PictureBox();
    bool allowShow;
    public bool HotkeyOk;

    public LayoutOverlay(string path)
    {
        this.path = path;
        Text = "Corne layout";
        FormBorderStyle = FormBorderStyle.None;
        ShowInTaskbar = false;
        TopMost = true;
        StartPosition = FormStartPosition.Manual;
        BackColor = Color.FromArgb(20, 23, 30);
        pic.Dock = DockStyle.Fill;
        pic.SizeMode = PictureBoxSizeMode.Zoom;
        pic.Click += (s, e) => Hide();
        Controls.Add(pic);
    }

    // topmost, no taskbar button, never steals focus from the app you are typing in
    protected override CreateParams CreateParams
    {
        get
        {
            var cp = base.CreateParams;
            cp.ExStyle |= 0x00000008 | 0x00000080 | 0x08000000;
            return cp;
        }
    }

    protected override bool ShowWithoutActivation { get { return true; } }

    // stay hidden when Application.Run starts the form
    protected override void SetVisibleCore(bool value)
    {
        if (!allowShow)
        {
            value = false;
            if (!IsHandleCreated) CreateHandle();
        }
        base.SetVisibleCore(value);
    }

    protected override void OnHandleCreated(EventArgs e)
    {
        base.OnHandleCreated(e);
        HotkeyOk = RegisterHotKey(Handle, 1, MOD_NOREPEAT, VK_F24);
    }

    protected override void OnFormClosed(FormClosedEventArgs e)
    {
        UnregisterHotKey(Handle, 1);
        base.OnFormClosed(e);
    }

    protected override void WndProc(ref Message m)
    {
        if (m.Msg == WM_HOTKEY) Toggle();
        base.WndProc(ref m);
    }

    void Toggle()
    {
        if (Visible) { Hide(); return; }
        if (!File.Exists(path)) return;

        Image img;
        using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
        using (var tmp = Image.FromStream(fs))
            img = new Bitmap(tmp);
        if (pic.Image != null) pic.Image.Dispose();
        pic.Image = img;

        var area = Screen.FromPoint(Cursor.Position).WorkingArea;
        double k = Math.Min(1.0, Math.Min(area.Width * 0.95 / img.Width, area.Height * 0.90 / img.Height));
        Width = (int)(img.Width * k);
        Height = (int)(img.Height * k);
        Left = area.Left + (area.Width - Width) / 2;
        Top = area.Top + (area.Height - Height) / 2;

        allowShow = true;
        Show();
    }
}
'@

# one instance only
$created = $false
$mutex = New-Object System.Threading.Mutex($true, 'Global\CorneLayoutOverlay', [ref]$created)
if (-not $created) { exit }

$form = New-Object LayoutOverlay $png
$null = $form.Handle
if (-not $form.HotkeyOk) {
    [System.Windows.Forms.MessageBox]::Show('Az F24 gyorsbillentyűt már egy másik program használja.', 'Corne layout') | Out-Null
    exit 1
}
[System.Windows.Forms.Application]::Run($form)
