import wx
import os
import subprocess as sp
import sys

FRAME_WIDTH = 250
FRAME_HEIGHT = 300

class InfoDialog(wx.Dialog):
    def __init__(self, parent=None, total_time=None, shapes=None, clipped=None, log_dir=None):
        width, height = wx.GetDisplaySize()
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title=_("Total Information"),
                           pos=wx.DefaultPosition, 
                           size=wx.Size(FRAME_WIDTH*max(1, width//1920), FRAME_HEIGHT*max(1, height//1080)), 
                           style=wx.DEFAULT_DIALOG_STYLE)

        self.log_dir = log_dir
        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        bSizer1 = wx.BoxSizer(wx.VERTICAL)

        self.staticText = wx.StaticText(
            self, wx.ID_ANY, 
            _("Filler ends!\nTotal time: {total_time:.1f} sec\nCreated shapes: {shapes}\nAdded: {clipped}\n\nDetails in log file.").format(
                total_time=total_time,
                shapes=shapes,
                clipped=clipped), 
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.staticText.Wrap(-1)
        bSizer1.Add(self.staticText, 1, wx.ALL | wx.EXPAND, 5)

        self.okButton = wx.Button(
            self, wx.ID_ANY, u"OK", wx.DefaultPosition, wx.DefaultSize, 0)
        bSizer1.Add(self.okButton, 0, wx.ALL | wx.EXPAND, 5)

        self.logButton = wx.Button(self, wx.ID_ANY, _("Logs"), wx.DefaultPosition, wx.DefaultSize, 0)
        bSizer1.Add(self.logButton, 0, wx.ALL | wx.EXPAND, 5)
        
        self.SetSizer(bSizer1)
        self.Layout()

        self.Centre(wx.BOTH)

        self.okButton.Bind(wx.EVT_BUTTON, self.OnOK)
        self.logButton.Bind(wx.EVT_BUTTON, self.OnLog)

    def OnOK(self, event):
        if self.IsModal():
            self.EndModal(0)
        else:
            self.Close(True)

    def OnLog(self, event):
        if not os.path.exists(self.log_dir):
            wx.MessageBox(_("Not found logs directory"), _("Error"), wx.OK | wx.ICON_ERROR)
            return

        try:
            if sys.platform == 'win32':
                os.startfile(self.log_dir)
            elif sys.platform == 'darwin':
                sp.call(['open', self.log_dir])
            else:
                sp.call(['xdg-open', self.log_dir])
        except Exception as e:
            wx.MessageBox(_("Not open logs directory"), _("Error"), wx.OK | wx.ICON_ERROR)