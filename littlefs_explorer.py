import sys
import os
import shutil
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTreeView, QTextEdit,
                             QMessageBox, QInputDialog, QMenu, QDialog, QPlainTextEdit,
                             QFileSystemModel, QComboBox, QLabel, QScrollArea,
                             QFileDialog) # QFileDialog 추가

from PySide6.QtCore import Qt, QDir, QModelIndex, QFileSystemWatcher, Signal, QSize
from PySide6.QtGui import QAction, QCursor, QIcon

# 기존 스크립트 모듈 임포트
from dump_littlefs import dump_bin_file
from flash_littlefs import download_bin_file
from mklittlefs import extract_files, assemble_files
from gen_esp32part import PartitionTable

class LittleFSTreeView(QTreeView):
    """외부 파일 드래그 앤 드롭을 지원하는 커스텀 트리 뷰"""
    fileDropped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            model = self.model()
            # 드롭된 위치의 인덱스 가져오기 (폴더면 해당 폴더로, 아니면 루트로)
            index = self.indexAt(event.pos())
            target_dir = model.filePath(index) if index.isValid() and os.path.isdir(model.filePath(index)) else model.rootPath()

            for url in event.mimeData().urls():
                src_path = url.toLocalFile()
                dst_path = os.path.join(target_dir, os.path.basename(src_path))

                # 파일이 이미 존재하면 덮어쓸지 묻는 대화 상자 표시
                if os.path.exists(dst_path):
                    reply = QMessageBox.question(self, 'Overwrite File?',
                                                 f"'{os.path.basename(src_path)}'이(가) 이미 존재합니다. 덮어쓰시겠습니까?",
                                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if reply == QMessageBox.No:
                        continue # 덮어쓰지 않으면 다음 파일로 넘어감

                if os.path.isdir(src_path): # 폴더 복사
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True) # dirs_exist_ok=True로 기존 폴더에 병합
                else: # 파일 복사
                    shutil.copy2(src_path, dst_path) # 메타데이터도 함께 복사
            event.acceptProposedAction()
            self.fileDropped.emit()

