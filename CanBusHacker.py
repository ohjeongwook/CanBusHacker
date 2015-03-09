from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtSql import *
import time
import os
import re
import sys
import time
import random
import sqlite3
import pprint

import serial
if os.name == 'nt': #sys.platform == 'win32':
	from serial.tools.list_ports_windows import *
elif os.name == 'posix':
	from serial.tools.list_ports_posix import *	

class CanLogReader(QThread):
	canMessageSignal=Signal(list)
	EmulationMode=False
	def __init__(self,log_db,emulation_mode=False):
		QThread.__init__(self)
		self.EmulationMode=emulation_mode
		
	def run(self):
		Conn = sqlite3.connect(log_db)
		Cursor = Conn.cursor()
	
		last_packet_time=0
		for (packet_time,packet_id,payload) in Cursor.execute('SELECT Time,PacketID,Payload FROM Packets ORDER BY ID ASC'):
			self.canMessageSignal.emit((packet_time,packet_id,payload))
			
			if self.EmulationMode:
				time_interval=packet_time-last_packet_time
				if last_packet_time!=0:
					time.sleep(time_interval)
				last_packet_time=packet_time
				
class CanPacketReader(QThread):
	canMessageSignal=Signal(list)
	def __init__(self,com,log_db=''):
		QThread.__init__(self)
		self.COM=com
		self.LogDB=log_db
		
	def run(self):
		try:
			Serial=serial.Serial(self.COM, baudrate=9600)
		except:
			import traceback
			traceback.print_exc()
			Serial=None			

		if self.LogDB:
			if Serial is not None:
				Conn = sqlite3.connect(self.LogDB)
				Cursor = Conn.cursor()
				
				try:
					Cursor.execute('''CREATE TABLE Packets(ID INTEGER PRIMARY KEY, Time DATETIME, PacketID INTEGER, Payload VARCHAR(15))''')
				except:
					pass
			
		CANMessagePattern=re.compile('CAN Message: \[(.*)\] ([^ ]+) ([^\r\n]+)')	
		while Serial is not None:
			message=Serial.readline()
			m=CANMessagePattern.match(message)
			if m!=None:
				current_time=time.time()

				id=m.group(1)
				length=int(m.group(2))
				bytes=m.group(3)[0:length*3]

				if self.LogDB:
					Cursor.execute('''INSERT INTO Packets(Time, PacketID, Payload) VALUES(?,?,?)''', (current_time, id, bytes))
					Conn.commit()
					
				self.canMessageSignal.emit((current_time,id,bytes))
	
class PacketTable(QAbstractTableModel):
	def __init__(self,parent, *args):
		QAbstractTableModel.__init__(self,parent,*args)
		self.PacketList=[]
		self.BufferedPacketList=[]
		self.LastIndex=None
		self.LastDataChangedEmitTime=time.time()
		
	def rowCount(self,parent):
		return len(self.PacketList)
	
	def columnCount(self,parent):
		return 3

	def data(self,index,role):
		if not index.isValid():
			return None
		elif role!=Qt.DisplayRole:
			return None

		self.LastIndex=index
		return str(self.PacketList[index.row()][index.column()])

	def headerData(self,col,orientation,role):
		if orientation==Qt.Horizontal and role==Qt.DisplayRole:
			return ["Time","Id","Payload"][col]
		return None	
	
	def addPacket(self,packet):
		self.BufferedPacketList.append(packet)
				
		cur_time=time.time()
		
		if cur_time-self.LastDataChangedEmitTime>0.1:
			start_row=len(self.PacketList)
			end_row=start_row+len(self.BufferedPacketList)-1
			
			self.beginInsertRows(QModelIndex(), start_row, end_row)
			self.PacketList.extend(self.BufferedPacketList)
			self.endInsertRows()
		
			self.dataChanged.emit(start_row,end_row)
			self.LastDataChangedEmitTime=cur_time
			self.BufferedPacketList=[]
			
	def addPackets(self,packets):
		self.beginRemoveRows(QModelIndex(), 0, len(self.PacketList)-1)
		self.PacketList=[]
		self.endRemoveRows()
	
		start_row=0
		end_row=start_row+len(packets)-1
		self.beginInsertRows(QModelIndex(), start_row, end_row)
		self.PacketList=packets
		self.endInsertRows()
	
		self.dataChanged.emit(start_row,end_row)
			
