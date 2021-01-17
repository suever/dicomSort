import os
import re
import six
import wx

import wx.grid
import wx.html

from wx.lib.mixins.listctrl import CheckListCtrlMixin, TextEditMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

from dicomsort.gui import errors, events
from dicomsort.gui.dialogs import SeriesRemoveWarningDlg


class FileDropTarget(wx.FileDropTarget):
    def __init__(self, callback):
        super(FileDropTarget, self).__init__()
        self.callback = callback

    def OnDropFiles(self, x, y, filenames):
        self.callback(x, y, filenames)


class CustomDataTable(wx.grid.PyGridTableBase):
    def __init__(self, data):
        super(CustomDataTable, self).__init__()

        self.colLabels = ['', 'DICOM Property', 'Replacement Value']

        self.dataTypes = [
            wx.grid.GRID_VALUE_BOOL,
            wx.grid.GRID_VALUE_STRING,
            wx.grid.GRID_VALUE_STRING
        ]

        if data is None:
            data = [['', '', ''], ]

        self.data = data

    # --------------------------------------------------
    # required methods for the wxPyGridTableBase interface

    def GetNumberRows(self):
        return len(self.data)

    def GetNumberCols(self):
        return len(self.data[0])

    def IsEmptyCell(self, row, col):
        try:
            return not self.data[row][col]
        except IndexError:
            return True

    # Get/Set values in the table.  The Python version of these
    # methods can handle any data-type, (as long as the Editor and
    # Renderer understands the type too,) not just strings as in the
    # C++ version.
    def GetValue(self, row, col):
        try:
            return self.data[row][col]
        except IndexError:
            return ''

    def SetValue(self, row, col, value):
        def innerSetValue(row, col, value):
            try:
                self.data[row][col] = value
            except IndexError:
                # add a new row
                self.data.append([''] * self.GetNumberCols())
                innerSetValue(row, col, value)

                # tell the grid we've added a row
                msg = wx.grid.GridTableMessage(
                    self,
                    wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED,
                    1
                )

                view = self.GetView()

                if view:
                    view.ProcessTableMessage(msg)
        innerSetValue(row, col, value)

    # --------------------------------------------------
    # Some optional methods

    # Called when the grid needs to display labels
    def GetColLabelValue(self, col):
        return self.colLabels[col]

    # Called to determine the kind of editor/renderer to use by
    # default, doesn't necessarily have to be the same type used
    # natively by the editor/renderer if they know how to convert.
    def GetTypeName(self, row, col):
        return self.dataTypes[col]

    # Called to determine how the data can be fetched and stored by the
    # editor and renderer.  This allows you to enforce some type-safety
    # in the grid.
    def CanGetValueAs(self, row, col, typeName):
        colType = self.dataTypes[col].split(':')[0]
        if typeName == colType:
            return True
        else:
            return False

    def CanSetValueAs(self, row, col, typeName):
        return self.CanGetValueAs(row, col, typeName)


