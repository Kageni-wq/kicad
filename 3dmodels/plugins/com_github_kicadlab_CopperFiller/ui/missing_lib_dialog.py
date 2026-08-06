import wx

FRAME_WIDTH = 550
FRAME_HEIGHT = 350

class MissingLibsDialog(wx.Dialog):
    def __init__(self, parent=None):
        width, height = wx.GetDisplaySize()
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title=u"Libraries are not found!",
                           pos=wx.DefaultPosition, 
                           size=wx.Size(FRAME_WIDTH*max(1, width//1920), FRAME_HEIGHT*max(1, height//1080)), 
                           style=wx.DEFAULT_DIALOG_STYLE)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        bSizer1 = wx.BoxSizer(wx.VERTICAL)

        self.staticText = wx.StaticText(
            self, wx.ID_ANY, f"Some python library not found!\n\nPlease follow the installation guide at the link below. Until you finish the installation no CopperFiller functions will be available. After finishing the installation, please restart KiCAD.", wx.DefaultPosition, wx.DefaultSize, 0)
        self.staticText.Wrap(-1)

        bSizer1.Add(self.staticText, 1, wx.ALL | wx.EXPAND, 5)

        self.hyperlink = wx.adv.HyperlinkCtrl(self, wx.ID_ANY, u"https://github.com/kicadlab/CopperFiller",
                                              u"https://github.com/kicadlab/CopperFiller", wx.DefaultPosition, wx.DefaultSize, wx.adv.HL_ALIGN_CENTRE | wx.adv.HL_DEFAULT_STYLE)
        bSizer1.Add(self.hyperlink, 0, wx.ALL | wx.EXPAND, 5)

        self.okButton = wx.Button(
            self, wx.ID_ANY, u"OK", wx.DefaultPosition, wx.DefaultSize, 0)
        bSizer1.Add(self.okButton, 0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(bSizer1)
        self.Layout()

        self.Centre(wx.BOTH)

        self.okButton.Bind(wx.EVT_BUTTON, self.OnOK)

    def OnOK(self, event):
        if self.IsModal():
            self.EndModal(0)
        else:
            self.Close(True)