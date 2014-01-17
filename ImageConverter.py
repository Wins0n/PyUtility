#!/usr/bin/env python
# -*- coding:utf-8 -*-

import wx
import os
import time
import Image
import datetime
import threading
import wx.lib.agw.hyperlink as wxHL

class IcRsrc(object):
    """所有的字符串以及数据参数都集中放在这里，方便修改以及设置多语言"""
    majorVersion = 1
    minorVersion = 0
    winSize = (680, 420)
    sbFields = [-1, -3, -1, -1, -1, -3]
    sbText = {0:u"转换进度", 2:u"已用时间", 3:"00:00:00", 4:u"作者主页"}
    sbBlog = "http://www.programlife.net/"
    winTitle = "Image Converter"
    listHeader = {0:u"文件路径", 1:u"状态"}
    listHeaderWidth = {0:0.8*winSize[0], 1:0.1*winSize[0]}
    menuItemLabel = [u"添加图片文件", u"设置输出路径", "", 
                     u"清空已选文件", "", u"设置图片格式", 
                     "", u"开始转换", u"停止转换", "", u"退出程序"]
    menuItemId = [wx.NewId(), wx.NewId(), None, wx.NewId(), None, wx.NewId(), 
                  None, wx.NewId(), wx.NewId(), None, wx.NewId()]
    fmtDlgTitle = u"设置目标图片格式"
    fmtDlgText = u"请填写图片扩展名(如BMP), 所有文件将被转换为该格式"
    openDlgTitle = u"添加要转换的图片文件"
    openDlgFmt = "BMP (*.bmp;*.dib)|*.bmp;*.dib|" \
                 "JPEG (*.jpg;*.jpeg)|*.jpg;*.jpeg|" \
                 "GIF (*.gif)|*.gif|" \
                 "PNG (*.png)|*.png|" \
                 "All files (*.*)|*.*"
    saveDlgTitle = u"设置输出目录"
    lsWaiting = u"="
    lsSuccess = u"√"
    lsFail = u"X"
    stopScanTitle = u"操作确认"
    stopScanContent = u"正在添加要转换的图片文件，确定要退出吗？"
    stopConvertTitle = u"操作确认"
    stopConvertContent = u"正在转换已添加的图片文件，确定要退出吗？"
    
    @classmethod
    def getTitle(cls):
        return "%s %d.%d" % (cls.winTitle, cls.majorVersion, cls.minorVersion)
    
class IcStatusBar(wx.StatusBar):
    """继承自StatusBar的状态栏，因为上面要放置控件，所以需要自定义"""
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, -1)
        self.SetFieldsCount(len(IcRsrc.sbFields))
        self.SetStatusWidths(IcRsrc.sbFields)
        
        self.createFields()
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Reposition()
        
    def createFields(self):
        for k, v in IcRsrc.sbText.items():
            self.SetStatusText(v, k)
        self.gauge = wx.Gauge(self, -1, 100)
        self.blog = wxHL.HyperLinkCtrl(self, -1, IcRsrc.sbBlog, 
                                       URL=IcRsrc.sbBlog)
        
    def OnSize(self, event):
        event.Skip()
        self.Reposition()
        
    def Reposition(self):
        """为了防止状态栏中的控件摆放错乱，需要设置好各自的位置以及大小"""
        for k, v in {1:self.gauge, 5:self.blog}.items():
            rect = self.GetFieldRect(k)
            rect.x += 1
            rect.y += 1
            rect.width -= 1
            rect.height -= 1
            v.SetRect(rect)
        
