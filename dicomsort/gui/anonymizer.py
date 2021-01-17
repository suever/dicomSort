import wx

from dicomsort.gui import widgets


class AnonymizeList(widgets.CheckListCtrl):

    def __init__(self, *args, **kwargs):
        super(AnonymizeList, self).__init__(*args, **kwargs)

        # Insert the two columns (omits the first column as that is the checkbox)
        self.InsertColumn(1, 'DICOM Property', width=200)
        self.InsertColumn(2, 'Replacement Value')

        # Automatically size the column
        self.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)

        # Make the replacement values editable
        self.SetColumnEditable(2)

    def GetReplacementDict(self):
        res = dict()

        x = [i for i in range(self.ItemCount) if len(self.GetStringItem(i, 1))]

        for row in x:
            res[self.GetStringItem(row, 0)] = self.GetStringItem(row, 1)

        return res

    def GetAnonDict(self):

        anonDict = dict()

        for key, val in self.GetCheckedStrings():
            anonDict[key] = val

        return anonDict

    def SetReplacementDict(self, dictionary):
        print(dictionary)
        keys = list(dictionary.keys())
        inds = self.FindStrings(keys, 1)

        for i, row in enumerate(inds):
            if row is None:
                continue

            self.SetItem(row, 2, dictionary[keys[i]])

    def CheckStrings(self, strings, col=0):
        inds = [ind for ind in self.FindStrings(strings, col)
                if ind is not None]
        self.CheckItems(inds)

    def GetDicomField(self, row):
        return self.GetItem(row, 1).Text