class CheckListCtrl(wx.ListCtrl, TextEditMixin, ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT)
        ListCtrlAutoWidthMixin.__init__(self)

        TextEditMixin.__init__(self)

        self.EnableCheckBoxes()

        # Keep track of the editable columns
        self.editable_columns = set()

        # Bind the edit event to prevent editing of the first column.
        # Additionally we need this to allow the user to interact with
        # the checkbox because when using the TextEditMixin, any
        # mouse interaction with the checkbox is ignored.
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)

        self.InsertColumn(0, '')

        # TODO: Make the first column fit to the checkbox
        self.SetColumnWidth(0, wx.LIST_AUTOSIZE)

    def OnBeginLabelEdit(self, event):
        if event.GetColumn() == 0:
            item = event.GetIndex()
            # Toggle the checkbox
            self.CheckItem(item, check=(not self.IsItemChecked(item)))
            event.Veto()
            return

        # TODO: Check if this column is disabled?

        event.Skip()

    def SetColumnEditable(self, column, edit=True):
        if edit:
            self.editable_columns.add(column)
        else:
            self.editable_columns.remove(column)

    def ClearColumn(self, column):
        for row in range(self.ItemCount):
            self.SetItem(row, column, '')

    def SetStringItems(self, items):
        self.DeleteAllItems()

        for item in items:
            if isinstance(item, str):
                item = [item, ]

            # Insert an empty item which is the checkbox column
            row = self.InsertItem(self.GetItemCount() + 1, '')

            for column, value in enumerate(item):
                self.SetItem(row, column + 1, value)

    def CheckItems(self, rows, check=True):
        for row in rows:
            self.CheckItem(row, check)

    def GetCheckedItems(self, column=None):
        return [self.GetItemList(column) for row in self._GetCheckedRows()]

    def _GetCheckedRows(self):
        return [row for row in range(self.ItemCount) if self.IsItemChecked(row)]

    def UnCheckAll(self):
        self.CheckItems(range(self.ItemCount), False)

    def GetCheckedStrings(self, column=None):
        return [self.GetStringItem(row, column) for row in self._GetCheckedRows()]

    def FindStrings(self, strings, column=0):
        strings = [six.ensure_text(string) for string in strings]

        fields = [item.Text for item in self.GetItemList(column)]

        indices = []

        for string in strings:
            try:
                indices.append(fields.index(string))
            except ValueError:
                indices.append(None)

        return indices

    def GetItemList(self, column=None):
        if column is None:
            return [self.GetItemList(column) for column in range(self.ColumnCount)]

        return [self.GetItem(row, column) for row in range(self.ItemCount)]

    def GetStringItem(self, row, column=None):
        if column is None:
            return [self.GetStringItem(row, column) for column in range(self.ColumnCount)]

        return self.GetItem(row, column).Text

    '''
    def OpenEditor(self, column, row):
        if column not in self.editable_columns:
            return

        return TextEditMixin.OpenEditor(self, column, row)
    '''






class CheckListCtrlOld(wx.ListCtrl, ListCtrlAutoWidthMixin,
                    CheckListCtrlMixin, TextEditMixin):

    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT)
        ListCtrlAutoWidthMixin.__init__(self)

        # The order here matter because we favor Check over Edit
        TextEditMixin.__init__(self)
        CheckListCtrlMixin.__init__(self)

        self.editColumns = []

    def _GetCheckedIndexes(self):
        return [i for i in range(self.ItemCount) if self.IsChecked(i)]

    def ClearColumn(self, col):
        [self.SetItem(i, col, '') for i in range(self.ItemCount)]

    def SetColumnEditable(self, column, edit=True):
        if edit:
            if column not in self.editColumns:
                self.editColumns.append(column)
        else:
            if column in self.editColumns:
                self.editColumns.remove(column)

    def SetStringItems(self, items):
        self.DeleteAllItems()

        for item in items:
            if isinstance(item, str):
                item = [item, ]

            row = self.InsertItem(self.GetItemCount() + 1, item[0])

            for col in range(1, len(item)):
                self.SetItem(row, col, item[col])

    def CheckItems(self, itemIndex):
        [self.CheckItem(index) for index in itemIndex]

    def GetCheckedItems(self, col=None):
        return [self.GetItemList(r, col) for r in self._GetCheckedIndexes()]

    def UnCheckAll(self):
        [self.CheckItem(index, False) for index in range(self.ItemCount)]

    def GetCheckedStrings(self, col=None):
        return [self.GetStringItem(r, col) for r in self._GetCheckedIndexes()]

    def FindStrings(self, strings, col=0):
        strings = [six.ensure_text(string) for string in strings]

        fields = [item.Text for item in self.GetItemList(col)]

        inds = list()

        for string in strings:
            try:
                inds.append(fields.index(six.ensure_text(string)))
            except ValueError:
                inds.append(None)

        return inds

    def GetItemList(self, column=None):
        if column is None:
            return [self.GetItemList(c) for c in range(self.ColumnCount)]
        else:
            return [self.GetItem(r, column) for r in range(self.ItemCount)]

    def GetStringItem(self, row, column=None):
        if column is None:
            return [
                self.GetStringItem(row, c) for c in range(self.ColumnCount)
            ]
        else:
            return self.GetItem(row, column).Text

    def OpenEditor(self, column, row):
        """
        Overloaded method to render certain columns un-editable
        """
        if column not in self.editColumns:
            return
        else:
            # Call superclass edit method
            TextEditMixin.OpenEditor(self, column, row)