class TreeItem(object):
	def __init__(self,data,parent=None,assoc_data=None):
		self.parentItem=parent
		self.itemData=data
		self.childItems=[]
		self.assocData=assoc_data
		
	def appendChild(self,item):
		self.childItems.append(item)
		
	def child(self,row):
		return self.childItems[row]
		
	def childCount(self):
		return len(self.childItems)
		
	def children(self):
		return self.childItems
		
	def columnCount(self):
		return len(self.itemData)
	
	def data(self,column):
		try:
			return self.itemData[column]
		except:
			import traceback
			traceback.print_exc()
			
	def parent(self):
		return self.parentItem
		
	def row(self):
		if self.parentItem:
			return parentItem.childItems.index(self)
			
		return 0
		
	def setAssocData(self,data):
		self.assocData=data
		
	def getAssocData(self):
		return self.assocData
		
class TreeModel(QAbstractItemModel):
	def __init__(self,root_item,parent=None):
		super(TreeModel,self).__init__(parent)
		self.rootItem=TreeItem(root_item)
		self.ID2Item={}
		self.BufferedMap={}
		self.LastDataChangedEmitTime=time.time()
		
	def columnCount(self,parent):
		if parent.isValid():
			return parent.internalPointer().columnCount()
		else:
			return self.rootItem.columnCount()
		
	def rowCount(self,parent):
		if parent.column()>0:
			return 0
			
		if not parent.isValid():
			parentItem=self.rootItem
		else:
			parentItem=parent.internalPointer()
			
		return parentItem.childCount()
		
	def data(self,index,role):
		if not index.isValid():
			return None
			
		if role==Qt.DisplayRole:
			item=index.internalPointer()
			return item.data(index.column())
			
		return None
		
	def flags(self,index):
		if not index.isValid():
			return Qt.NoItemFlags
			
		return Qt.ItemIsEnabled|Qt.ItemIsSelectable
	
	def index(self,row,column,parent):
		if not self.hasIndex(row,column,parent):
			return QModelIndex()
			
		if not parent.isValid():
			parentItem=self.rootItem
		else:
			parentItem=parent.internalPointer()
			
		childItem=parentItem.child(row)
		if childItem:
			return self.createIndex(row,column,childItem)
		else:
			return QModelIndex()
			
	def parent(self,index):
		if not index.isValid():
			return QModelindex()
			
		childItem=index.internalPointer()
		parentItem=childItem.parent()
		
		if parentItem is not None:
			if parentItem==self.rootItem:
					return QModelIndex()
					
			return self.createIndex(parentItem.row(),0,parentItem)
		return QModelIndex()
		
	def headerData(self,section,orientation,role):
		if orientation==Qt.Horizontal and role==Qt.DisplayRole:
			return self.rootItem.data(section)
			
		return None
		
	def addIDData(self,id,count):
		self.BufferedMap[id]=count
			
		cur_time=time.time()
		if cur_time-self.LastDataChangedEmitTime>0.1:
			start_row=0
			end_row=0
			for (id,count) in self.BufferedMap.items():
				insert_row=0
				if self.ID2Item.has_key(id):
					tree_item=self.ID2Item[id]
					tree_item.itemData[1]="%d" % count
				else:
					self.beginInsertRows(QModelIndex(), start_row, end_row)
					tree_item=TreeItem([str(id),"%d" % count],assoc_data=id)
					self.ID2Item[id]=tree_item
					self.rootItem.appendChild(tree_item)			
					self.endInsertRows()
					start_row=end_row
					end_row+=1
			self.dataChanged.emit(start_row,end_row)
			self.LastDataChangedEmitTime=cur_time
			self.BufferedMap={}
	
	def getAssocData(self,index):
		if not index.isValid():
			return None
		item=index.internalPointer()
		return item.getAssocData()
		