class IcFrame(wx.Frame):
    """自定义的Frame框架"""
    def __init__(self):
        wx.Frame.__init__(self, None, -1, IcRsrc.getTitle(),
            size=IcRsrc.winSize,
            style=wx.DEFAULT_FRAME_STYLE ^ 
                  wx.MAXIMIZE_BOX ^ wx.RESIZE_BORDER)
        self.createControls()
        self.createStatusBar()
        self.initValues()
        
    def createControls(self):
        """通过BoxSizer进行界面布局"""
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.fileList = wx.ListCtrl(self, -1, 
                                    style=wx.LC_REPORT | wx.LC_SINGLE_SEL |
                                          wx.LC_HRULES | wx.LC_VRULES)
        for k, v in IcRsrc.listHeader.items():
            self.fileList.InsertColumn(k, v)
            self.fileList.SetColumnWidth(k, IcRsrc.listHeaderWidth[k])
        self.fileList.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.mainSizer.Add(self.fileList, 1, wx.EXPAND | wx.ALL)
        self.SetSizer(self.mainSizer)
        self.Layout()
        
    def createStatusBar(self):
        self.statusbar = IcStatusBar(self)
        self.SetStatusBar(self.statusbar)
        
    def initValues(self):
        self.format = "jpg"
        self.output_dir = ""
        self.source = []
        self.scanning = False
        self.converting = False
        self.hasMenu = False
        
    def OnContextMenu(self, event):
        """弹出右键菜单"""
        if not self.hasMenu:
            self.hasMenu = True
            evtHandler= [self.OnAddSrcFiles, self.OnSelectOutputDir,
                         None, self.OnClearSelect, None, self.OnSetImageFormat,
                         None, self.OnStartConvert, self.OnStopConvert, 
                         None, self.OnExitApp]
            for id, handler in zip(IcRsrc.menuItemId, evtHandler):
                if id != None:
                    self.Bind(wx.EVT_MENU, handler, id=id)
                    self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI, id=id)
            self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self.OnMenuHighlight)
            
            self.menu = wx.Menu()
            for id, label in zip(IcRsrc.menuItemId, IcRsrc.menuItemLabel):
                if id != None:
                    self.menu.Append(id, label)
                else:
                    self.menu.AppendSeparator()
        self.PopupMenu(self.menu)
        
    def OnUpdateUI(self, event):
        """弹出菜单时检查状态，设置各个菜单项是否激活"""
        status = []
        if self.scanning:
            status = [False, True, None, False, None, True, 
                      None, False, False, None, True]
        elif self.converting:
            status = [False, False, None, False, None, False, 
                      None, False, True, None, True]
        else:
            status = [True, True, None, True, None, True, 
                      None, True, False, None, True]
        
        for id, s in zip(IcRsrc.menuItemId, status):
            if id != None:
                self.menu.Enable(id, s)
        
    def OnAddSrcFiles(self, event):
        """添加要转换的图片文件"""
        dlg = wx.FileDialog(self, message=IcRsrc.openDlgTitle,
                            defaultDir=os.getcwd(), defaultFile="",
                            wildcard=IcRsrc.openDlgFmt,
                            style=wx.OPEN | wx.MULTIPLE | wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            self.source.extend(paths)
            self.scanthread = ScanThread(self, paths)
            self.scanthread.start()
        dlg.Destroy()
        
    def OnSelectOutputDir(self, event):
        """设置转换后的图片文件的存放路径"""
        dlg = wx.DirDialog(self, IcRsrc.saveDlgTitle,
                           style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.output_dir = dlg.GetPath()
        dlg.Destroy()
        
    def OnClearSelect(self, event):
        """清空已经添加的图片文件"""
        self.fileList.DeleteAllItems()
        self.source = []
        
    def OnSetImageFormat(self, event):
        """设置转换后的图片文件格式，Image模块可以根据扩展名自动识别最终的图片格式"""
        dlg = wx.TextEntryDialog(self, IcRsrc.fmtDlgText, IcRsrc.fmtDlgTitle)
        while dlg.ShowModal() == wx.ID_OK:
            self.format = dlg.GetValue()
            if len(self.format) == 0:
                continue
            break
        dlg.Destroy()
        
    def OnStartConvert(self, event):
        """开始转换图片文件，通过ConvertThread线程控制"""
        self.convertthread = ConvertThread(self, self.source)
        self.convertthread.start()
        
    def OnStopConvert(self, event):
        """停止转换"""
        if self.converting:
            self.convertthread.stop()
            self.statusbar.gauge.SetValue(0)
        
    def OnExitApp(self, event):
        """退出程序，在退出之前做适当的清理工作"""
        if self.scanning:
            dlg = wx.MessageDialog(self, IcRsrc.stopScanTitle, 
                                   IcRsrc.stopScanContent,
                                   wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_OK:
                self.scanthread.stop()
            dlg.Destroy()
                
        if self.converting:
            dlg = wx.MessageDialog(self, IcRsrc.stopConvertTitle, 
                                   IcRsrc.stopConvertContent,
                                   wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_OK:
                self.convertthread.stop()
            dlg.Destroy()
            
        self.Close(True)
        
    def OnMenuHighlight(self, event):
        """禁止菜单项的帮主字符串(helpString)出现在状态栏的第一个Field之中"""
        pass
    
class ScanThread(threading.Thread):
    """扫描线程，负责将待转换的图片路径添加到UI界面，防止数据量过大时假死"""
    def __init__(self, frame, paths):
        threading.Thread.__init__(self)
        self.thread_stop = False
        self.paths = paths
        self.frame = frame
        
    def run(self):
        self.frame.scanning = True
        for path in self.paths:
            if self.thread_stop:
                break
            count = self.frame.fileList.GetItemCount()
            index = self.frame.fileList.InsertStringItem(count, path)
            self.frame.fileList.SetStringItem(index, 1, IcRsrc.lsWaiting)
        self.frame.scanning = False
        
    def stop(self):
        self.thread_stop = True
        
class ConvertThread(threading.Thread):
    """转换线程，负责图片的格式转换工作"""
    def __init__(self, frame, paths):
        threading.Thread.__init__(self)
        self.thread_stop = False
        self.paths = paths
        self.frame = frame
        
    def run(self):
        self.frame.converting = True
        self.frame.statusbar.gauge.SetValue(0)
        dirname = os.path.normpath(self.frame.output_dir)
        convertres = ""
        count = len(self.paths)-1
        curimg = 0
        starttime = datetime.datetime.now()
        
        for path in self.paths:
            if self.thread_stop:
                break
            filename = os.path.basename(path)
            filename = filename[:filename.rfind(".")] + "." + self.frame.format
            filepath = os.path.join(dirname, filename)
            try:
                # 图片格式转换只需要这一句代码即可
                Image.open(path).save(filepath)
                convertres = IcRsrc.lsSuccess
            except Exception, e:
                print e
                convertres = IcRsrc.lsFail
            self.frame.fileList.SetStringItem(curimg, 1, convertres)
            self.frame.statusbar.gauge.SetValue(curimg*100.0/count)
            # 设置ListCtrl当前行为选中状态
            self.frame.fileList.SetItemState(curimg, wx.LIST_STATE_SELECTED,
                                             wx.LIST_STATE_SELECTED)
            # 让ListCtrl自动滚动
            self.frame.fileList.EnsureVisible(curimg)
            curimg += 1
            interval = (datetime.datetime.now() - starttime).seconds
            self.frame.statusbar.SetStatusText(sec2str(interval), 3)
            time.sleep(0.01)
        self.frame.converting = False
        
    def stop(self):
        self.thread_stop = True
    
class IcApp(wx.App):
    """App类"""
    def OnInit(self):
        frame = IcFrame()
        frame.Show()
        frame.Center()
        self.SetTopWindow(frame)
        return True
    
def sec2str(sec):
    """将秒数转换为格式化字符串"""
    h = sec / 3600
    m = (sec % 3600) / 60
    s = sec % 3600 % 60
    return "%02d:%02d:%02d" % (h, m, s)
    
def Main():
    """Main函数"""
    app = IcApp()
    app.MainLoop()
    
if __name__ == "__main__":
    Main()
    