class PathEditCtrl(wx.Panel):
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        self.create()
        self.path = ''
        self.Bind(wx.EVT_TEXT_ENTER, self.ValidatePath, self.edit)

        dt = FileDropTarget(self.ValidateDropFiles)
        self.edit.SetDropTarget(dt)

    def ValidateDropFiles(self, x, y, filenames):
        self.SetPaths(filenames)

    def ValidatePath(self, *evnt):
        paths = self.edit.GetValue()

        self.SetPaths(paths.split(';'))

    def create(self):
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        opts = wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT | wx.TOP

        self.edit = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)
        hbox.Add(self.edit, 1, opts, 5)

        self.browse = wx.Button(self, -1, label="Browse")
        hbox.Add(self.browse, 0, opts, 10)

        self.browse.Bind(wx.EVT_BUTTON, self.BrowsePaths)

        self.SetSizer(hbox)

    def SetPaths(self, paths):
        if not isinstance(paths, list):
            paths = [paths, ]

        # Determine if there are any invalid paths
        badPaths = [path for path in paths if not os.path.isdir(path)]

        if len(badPaths):
            p = ', '.join(badPaths)
            errorMsg = 'The Following directories are invalid paths: %s' % p
            errors.throw_error(errorMsg, 'Invalid Paths', parent=self.Parent)
            return

        self.path = paths
        self.edit.SetValue(';'.join(paths))

        # Trigger an EVT_PATH event
        self.Notify()

    def Notify(self, *evnt):
        event = events.PathEvent(path=self.path)
        wx.PostEvent(self, event)

    def BrowsePaths(self, *evnt):
        # Open the dialog and search
        if len(self.path):
            defaultPath = self.path[0]
        else:
            defaultPath = ''

        pathDlg = wx.DirDialog(self.GetParent(), "Please Select Directory",
                               defaultPath)
        pathDlg.CenterOnParent()

        if pathDlg.ShowModal() == wx.ID_OK:
            path = pathDlg.GetPath()
            self.SetPaths([path, ])

        pathDlg.Destroy()