class TextEditorDialog(QDialog):
    """파일 내용을 조회하고 수정하기 위한 간단한 텍스트 에디터 다이얼로그"""
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(f"Editing: {os.path.basename(file_path)}")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        self.editor = QPlainTextEdit()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())
        except Exception as e:
            self.editor.setPlainText(f"Error reading file: {e}")
            self.editor.setReadOnly(True)
            
        layout.addWidget(self.editor)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def save_and_close(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {e}")

class LittleFSExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ESP32 LittleFS Explorer")
        self.resize(1000, 700)

        # 기본 설정값 (기존 스크립트와 동일)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.bin_file = os.path.join(self.base_dir, "littlefs.bin")
        self.new_bin_file = os.path.join(self.base_dir, "new_littlefs.bin")
        self.extract_folder = os.path.join(self.base_dir, "extracted_data")
        self.img_dir = os.path.join(self.base_dir, "img")
        self.offset = "0x110000"
        self.size = 0x14F000
        self.block_size = 4096

        if not os.path.exists(self.extract_folder):
            os.makedirs(self.extract_folder)

        self.init_ui()

    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} ({port.description})", port.device)
        
        if self.port_combo.count() == 0:
            self.port_combo.addItem("No COM Ports Found", "")
        self.port_combo.setCurrentIndex(0) # 첫 번째 포트 선택

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 0. COM 포트 선택 레이아웃
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Serial Port:"))
        self.port_combo = QComboBox()
        port_layout.addWidget(self.port_combo, 1)
        self.btn_refresh = QPushButton("Refresh")
        # 아이콘 추가
        refresh_icon = os.path.join(self.img_dir, "refresh.png")
        if os.path.exists(refresh_icon):
            self.btn_refresh.setIcon(QIcon(refresh_icon))
            self.btn_refresh.setIconSize(QSize(16, 16))

        self.btn_refresh.setFixedWidth(80) # 버튼 너비 고정
        self.btn_refresh.clicked.connect(self.refresh_ports)
        port_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(port_layout)

        # 0.1 파티션 테이블 표시 영역 (Container & Blocks)
        partition_group = QVBoxLayout()
        partition_group.addWidget(QLabel("ESP32 Partition Layout (from 0x8000):"))
        
        self.btn_load_partition = QPushButton("Load Partition Table from Device")
        # 아이콘 추가
        part_icon = os.path.join(self.img_dir, "load_partition.png")
        if os.path.exists(part_icon):
            self.btn_load_partition.setIcon(QIcon(part_icon))
            self.btn_load_partition.setIconSize(QSize(20, 20))

        self.btn_load_partition.clicked.connect(self.load_partition_table)
        partition_group.addWidget(self.btn_load_partition)

        self.partition_container = QWidget()
        self.partition_layout = QHBoxLayout(self.partition_container)
        self.partition_layout.setContentsMargins(5, 5, 5, 5)
        self.partition_layout.setSpacing(5)
        self.partition_layout.setAlignment(Qt.AlignLeft)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.partition_container)
        scroll_area.setFixedHeight(110)
        partition_group.addWidget(scroll_area)
        main_layout.addLayout(partition_group)

        # 1. 상단 액션 버튼
        btn_layout = QHBoxLayout()
        self.btn_read = QPushButton("Read Selected Partition & Extract")
        # 아이콘 추가
        read_esp_icon = os.path.join(self.img_dir, "read_partition.png")
        if os.path.exists(read_esp_icon):
            self.btn_read.setIcon(QIcon(read_esp_icon))
            self.btn_read.setIconSize(QSize(24, 24))

        self.btn_read.setFixedHeight(40)
        self.btn_read.clicked.connect(self.action_read_and_extract)
        
        self.btn_write = QPushButton("Assemble & Write to Selected Partition")
        # 아이콘 추가
        write_esp_icon = os.path.join(self.img_dir, "write_partition.png")
        if os.path.exists(write_esp_icon):
            self.btn_write.setIcon(QIcon(write_esp_icon))
            self.btn_write.setIconSize(QSize(24, 24))

        self.btn_write.setFixedHeight(40)
        self.btn_write.setStyleSheet("background-color: #d1e7dd; font-weight: bold;")
        self.btn_write.clicked.connect(self.action_assemble_and_flash)

        btn_layout.addWidget(self.btn_read)
        btn_layout.addWidget(self.btn_write)
        main_layout.addLayout(btn_layout)

        # 1.1 바이너리 파일 처리 버튼 (Step 3.3 & 3.4)
        bin_btn_layout = QHBoxLayout()
        self.btn_read_bin = QPushButton("Read from .bin File")
        # 아이콘 추가
        read_bin_icon = os.path.join(self.img_dir, "read_from_bin.png")
        if os.path.exists(read_bin_icon):
            self.btn_read_bin.setIcon(QIcon(read_bin_icon))
            self.btn_read_bin.setIconSize(QSize(20, 20))

        self.btn_read_bin.setFixedHeight(30)
        self.btn_read_bin.clicked.connect(self.action_read_from_bin)

        self.btn_write_bin = QPushButton("Write to .bin File")
        # 아이콘 추가
        write_bin_icon = os.path.join(self.img_dir, "write_to_bin.png")
        if os.path.exists(write_bin_icon):
            self.btn_write_bin.setIcon(QIcon(write_bin_icon))
            self.btn_write_bin.setIconSize(QSize(20, 20))

        self.btn_write_bin.setFixedHeight(30)
        self.btn_write_bin.clicked.connect(self.action_write_to_bin)

        bin_btn_layout.addWidget(self.btn_read_bin)
        bin_btn_layout.addWidget(self.btn_write_bin)
        main_layout.addLayout(bin_btn_layout)

        # 2. 파일 트리 뷰 (Step 3: CRUD)
        self.model = QFileSystemModel()
        self.model.setRootPath(self.extract_folder)
        self.model.setReadOnly(False) # 직접 이름 수정 가능

        self.tree = LittleFSTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.extract_folder))
        self.tree.setColumnWidth(0, 300)
        self.tree.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree.setAnimated(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.doubleClicked.connect(self.open_file_editor)
        self.tree.fileDropped.connect(self.update_usage_status)
        
        main_layout.addWidget(self.tree)

        # 3. 용량 표시 상태바 (Step 3.5)
        self.status_label = QLabel("Usage: 0 / 0 bytes (0.0%)")
        self.status_label.setStyleSheet("padding: 5px; background-color: #f8f9fa; border-top: 1px solid #dee2e6;")
        main_layout.addWidget(self.status_label)

        # 3. 하단 로그 출력창
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(150)
        self.log_view.setStyleSheet("background-color: #f8f9fa; font-family: Consolas;")
        main_layout.addWidget(self.log_view)

        # 4. 파일 시스템 감시자 설정 (자동 리프레시 및 용량 체크용)
        self.watcher = QFileSystemWatcher([self.extract_folder])
        self.watcher.directoryChanged.connect(self.on_extracted_folder_changed)

        self.refresh_ports()
        self.update_usage_status()
        self.log("Explorer Initialized. Work directory: " + self.extract_folder)

    def log(self, message):
        self.log_view.append(f"> {message}")

    # --- ESP32 통신 및 바이너리 처리 ---
    def load_partition_table(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "Warning", "Please select a COM port.")
            return

        self.log("Reading partition table (offset 0x8000)...")
        part_bin = os.path.join(self.base_dir, "partition_table.bin")
        # 파티션 테이블 섹터(0x1000)를 읽어옵니다.
        if dump_bin_file(part_bin, "0x8000", "0x1000", port=port):
            try:
                with open(part_bin, "rb") as f:
                    data = f.read()
                table = PartitionTable.from_binary(data)
                self.update_partition_view(table)
                self.log("Partition table analyzed and displayed.")
            except Exception as e:
                self.log(f"Error parsing partition table: {e}")
        else:
            self.log("Failed to read partition table from ESP32.")

    def update_partition_view(self, table):
        # 기존 레이아웃 내 위젯 삭제
        for i in reversed(range(self.partition_layout.count())): 
            widget = self.partition_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        for p in table:
            # 블록 생성: 이름, 타입/서브타입, 크기 표시
            info = f"{p.name}\n({hex(p.type)}/{hex(p.subtype)})\n{hex(p.size)}"
            btn = QPushButton(info)
            btn.setToolTip(f"Offset: {hex(p.offset)}\nSize: {hex(p.size)}\nFlags: {p.get_flags_list()}")
            btn.setMinimumWidth(120)
            # LittleFS 파티션 (0x01/0x83)인 경우 시각적으로 강조
            if p.type == 0x01 and p.subtype == 0x83:
                btn.setStyleSheet("background-color: #fff3cd; border: 2px solid #ffc107; font-weight: bold;")
            
            btn.clicked.connect(lambda checked=False, part=p: self.on_partition_selected(part))
            self.partition_layout.addWidget(btn)

    def on_partition_selected(self, part):
        self.offset = hex(part.offset)
        self.size = part.size
        self.log(f"Partition Selected -> Name: {part.name}, Offset: {self.offset}, Size: {hex(self.size)}")
        self.update_usage_status()

    def on_extracted_folder_changed(self, path):
        """폴더 내용이 변경될 때 트리 뷰 모델 갱신 및 용량 체크"""
        self.update_usage_status()
        # QFileSystemModel은 자동 감시 기능이 있으나, 외부 변경 시 즉각 반영을 보장하기 위해 setRootPath 재설정
        self.model.setRootPath(self.extract_folder)
        self.tree.setRootIndex(self.model.index(self.extract_folder))

    def update_usage_status(self):
        """현재 extracted_data 폴더의 총 용량을 계산하여 표시 (Step 3.5)"""
        total_size = 0
        if os.path.exists(self.extract_folder):
            for root, dirs, files in os.walk(self.extract_folder):
                for f in files:
                    try:
                        total_size += os.path.getsize(os.path.join(root, f))
                    except OSError: continue
        
        limit = self.size
        percentage = (total_size / limit * 100) if limit > 0 else 0
        self.status_label.setText(f"Storage Usage: {total_size:,} / {limit:,} bytes ({percentage:.1f}%)")
        
        # 용량 초과 시 붉은색으로 강조
        if total_size > limit:
            self.status_label.setStyleSheet("padding: 5px; color: white; background-color: #dc3545; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("padding: 5px; color: black; background-color: #f8f9fa;")

    def action_read_and_extract(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "Warning", "Please select a COM port.")
            return

        self.log("Starting Read Process...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if dump_bin_file(self.bin_file, self.offset, hex(self.size), port=port):
                self.log("Dump success. Extracting...")
                extract_files(self.bin_file, self.extract_folder, self.block_size) # mklittlefs.py에서 폴더 초기화 로직 포함
                self.log("Extraction complete. Refreshing file view.")
                self.model.setRootPath(self.extract_folder) # 파일 시스템 모델 갱신
                self.tree.setRootIndex(self.model.index(self.extract_folder))
                
                # shutil.rmtree로 인해 감시가 풀린 경우 다시 등록
                if self.extract_folder not in self.watcher.directories():
                    self.watcher.addPath(self.extract_folder)
                self.update_usage_status()

                QMessageBox.information(self, "Success", "LittleFS data read and extracted successfully!")
            else:
                self.log("Dump failed.")
        finally:
            QApplication.restoreOverrideCursor()

    def action_assemble_and_flash(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "Warning", "Please select a COM port.")
            return

        self.log("Starting Write Process...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # 4. mklittlefs.py 사용
            assemble_files(self.extract_folder, self.new_bin_file, self.block_size, self.size)
            self.log(f"Assembly complete. Starting flash to ESP32 on port {port}...")
            if download_bin_file(self.new_bin_file, self.offset, port=port):
                self.log("Flash complete.")
                QMessageBox.information(self, "Success", "New LittleFS image flashed to ESP32.")
            else:
                self.log("Flash failed.")
        finally:
            QApplication.restoreOverrideCursor()

    def action_read_from_bin(self):
        """특정 bin 파일을 선택하여 추출 (Step 3.3)"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select LittleFS Binary", "", "Binary Files (*.bin);;All Files (*)")
        if not file_path:
            return

        self.log(f"Reading from binary: {file_path}")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.size = os.path.getsize(file_path)  # 읽은 bin 파일의 크기를 기준 용량으로 설정 (Step 3.5)
            extract_files(file_path, self.extract_folder, self.block_size)
            self.log("Extraction successful.")
            self.model.setRootPath(self.extract_folder)
            self.tree.setRootIndex(self.model.index(self.extract_folder))
            
            if self.extract_folder not in self.watcher.directories():
                self.watcher.addPath(self.extract_folder)
            self.update_usage_status()

            QMessageBox.information(self, "Success", "LittleFS binary extracted successfully.")
        except Exception as e:
            self.log(f"Error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to read from bin: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def action_write_to_bin(self):
        """현재 데이터를 bin 파일로 조립 (Step 3.4)"""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save LittleFS Binary", "new_littlefs.bin", "Binary Files (*.bin);;All Files (*)")
        if not file_path:
            return

        self.log(f"Writing to binary: {file_path}")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            assemble_files(self.extract_folder, file_path, self.block_size, self.size)
            self.log(f"Assembly complete: {file_path}")
            QMessageBox.information(self, "Success", f"Binary assembled and saved to:\n{file_path}")
        except Exception as e:
            self.log(f"Error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to assemble bin: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    # --- 파일 시스템 CRUD 제어 ---
    def show_context_menu(self, position):
        index = self.tree.indexAt(position)
        menu = QMenu()
        
        create_file_act = QAction("Create New File", self)
        create_file_act.triggered.connect(lambda: self.create_item(index, is_dir=False))
        
        create_dir_act = QAction("Create New Folder", self)
        create_dir_act.triggered.connect(lambda: self.create_item(index, is_dir=True))
        
        delete_act = QAction("Delete", self)
        delete_act.triggered.connect(self.delete_items)
        
        menu.addAction(create_file_act)
        menu.addAction(create_dir_act)
        if index.isValid():
            menu.addSeparator()
            menu.addAction(delete_act)
            
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def create_item(self, index, is_dir):
        path = self.model.filePath(index) if index.isValid() else self.extract_folder
        if not os.path.isdir(path):
            path = os.path.dirname(path)
            
        name, ok = QInputDialog.getText(self, "New Item", "Enter Name:")
        if ok and name:
            new_path = os.path.join(path, name)
            try:
                if is_dir:
                    os.makedirs(new_path, exist_ok=True)
                else:
                    with open(new_path, 'w') as f: pass
                self.log(f"Created: {new_path}")
                self.update_usage_status()  # 변경 사항 반영
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create item: {e}")

    def delete_items(self):
        selected_indexes = self.tree.selectionModel().selectedRows()
        if not selected_indexes:
            return

        confirm = QMessageBox.question(self, "Delete", f"Are you sure you want to delete {len(selected_indexes)} selected item(s)?")
        if confirm == QMessageBox.Yes:
            for index in selected_indexes:
                path = self.model.filePath(index)
                if not os.path.exists(path):
                    continue
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    self.log(f"Deleted: {path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not delete {os.path.basename(path)}: {e}")
            self.update_usage_status()  # 삭제 후 용량 갱신

    def open_file_editor(self, index):
        path = self.model.filePath(index)
        if os.path.isfile(path):
            dialog = TextEditorDialog(path, self)
            if dialog.exec() == QDialog.Accepted:
                self.log(f"Updated file: {path}")
                self.update_usage_status()  # 파일 수정 후 용량 갱신

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # 운영체제에 상관없이 일관된 스타일 제공
    explorer = LittleFSExplorer()
    explorer.show()
    sys.exit(app.exec())