class StartCaptureDlg(QDialog):
	def __init__(self,parent=None,default_log_db=''):
		super(StartCaptureDlg,self).__init__(parent)
		self.setWindowTitle("Start Capture")

		self.Index2Port={}
		self.comboBox=QComboBox(self)
		i=0
		for port, desc, hwid in comports():
			name= '%s - %s' % (port,desc)
			self.comboBox.addItem(name)
			if os.name == 'nt':
				self.Index2Port[i]='\\\\.\\'+port
			else:
				self.Index2Port[i]=port
			i+=1

		log_db_button=QPushButton('Output Log:',self)
		log_db_button.clicked.connect(self.askLogDB)		
		self.log_db_line=QLineEdit("")
		self.log_db_line.setAlignment(Qt.AlignLeft)
		self.log_db_line.setMinimumWidth(250)
		self.log_db_line.setText(default_log_db)
		
		buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		buttonBox.accepted.connect(self.accept)
		buttonBox.rejected.connect(self.reject)
		
		main_layout=QGridLayout()
		main_layout.addWidget(self.comboBox,0,0,1,2)
		main_layout.addWidget(log_db_button,1,0)
		main_layout.addWidget(self.log_db_line,1,1)		
		main_layout.addWidget(buttonBox,2,0,1,2,Qt.AlignCenter)

		self.setLayout(main_layout)
		
	def askLogDB(self):
		log_db=QFileDialog.getSaveFileName(self,'Save File',
												"",
												'DB (*.db *.*)')[0]	
		self.log_db_line.setText(log_db)
												
	def getLogDB(self):
		return self.log_db_line.text()
		
	def getCOMPort(self):
		return self.Index2Port[self.comboBox.currentIndex()]
		
		
