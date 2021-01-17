import wx

from dicomsort.gui.widgets import CheckListCtrl
from wx.lib.mixins.listctrl import TextEditMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

class TestListCtrl(wx.ListCtrl, TextEditMixin, ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        TextEditMixin.__init__(self)
        ListCtrlAutoWidthMixin.__init__(self)

        self.EnableCheckBoxes()

        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)

    def OnBeginLabelEdit(self, event):
        if event.GetColumn() == 0:
            item = event.GetIndex()
            self.CheckItem(item, check=(not self.IsItemChecked(item)))
            event.Veto()
            return

        if event.GetColumn() == 1:
            event.Veto()
            return

        event.Skip()

        




app = wx.App(redirect=True, filename="log.txt")
top = wx.Frame(None, title="Hello World", size=(300, 200))

v = TestListCtrl(top, -1, style=wx.LC_REPORT)
v.InsertColumn(0, '')
v.InsertColumn(1, 'Property')
v.InsertColumn(2, 'Value')
ind = v.InsertStringItem(0, '')
v.SetStringItem(ind, 1, 'PatientName')
v.SetStringItem(ind, 2, 'ANONYMOUS')
v.EnableCheckBoxes()
v.SetColumnWidth(0, wx.LIST_AUTOSIZE)
v.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
v.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)

top.Show()
app.MainLoop()
