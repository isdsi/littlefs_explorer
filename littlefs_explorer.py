import sys
import os
import shutil
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTreeView, QTextEdit,
                             QMessageBox, QInputDialog, QMenu, QDialog, QPlainTextEdit,
                             QFileSystemModel, QComboBox, QLabel,
                             QFileDialog) # QFileDialog 추가

from PySide6.QtCore import Qt, QDir, QModelIndex
from PySide6.QtGui import QAction, QCursor

# 기존 스크립트 모듈 임포트
from dump_littlefs import dump_bin_file
from flash_littlefs import download_bin_file
from mklittlefs import extract_files, assemble_files

class LittleFSTreeView(QTreeView):
    """외부 파일 드래그 앤 드롭을 지원하는 커스텀 트리 뷰"""
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
        self.btn_refresh.setFixedWidth(80) # 버튼 너비 고정
        self.btn_refresh.clicked.connect(self.refresh_ports)
        port_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(port_layout)

        # 1. 상단 액션 버튼
        btn_layout = QHBoxLayout()
        self.btn_read = QPushButton("Step 1 & 2: Read from ESP32 & Extract")
        self.btn_read.setFixedHeight(40)
        self.btn_read.clicked.connect(self.action_read_and_extract)
        
        self.btn_write = QPushButton("Step 4 & 5: Assemble & Write to ESP32")
        self.btn_write.setFixedHeight(40)
        self.btn_write.setStyleSheet("background-color: #d1e7dd; font-weight: bold;")
        self.btn_write.clicked.connect(self.action_assemble_and_flash)

        btn_layout.addWidget(self.btn_read)
        btn_layout.addWidget(self.btn_write)
        main_layout.addLayout(btn_layout)

        # 1.1 바이너리 파일 처리 버튼 (Step 3.3 & 3.4)
        bin_btn_layout = QHBoxLayout()
        self.btn_read_bin = QPushButton("Read from .bin File")
        self.btn_read_bin.setFixedHeight(30)
        self.btn_read_bin.clicked.connect(self.action_read_from_bin)

        self.btn_write_bin = QPushButton("Write to .bin File")
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
        
        main_layout.addWidget(self.tree)

        # 3. 하단 로그 출력창
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(150)
        self.log_view.setStyleSheet("background-color: #f8f9fa; font-family: Consolas;")
        main_layout.addWidget(self.log_view)

        self.refresh_ports()
        self.log("Explorer Initialized. Work directory: " + self.extract_folder)

    def log(self, message):
        self.log_view.append(f"> {message}")

    # --- ESP32 통신 및 바이너리 처리 ---
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
            extract_files(file_path, self.extract_folder, self.block_size)
            self.log("Extraction successful.")
            self.model.setRootPath(self.extract_folder)
            self.tree.setRootIndex(self.model.index(self.extract_folder))
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

    def open_file_editor(self, index):
        path = self.model.filePath(index)
        if os.path.isfile(path):
            dialog = TextEditorDialog(path, self)
            if dialog.exec() == QDialog.Accepted:
                self.log(f"Updated file: {path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # 운영체제에 상관없이 일관된 스타일 제공
    explorer = LittleFSExplorer()
    explorer.show()
    sys.exit(app.exec())