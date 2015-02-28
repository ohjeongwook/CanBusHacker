from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtSql import *
import time
import serial
import time
import os
import re
import sys
import time
import random
import sqlite3

class CanLogReader(QThread):
	canMessageSignal=Signal(list)
	def __init__(self,log_db):
		QThread.__init__(self)
		
	def run(self):
		Conn = sqlite3.connect(log_db)
		Cursor = Conn.cursor()
	
		for (packet_time,packet_id,payload) in Cursor.execute('SELECT Time,PacketID,Payload FROM Packets ORDER BY ID ASC'):
			self.canMessageSignal.emit((packet_time,packet_id,payload))
			time.sleep(0.1)
				
class CanPacketReader(QThread):
	canMessageSignal=Signal(list)
	def __init__(self,com,log_db='CANPackets.db'):
		QThread.__init__(self)
		
	def run(self):
		try:
			Serial=serial.Serial(r'\\.\\'+com, baudrate=9600)
		except:
			import traceback
			traceback.print_exc()
			Serial=None			

		if Serial is not None:
			Conn = sqlite3.connect(log_db)
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

				Cursor.execute('''INSERT INTO Packets(Time, PacketID, Payload) VALUES(?,?,?)''', (current_time, id, bytes))
				Conn.commit()
				
				self.canMessageSignal.emit((current_time,id,bytes))
	
class PacketTable(QAbstractTableModel):
	def __init__(self,parent, *args):
		QAbstractTableModel.__init__(self,parent,*args)
		self.PacketList=[]
		self.LastIndex=None
		
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
		insert_row=len(self.PacketList)
		self.beginInsertRows(QModelIndex(), insert_row, insert_row)
		self.PacketList.append(packet)
		self.endInsertRows()
		self.dataChanged.emit(insert_row,insert_row)
	
class TreeItem(object):
	def __init__(self,data,parent=None):
		self.parentItem=parent
		self.itemData=data
		self.childItems=[]
		
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
		
class TreeModel(QAbstractItemModel):
	def __init__(self,root_item,parent=None):
		super(TreeModel,self).__init__(parent)
		self.rootItem=TreeItem(root_item)
		self.ID2Item={}
		
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
		insert_row=0
		self.beginInsertRows(QModelIndex(), insert_row, insert_row)
		
		if self.ID2Item.has_key(id):
			tree_item=self.ID2Item[id]
			tree_item.itemData[1]="%d" % count
		else:
			tree_item=TreeItem([str(id),"%d" % count])
			self.ID2Item[id]=tree_item
			self.rootItem.appendChild(tree_item)
			
		self.endInsertRows()
		self.dataChanged.emit(insert_row,insert_row)
	
class MainWindow(QMainWindow):
	DebugPacketLoad=0
	def __init__(self,com='',log_db=''):
		super(MainWindow,self).__init__()
		self.setWindowTitle("CanBusHacker")
		
		vertical_splitter=QSplitter()
		vertical_splitter.setOrientation(Qt.Vertical)
		horizontal_splitter=QSplitter()
		self.idTreeView=QTreeView()
		self.idTreeModel=TreeModel(("ID","Count"))
		self.idTreeView.setModel(self.idTreeModel)
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

		horizontal_splitter.addWidget(self.PacketTableView)		
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
		self.show()
			
		if com:
			self.can_packet_reader=CanPacketReader(com,log_db)
			self.can_packet_reader.canMessageSignal.connect(self.getCanMessage)
			self.can_packet_reader.start()
		elif log_db:
			self.can_log_reader=CanLogReader(log_db)
			self.can_log_reader.canMessageSignal.connect(self.getCanMessage)
			self.can_log_reader.start()		
		
		self.IDCountMap={}
		self.LastPayloadMap={}
		self.TimeMap={}

	def getCanMessage(self,(current_time,id,bytes)):
		self.PacketTableModel.addPacket((current_time,id,bytes))
		self.PacketTableView.scrollToBottom()
		
		if not self.IDCountMap.has_key(id):
			self.IDCountMap[id]=1
		else:
			self.IDCountMap[id]+=1

		self.LastPayloadMap[id]=bytes
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
	app=QApplication(sys.argv)
	app.processEvents()
	window=MainWindow(com,log_db)
	window.show()
	sys.exit(app.exec_())