class FieldSelector(wx.Panel):

    def __init__(self, parent, id=-1, size=(250, 300), choices=None,
                 titles=None):
        wx.Panel.__init__(self, parent, id=id, size=size)

        self.choices = choices or []
        self.titles = titles or ['', '']

        self.create()

    def Filter(self, string=None):
        if string and isinstance(string, str):
            self.search.SetValue(string)
        else:
            string = self.search.GetValue()

        newVals = [p for p in self.choices if re.search(string, p,
                                                        re.IGNORECASE)]

        self.options.SetItems(newVals)

    def _return_focus(self):
        return

    def _sort_callback(self, *evnt):
        event = events.SortEvent(
            anon=self.anonQ.IsChecked(), fields=self.GetFormatFields()
        )
        wx.PostEvent(self, event)

    def GetSelectedItems(self):
        return self.selected.GetItems()

    def GetFormatFields(self):
        items = self.GetSelectedItems()
        return ['%(' + item + ')s' for item in items]

    def _anon_tick(self, args):
        if self.anonQ.IsChecked():
            self.Parent.QuickRename()

    def create(self):

        self.titleL = wx.StaticText(self, -1, self.titles[0])
        self.options = wx.ListBox(self, -1, choices=self.choices)

        self.search = wx.SearchCtrl(
            self, -1, "", style=wx.TE_PROCESS_ENTER)

        self.titleR = wx.StaticText(self, -1, self.titles[1])
        self.selected = wx.ListBox(self, -1, choices=[])

        self.sortBtn = wx.Button(self, -1, label="Sort Images")
        self.anonQ = wx.CheckBox(self, -1, label="Anonymize Data")

        # Make it so that when we check the checkbox it brings up the quick
        # rename dialog
        self.anonQ.Bind(wx.EVT_CHECKBOX, self._anon_tick)

        self.sortBtn.Bind(wx.EVT_BUTTON, self._sort_callback)

        # Setup double-click callbacks
        self.options.Bind(wx.EVT_LISTBOX_DCLICK, self.SelectItem)
        self.selected.Bind(wx.EVT_LISTBOX_DCLICK, self.DeselectItem)

        # Setup Search Control
        self.search.Bind(wx.EVT_TEXT, self.Filter)
        self.search.Bind(wx.EVT_TEXT_ENTER, self._return_focus)

        # Setup controls:
        self.bAdd = wx.Button(self, -1, label=">>", size=(50, -1))
        self.bRemove = wx.Button(self, -1, label="<<", size=(50, -1))
        self.bUp = wx.Button(self, -1, label="Up", size=(50, -1))
        self.bDown = wx.Button(self, -1, label="Down", size=(50, -1))

        self.bAdd.Bind(wx.EVT_BUTTON, self.SelectItem)
        self.bRemove.Bind(wx.EVT_BUTTON, self.DeselectItem)
        self.bUp.Bind(wx.EVT_BUTTON, self.PromoteSelection)
        self.bDown.Bind(wx.EVT_BUTTON, self.DemoteSelection)

        self._initialize_layout()

    def WidgetList(self):
        a = [self.options, self.search, self.selected,
             self.bAdd, self.bRemove, self.bUp, self.bDown]
        return a

    def DisableAll(self):
        [item.Disable() for item in self.WidgetList()]

    def EnableAll(self):
        [item.Enable(True) for item in self.WidgetList()]

    def _initialize_layout(self):
        # BoxSizer containing the options to select
        vboxOptions = wx.BoxSizer(wx.VERTICAL)

        vboxOptions.Add(self.titleL, 0, wx.ALIGN_CENTER_HORIZONTAL)
        vboxOptions.Add(self.options, 1,
                        wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        vboxOptions.Add(self.search, 0, wx.EXPAND | wx.ALL, 10)

        # BoxSizer containing the selected options
        vboxSelect = wx.BoxSizer(wx.VERTICAL)

        vboxSelect.Add(self.titleR, 0, wx.ALIGN_CENTER_HORIZONTAL)
        vboxSelect.Add(self.selected, 1,
                       wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        vboxSelect.Add(self.anonQ, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        vboxSelect.Add(
            self.sortBtn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)

        # BoxSizer housing the controls
        vboxControl = wx.BoxSizer(wx.VERTICAL)

        vboxControl.Add(self.bAdd, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 30)
        vboxControl.Add(
            self.bRemove, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 15)
        vboxControl.Add(self.bUp, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 15)
        vboxControl.Add(self.bDown, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 15)

        # Horizontal Box that contains all elements
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        hbox.Add(vboxOptions, 1, wx.EXPAND | wx.ALL, 10)
        hbox.Add(vboxControl, 0, wx.ALL, 0)
        hbox.Add(vboxSelect, 1, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(hbox)

    def has_default(self):
        if self.selected.GetCount() == 0:
            return False

        if self.selected.GetItems()[-1] == 'SeriesDescription':
            return True
        else:
            return False

    def PromoteSelection(self, *evnt):
        self._move_selection(-1)

    def DemoteSelection(self, *evnt):
        self._move_selection(1)

    def _move_selection(self, inc):
        """
        Shared method for moving an item around the list.
        There really has to be a better way...
        """

        index = self.selected.GetSelection()

        if index == self.selected.GetCount() - 1 and self.has_default():
            return

        if inc < 0 and (self.selected.Count == 1 or index == 0):
            return
        elif (inc > 0 and index == self.selected.Count - 1):
            return

        prop = self.selected.GetStringSelection()

        self.selected.Delete(index)
        self.selected.Insert(prop, index + inc)
        self.selected.Select(index + inc)

    def SelectItem(self, *evnt):
        item = self.options.GetStringSelection()
        if self.has_default():
            self.selected.Insert(item, self.selected.GetCount() - 1)
        else:
            self.selected.Append(item)

    def DeselectItem(self, *evnt):
        index = self.selected.GetSelection()

        if index == -1:
            return

        if index == self.selected.GetCount() - 1 and self.has_default():
            warn = SeriesRemoveWarningDlg(None)
            warn.ShowModal()

            if warn.choice == 0:
                return
            elif warn.choice == 1:
                # change to original filenames
                cfg = self.GetParent().config
                cfg['FilenameFormat']['Selection'] = 1
                page = self.GetParent().prefDlg.pages['FilenameFormat']
                page.UpdateFromConfig(cfg)

        self.selected.Delete(index)

        self.selected.Select(index - 1)

    def SetTitles(self, titleL, titleR):
        self.leftBox

    def SetOptions(self, optionList=[]):
        # clear
        self.options.SetItems(optionList)
        self.choices = optionList