class MainWindow(QMainWindow):
	DebugPacketLoad=0
	def __init__(self,com='',log_db='',emulation_mode=False):
		super(MainWindow,self).__init__()
		self.setWindowTitle("CanBusHacker")
		
		self.COM=com
		self.LogDB=log_db
		self.EmulationMode=emulation_mode
		
		vertical_splitter=QSplitter()
		vertical_splitter.setOrientation(Qt.Vertical)
		horizontal_splitter=QSplitter()
		self.idTreeView=QTreeView()
		self.idTreeModel=TreeModel(("ID","Count"))
		self.idTreeView.setModel(self.idTreeModel)
		self.idTreeView.connect(self.idTreeView.selectionModel(),SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.idTreeSelected)
		horizontal_splitter.addWidget(self.idTreeView)
			
		self.PacketTableView=QTableView()
		vheader=QHeaderView(Qt.Orientation.Vertical)
		#vheader.setResizeMode(QHeaderView.ResizeToContents)
		self.PacketTableView.setVerticalHeader(vheader)
		self.PacketTableView.horizontalHeader().setResizeMode(QHeaderView.Stretch)
		self.PacketTableView.setSortingEnabled(True)
		self.PacketTableView.setSelectionBehavior(QAbstractItemView.SelectRows)		
		self.PacketTableModel=PacketTable(self)
		self.PacketTableView.setModel(self.PacketTableModel)
		
		self.CurrentPacketTableView=QTableView()
		vheader=QHeaderView(Qt.Orientation.Vertical)
		self.CurrentPacketTableView.setVerticalHeader(vheader)
		self.CurrentPacketTableView.horizontalHeader().setResizeMode(QHeaderView.Stretch)
		self.CurrentPacketTableView.setSortingEnabled(True)
		self.CurrentPacketTableView.setSelectionBehavior(QAbstractItemView.SelectRows)		
		self.CurrentPacketTableModel=PacketTable(self)
		self.CurrentPacketTableView.setModel(self.CurrentPacketTableModel)		

		self.rightTabWidget=QTabWidget()
		self.rightTabWidget.addTab(self.PacketTableView,"All Packets")
		self.rightTabWidget.addTab(self.CurrentPacketTableView,"Current Packets")
		horizontal_splitter.addWidget(self.rightTabWidget)		
		horizontal_splitter.setStretchFactor(0,0)
		horizontal_splitter.setStretchFactor(1,1)

		vertical_splitter.addWidget(horizontal_splitter)
		self.logWidget=QTextEdit()
		vertical_splitter.addWidget(self.logWidget)
		vertical_splitter.setStretchFactor(0,1)
		vertical_splitter.setStretchFactor(1,0)		
		
		if self.DebugPacketLoad>0:
			Conn = sqlite3.connect(log_db)
			Cursor = Conn.cursor()
		
			for (time,packet_id,payload) in Cursor.execute('SELECT Time,PacketID,Payload FROM Packets ORDER BY ID ASC'):
				self.PacketTableModel.addPacket((time,packet_id,payload))	
			self.PacketTableView.setModel(self.PacketTableModel)
			
		main_widget=QWidget()
		vlayout=QVBoxLayout()
		vlayout.addWidget(vertical_splitter)
		main_widget.setLayout(vlayout)
		self.setCentralWidget(main_widget)
		
		self.createMenus()
		
		self.show()
		
		self.IDCountMap={}
		self.ID2Packets={}
		self.TimeMap={}

	def openLog(self):
		self.LogDB=QFileDialog.getOpenFileName(self,
												"Open Log DB",
												"",
												"DB Files (*.db)|All Files (*.*)")[0]
		if self.LogDB:
			self.can_log_reader=CanLogReader(self.LogDB,self.EmulationMode)
			self.can_log_reader.canMessageSignal.connect(self.getCanMessage)
			self.can_log_reader.start()
			
	def startCapture(self):
		start_capture_dlg=StartCaptureDlg(default_log_db="log.db")
		if start_capture_dlg.exec_():
			self.COM=start_capture_dlg.getCOMPort()
			log_db=start_capture_dlg.getLogDB()
			if self.COM:
				self.can_packet_reader=CanPacketReader(self.COM,log_db)
				self.can_packet_reader.canMessageSignal.connect(self.getCanMessage)
				self.can_packet_reader.start()
		
	def stopCapture(self):
		pass
		
	def createMenus(self):
		self.fileMenu=self.menuBar().addMenu("&File")
		self.openAct=QAction("&Open Log...",
									self,
									triggered=self.openLog)
		self.fileMenu.addAction(self.openAct)

		self.arduinoMenu=self.menuBar().addMenu("&Arduino")
		self.startCaptureAct=QAction("&Start Capture",
									self,
									triggered=self.startCapture)
		self.arduinoMenu.addAction(self.startCaptureAct)		
		self.stopCaptureAct=QAction("&Start Capture",
									self,
									triggered=self.stopCapture)
		self.arduinoMenu.addAction(self.stopCaptureAct)			
		
	def idTreeSelected(self,newSelection,oldSelection):
		for index in newSelection.indexes():
			id=self.idTreeModel.getAssocData(index)
			#pprint.pprint(self.ID2Packets[id])
			self.rightTabWidget.setCurrentIndex(1)
			self.CurrentPacketTableModel.addPackets(self.ID2Packets[id])
			
	def getCanMessage(self,(current_time,id,bytes)):
		self.PacketTableModel.addPacket((current_time,id,bytes))
		self.PacketTableView.scrollToBottom()
		
		if not self.IDCountMap.has_key(id):
			self.IDCountMap[id]=1
		else:
			self.IDCountMap[id]+=1

		if not self.ID2Packets.has_key(id):
			self.ID2Packets[id]=[]
			
		self.ID2Packets[id].append([current_time,id,bytes])
		
		if self.TimeMap.has_key(id):
			elapsed_time=current_time - self.TimeMap[id]
		else:
			elapsed_time=0
		self.TimeMap[id]=current_time
		
		self.idTreeModel.addIDData(id,self.IDCountMap[id])
		
if __name__=='__main__':
	import sys
	
	com='' #TODO:
	log_db=r'SampleLogs\log.db'
	emulation_mode=False
	
	app=QApplication(sys.argv)
	app.processEvents()
	window=MainWindow(com,log_db,emulation_mode)
	window.show()
	sys.exit(app.exec_())